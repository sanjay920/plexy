import json
from typing import Dict, List
from datetime import datetime
from tavily import TavilyClient
from core.config import TAVILY_API_KEY

TOOL_NAME = "web_search_tool"


def run(queries: List[str]) -> Dict:
    """
    Run a web search for each query using Tavily and return a combined result.
    If Tavily or the search fails, we add an error doc that includes content="",
    to avoid KeyError down the pipeline.
    """
    client = TavilyClient(api_key=TAVILY_API_KEY)
    all_results = []
    for q in queries:
        try:
            response = client.search(
                query=q,
                search_depth="advanced",
                include_answer=False,
                include_raw_content=True,
                max_results=10,
            )
            results = response.get("results", [])
            shaped = [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    # We store the text in "content" so it’s consistent
                    "content": (r.get("content") or r.get("raw_content") or ""),
                    "score": r.get("score", 0.0),
                }
                for r in results
            ]
            all_results.extend(shaped)
        except Exception as e:
            # If there's a failure, store an 'error doc' with empty content
            all_results.append(
                {
                    "title": "Error doc",
                    "url": "",
                    "content": "",
                    "score": 0.0,
                    "error": str(e),
                    "query": q,
                }
            )
    return {
        "success": True,
        "queries": queries,
        "results": all_results,
        "timestamp": datetime.now().isoformat(),
    }
