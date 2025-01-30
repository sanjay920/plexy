import json
import sys
from typing import Dict, Optional, List, Generator
from ..models.base import BaseModel
from ..models.openai import OpenAIModel
from ..core.logger import log
from ..core.tool_registry import ToolRegistry


class Agent:
    """
    Agent manages the conversation, calls the model in a streaming fashion,
    and executes any tool calls that appear in the streamed output.
    """

    def __init__(
        self,
        model_provider: str = "openai",
        tool_dir: Optional[str] = None,
        debug: bool = False,
    ):
        self.model = self._init_model(model_provider)
        self.tool_registry = ToolRegistry(tool_dir)
        self.conversation: List[Dict] = []
        self.debug = debug

    def _init_model(self, provider: str) -> BaseModel:
        if provider == "openai":
            return OpenAIModel()
        raise ValueError(f"Unsupported model provider: {provider}")

    def stream_chat(self, user_input: str) -> Generator[str, None, None]:
        """
        Takes a user input, appends it to the conversation, and yields
        partial text or tool calls from the model in a streaming fashion.

        If a tool call is encountered, we run the tool, add the result to the
        conversation, then continue streaming by calling the model again.
        """
        # Add the user's message
        self.conversation.append({"role": "user", "content": user_input})

        while True:
            # Stream from the model
            for chunk in self.model.stream_chat(self.conversation, debug=self.debug):
                if chunk["type"] == "text":
                    # Regular text chunk: yield to caller
                    yield chunk["content"]

                elif chunk["type"] == "tool_call":
                    # The model is requesting a tool call
                    if self.debug:
                        log(f"Tool call requested: {chunk}", error=False)

                    tool_name = chunk["name"]
                    args_json = chunk["arguments"]
                    try:
                        args = json.loads(args_json) if args_json.strip() else {}
                    except json.JSONDecodeError:
                        # If the arguments are invalid JSON, handle gracefully
                        args = {}

                    # Add the assistant's tool call message
                    self.conversation.append(
                        {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": chunk["id"],
                                    "type": "function",
                                    "function": {
                                        "name": tool_name,
                                        "arguments": args_json,
                                    },
                                }
                            ],
                        }
                    )

                    # Execute the tool
                    try:
                        result = self.tool_registry.run_tool(tool_name, args)
                    except Exception as e:
                        # If the tool fails, we add an error response
                        result = {"error": str(e)}

                    if self.debug:
                        log(f"Tool execution result: {json.dumps(result, indent=2)}")

                    # Add the tool result to the conversation
                    self.conversation.append(
                        {
                            "role": "tool",
                            "content": json.dumps(result),
                            "tool_call_id": chunk[
                                "id"
                            ],  # Link the response to the tool call
                        }
                    )

                    # Break out of the loop so we can call the model again
                    # with the updated conversation
                    break

            else:
                # If we did not break, then no new tool call was found
                # and the model is done streaming.
                return

            # If we reach here, we executed a tool, so let's continue the conversation
            # by re-calling the model. The loop above repeats until no new calls appear.
