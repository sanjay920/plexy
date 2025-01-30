import json
from typing import Dict, Optional, List
from datetime import datetime
from tavily import TavilyClient
from ..core.config import TAVILY_API_KEY

TOOL_NAME = "web_search"

def run(
    query: str,
    topic: str = "general",
    time_range: str = "day",
    include_domains: Optional[List[str]] = None,
    page: int = 1
) -> Dict:
    """Perform a web search using Tavily."""
    try:
        client = TavilyClient(api_key=TAVILY_API_KEY)
        # We'll do a simple search; you can expand logic to respect topic/time_range
        response = client.search(
            query=query,
            search_depth="advanced",
            include_answer=False,
            include_raw_content=True,
            max_results=10,
            page=page,
        )

        return {
            "success": True,
            "query": query,
            "results": [
                {
                    "title": r["title"],
                    "url": r["url"],
                    "content": r["content"],
                }
                for r in response.get("results", [])
            ],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

