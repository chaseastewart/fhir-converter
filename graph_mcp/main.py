import os
from pathlib import Path
from dotenv import load_dotenv

from graph_mcp.parser import parse_repository
from graph_mcp.graph_builder import GraphBuilder

load_dotenv()


REPO_PATH = os.getenv("REPO_PATH")

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")


def main():

    if not REPO_PATH or not Path(REPO_PATH).is_dir():
        raise ValueError("Invalid REPO_PATH in .env")

    repo_name = Path(REPO_PATH).resolve().name

    print("\nStarting repository parsing...")

    parsed_files = parse_repository(REPO_PATH)

    print(f"Files parsed: {len(parsed_files)}")

    builder = GraphBuilder(
        NEO4J_URI,
        NEO4J_USERNAME,
        NEO4J_PASSWORD,
        NEO4J_DATABASE
    )

    try:

        builder.verify_connection()

        builder.create_constraints()

        builder.create_repository(repo_name)

        print("\nCreating Neo4j graph...")

        for index, data in enumerate(parsed_files, start=1):

            builder.insert_file(repo_name, data)

            print(
                f"[{index}/{len(parsed_files)}] "
                f"Processed: {data['path']}"
            )

        print("\nLinking file imports...")

        for data in parsed_files:
            builder.link_imports(repo_name, data)

        print("\nLinking calls and inheritance...")

        for data in parsed_files:
            builder.link_symbols(repo_name, data)

        print("\nRepository graph created successfully!")

    finally:
        builder.close()


if __name__ == "__main__":
    main()
