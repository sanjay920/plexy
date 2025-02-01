from pydantic import BaseModel
from typing import Literal, List, Optional


class Decision(BaseModel):
    """
    The LLM returns a JSON matching this schema:
      {
        "action": "search" or "answer",
        "search_queries": [...],
        "message": "...",       # (if action == "answer")
        "scratchpad": "..."     # optional reasoning
      }
    """

    action: Literal["search", "answer"]
    search_queries: List[str]
    message: Optional[str]
    scratchpad: Optional[str]
