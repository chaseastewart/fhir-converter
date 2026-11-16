
import truststore

truststore.inject_into_ssl()

from neo4j import GraphDatabase

class GraphBuilder:

    def __init__(self, uri, username, password, database):
        self.driver = GraphDatabase.driver(
            uri,
            auth=(username, password),
            # Recycle pooled connections before Aura's load balancer
            # closes them, and probe idle ones before reuse.
            max_connection_lifetime=1800,
            liveness_check_timeout=60,
            keep_alive=True
        )
        self.database = database or None

    def verify_connection(self):
        self.driver.verify_connectivity()
        print("Connected to Neo4j AuraDB")

    def create_constraints(self):

        queries = [
            """
            CREATE CONSTRAINT repository_id IF NOT EXISTS
            FOR (n:Repository)
            REQUIRE n.id IS UNIQUE
            """,
            """
            CREATE CONSTRAINT file_id IF NOT EXISTS
            FOR (n:File)
            REQUIRE n.id IS UNIQUE
            """,
            """
            CREATE CONSTRAINT symbol_id IF NOT EXISTS
            FOR (n:Symbol)
            REQUIRE n.id IS UNIQUE
            """,
            """
            CREATE CONSTRAINT import_id IF NOT EXISTS
            FOR (n:Import)
            REQUIRE n.id IS UNIQUE
            """,
            """
            CREATE CONSTRAINT call_id IF NOT EXISTS
            FOR (n:Call)
            REQUIRE n.id IS UNIQUE
            """
        ]

        with self.driver.session(
            database=self.database
        ) as session:

            for query in queries:
                session.run(query).consume()

    def create_repository(self, repo_name):

        with self.driver.session(
            database=self.database
        ) as session:

            session.run(
                """
                MERGE (r:Repository {id: $id})
                SET r.name = $name
                """,
                id=repo_name,
                name=repo_name
            ).consume()

    def insert_file(self, repo_name, data):
        """Write one file and its symbols, imports and calls.

        Everything for the file goes in a single managed transaction
        (execute_write), so the driver retries automatically if the
        connection to AuraDB drops. Lists are sent with UNWIND instead
        of one round trip per item.
        """
        file_id = f"{repo_name}/{data['path']}"

        symbols = [
            {
                "id": s["id"],
                "name": s["name"],
                "kind": s["kind"],
                "qualified_name": s["qualified_name"],
                "line": s["line"],
                "end_line": s["end_line"],
                "parent_id": s["parent_id"],
            }
            for s in data["symbols"]
        ]

        imports = [
            {
                "id": f"{file_id}:import:{index}",
                "statement": item["text"],
                "line": item["line"],
            }
            for index, item in enumerate(data["imports"])
        ]

        calls = [
            {
                "id": f"{file_id}:call:{index}",
                "name": item["name"],
                "line": item["line"],
                "parent_id": item["parent_id"],
            }
            for index, item in enumerate(data["calls"])
        ]

        def work(tx):
            tx.run(
                """
                MATCH (r:Repository {id: $repo})
                MERGE (f:File {id: $file_id})
                SET f.path = $path
                MERGE (r)-[:HAS_FILE]->(f)
                """,
                repo=repo_name,
                file_id=file_id,
                path=data["path"]
            ).consume()

            # Symbols are listed parent-first (pre-order walk), so each
            # parent already exists when its children are merged.
            tx.run(
                """
                MATCH (f:File {id: $file_id})
                UNWIND $rows AS row
                MERGE (s:Symbol {id: row.id})
                SET s.name = row.name,
                    s.kind = row.kind,
                    s.qualified_name = row.qualified_name,
                    s.line = row.line,
                    s.end_line = row.end_line,
                    s.file = $path
                MERGE (f)-[:CONTAINS]->(s)

                WITH s, row
                OPTIONAL MATCH (parent:Symbol {id: row.parent_id})
                FOREACH (_ IN CASE
                    WHEN parent IS NULL THEN []
                    ELSE [1]
                END |
                    MERGE (parent)-[:CONTAINS]->(s)
                )
                """,
                file_id=file_id,
                path=data["path"],
                rows=symbols
            ).consume()

            tx.run(
                """
                MATCH (f:File {id: $file_id})
                UNWIND $rows AS row
                MERGE (i:Import {id: row.id})
                SET i.statement = row.statement,
                    i.line = row.line
                MERGE (f)-[:HAS_IMPORT]->(i)
                """,
                file_id=file_id,
                rows=imports
            ).consume()

            tx.run(
                """
                MATCH (f:File {id: $file_id})
                UNWIND $rows AS row
                MERGE (c:Call {id: row.id})
                SET c.name = row.name,
                    c.line = row.line
                MERGE (f)-[:HAS_CALL]->(c)

                WITH c, row
                OPTIONAL MATCH (s:Symbol {id: row.parent_id})
                FOREACH (_ IN CASE
                    WHEN s IS NULL THEN []
                    ELSE [1]
                END |
                    MERGE (s)-[:HAS_CALL]->(c)
                )
                """,
                file_id=file_id,
                rows=calls
            ).consume()

        with self.driver.session(
            database=self.database
        ) as session:
            session.execute_write(work)

    def link_imports(self, repo_name, data):
        """Create File-[:IMPORTS]->File and Import-[:RESOLVES_TO]->File.

        Call this after insert_file has run for every file, so the
        target File nodes already exist.
        """
        file_id = f"{repo_name}/{data['path']}"

        rows = [
            {
                "import_id": f"{file_id}:import:{index}",
                "target_id": f"{repo_name}/{target_path}",
                "line": item["line"],
            }
            for index, item in enumerate(data["imports"])
            for target_path in item.get("resolved", [])
        ]

        if not rows:
            return

        def work(tx):
            tx.run(
                """
                MATCH (f:File {id: $file_id})
                UNWIND $rows AS row
                MATCH (t:File {id: row.target_id})
                MATCH (i:Import {id: row.import_id})
                MERGE (i)-[:RESOLVES_TO]->(t)
                MERGE (f)-[r:IMPORTS]->(t)
                SET r.lines = CASE
                    WHEN r.lines IS NULL THEN [row.line]
                    WHEN row.line IN r.lines THEN r.lines
                    ELSE r.lines + row.line
                END
                """,
                file_id=file_id,
                rows=rows
            ).consume()

        with self.driver.session(
            database=self.database
        ) as session:
            session.execute_write(work)

    def link_symbols(self, repo_name, data):
        """Create CALLS and INHERITS edges from resolved calls and bases.

        Adds Call-[:RESOLVES_TO]->Symbol, caller-[:CALLS]->Symbol (the
        caller is the enclosing Symbol, or the File for module-level
        calls) and Symbol-[:INHERITS]->Symbol. Call this after
        insert_file has run for every file.
        """
        file_id = f"{repo_name}/{data['path']}"

        calls = [
            {
                "call_id": f"{file_id}:call:{index}",
                "caller_id": item["parent_id"],
                "target_id": item["target_id"],
                "resolution": item["resolution"],
                "line": item["line"],
            }
            for index, item in enumerate(data["calls"])
            if item.get("target_id")
        ]

        bases = [
            {"sub_id": s["id"], "base_id": base_id}
            for s in data["symbols"]
            for base_id in s.get("base_ids", [])
        ]

        if not calls and not bases:
            return

        def work(tx):
            tx.run(
                """
                MATCH (f:File {id: $file_id})
                UNWIND $rows AS row
                MATCH (t:Symbol {id: row.target_id})
                MATCH (c:Call {id: row.call_id})
                MERGE (c)-[:RESOLVES_TO]->(t)
                WITH f, t, row
                OPTIONAL MATCH (s:Symbol {id: row.caller_id})
                WITH t, row, coalesce(s, f) AS caller
                MERGE (caller)-[r:CALLS]->(t)
                SET r.resolution = row.resolution,
                    r.lines = CASE
                        WHEN r.lines IS NULL THEN [row.line]
                        WHEN row.line IN r.lines THEN r.lines
                        ELSE r.lines + row.line
                    END
                """,
                file_id=file_id,
                rows=calls
            ).consume()

            tx.run(
                """
                UNWIND $rows AS row
                MATCH (a:Symbol {id: row.sub_id})
                MATCH (b:Symbol {id: row.base_id})
                MERGE (a)-[:INHERITS]->(b)
                """,
                rows=bases
            ).consume()

        with self.driver.session(
            database=self.database
        ) as session:
            session.execute_write(work)

    def close(self):
        self.driver.close()
