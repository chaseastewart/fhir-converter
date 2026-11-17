# agent/mcp_tools.py
import os
from langchain_mcp_adapters.client import MultiServerMCPClient

async def get_graph_tools():
    client = MultiServerMCPClient({
    "neo4j":  {
    "command": r"venv\Scripts\mcp-neo4j-cypher.exe",
    "args": [],
    "transport": "stdio",
    "env": {
        **{k: os.environ[k] for k in ("NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD")},
        "NEO4J_DATABASE": os.environ.get("NEO4J_DATABASE", "neo4j"),
        "NEO4J_READ_ONLY": "true",
        "NEO4J_TRANSPORT": "stdio",
        },
    }})
    return await client.get_tools()
