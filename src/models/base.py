from abc import ABC, abstractmethod
from typing import List, Dict, Generator, Union

class BaseModel(ABC):
    """Base class for all model providers."""
    
    @abstractmethod
    def stream_chat(
        self, messages: List[Dict[str, str]], debug: bool = False
    ) -> Generator[Dict, None, None]:
        """
        Stream responses from the model. Yields dicts of the form:
          { "type": "text",       "content": "partial text..." }
          or
          { "type": "tool_call",  "name": "web_search", "arguments": "..." }
        """
        pass

