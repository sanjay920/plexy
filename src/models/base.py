from abc import ABC, abstractmethod
from typing import List, Dict, Generator


class BaseModel(ABC):
    """
    Base class for all model providers.
    Must implement stream_chat() yielding either text or tool calls.
    """

    @abstractmethod
    def stream_chat(
        self, messages: List[Dict[str, str]], debug: bool = False
    ) -> Generator[Dict, None, None]:
        """
        Yields dicts such as:
          { "type": "text", "content": "..." }
          { "type": "tool_call", "id": "...", "name": "...", "arguments": "..." }
        """
        pass
