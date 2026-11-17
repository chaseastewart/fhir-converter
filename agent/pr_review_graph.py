import os, asyncio, requests
from typing import TypedDict
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langchain.agents import create_agent
# from langchain_anthropic import ChatAnthropic
from langchain_groq import ChatGroq
from skill_loader import load_skill
from mcp_tools import get_graph_tools

load_dotenv()
GH = {"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
      "Accept": "application/vnd.github+json"}

class ReviewState(TypedDict):
    repo: str          # "owner/name"
    pr_number: int
    diff: str
    review: str

# Node 1: get the changed files and patches from GitHub
def fetch_diff(state: ReviewState) -> dict:
    github_repo = os.environ['GITHUB_REPO']
    url = f"https://api.github.com/repos/{github_repo}/pulls/{state['pr_number']}/files"
    resp = requests.get(url, headers=GH, params={"per_page": 100})
    resp.raise_for_status()
    files = resp.json()
    parts = [f"### {f['filename']} ({f['status']})\n{f.get('patch', '[binary or too large]')}"
             for f in files]
    return {"diff": "\n\n".join(parts)}

# Node 2: the reviewer (LLM + skill.md + Neo4j tools)
async def make_review_node():
    tools = await get_graph_tools()
    skill = load_skill(".claude\\skills\\github-pr-review\\SKILL.md")
    system = (
        skill
        + "\n\nYou also have tools that query a Neo4j graph of this codebase. "
          "Before judging a change, use them to find callers, dependents and related "
          "modules of the changed functions/classes, and flag any impact the diff "
          "itself does not show."
    )
    # agent = create_agent(
    #     ChatAnthropic(model="claude-sonnet-5-5", max_tokens=8000),
    #     tools,
    #     system_prompt=system,
    # )

    agent = create_agent(
        ChatGroq(model="openai/gpt-oss-120b", max_tokens=8000),
        tools,
        system_prompt=system,
    )


    async def review(state: ReviewState) -> dict:
        result = await agent.ainvoke(
            {"messages": [("user", f"Review this pull request diff:\n\n{state['diff']}")]}
        )
        return {"review": result["messages"][-1].content}
    return review

# Node 3: post the review back to the PR
def post_comment(state: ReviewState) -> dict:
    github_repo = os.environ['GITHUB_REPO']
    url = f"https://api.github.com/repos/{github_repo}/issues/{state['pr_number']}/comments"
    requests.post(url, headers=GH, json={"body": state["review"]}).raise_for_status()
    return {}

async def build_graph():
    graph = StateGraph(ReviewState)
    graph.add_node("fetch_diff", fetch_diff)
    graph.add_node("review", await make_review_node())
    graph.add_node("post_comment", post_comment)
    
    graph.add_edge(START, "fetch_diff")
    graph.add_edge("fetch_diff", "review")
    graph.add_edge("review", "post_comment")
    graph.add_edge("post_comment", END)
    return graph.compile()

if __name__ == "__main__":
    import sys
    async def main():
        sys.stdout.reconfigure(encoding="utf-8")
        app = await build_graph()
        print(app.get_graph().draw_mermaid())
        out = await app.ainvoke({"pr_number": int(sys.argv[1])})
        print(out["review"])
    asyncio.run(main())

