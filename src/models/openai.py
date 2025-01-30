import json
from typing import List, Dict, Generator
from datetime import datetime
from openai import OpenAI
from ..core.config import OPENAI_API_KEY
from ..core.logger import log
from .base import BaseModel


class OpenAIModel(BaseModel):
    def __init__(self):
        # Initialize OpenAI client with API key
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model_name = "gpt-4"
        # Example "function" tool definition
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the web for current information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query text",
                            },
                            "topic": {
                                "type": "string",
                                "enum": ["general", "news"],
                                "description": "The category of search",
                            },
                            "time_range": {
                                "type": "string",
                                "enum": ["day", "week", "month", "year"],
                                "description": "How far back to search",
                            },
                            "include_domains": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of domains to include",
                            },
                            "page": {
                                "type": "integer",
                                "description": "Page number for results",
                                "default": 1,
                            },
                        },
                        "required": ["query"],
                    },
                },
            }
        ]

        # System prompt with current date
        today = datetime.now().strftime("%A, %B %d, %Y")
        self.system_message = {
            "role": "system",
            "content": (
                f"You are Plexy, a helpful AI assistant with web_search capability. "
                f"Today is {today}. Use the function if necessary."
            ),
        }

    def stream_chat(
        self, messages: List[Dict[str, str]], debug: bool = False
    ) -> Generator[Dict, None, None]:
        """
        Streams responses from the OpenAI ChatCompletion endpoint. For partial text,
        yields: { "type": "text", "content": "..." }

        If/when a tool call is detected, yields: {
          "type": "tool_call",
          "name": "...",
          "arguments": "..."
        }
        and then ends the stream (so the caller can handle the function).
        """
        # Prepend the system prompt if it's not already present:
        full_messages = [self.system_message] + messages

        if debug:
            log("Sending streaming request to OpenAI with these messages:", error=False)
            log(json.dumps(full_messages, indent=2), error=False)

        # Updated streaming call using new SDK
        stream = self.client.chat.completions.create(
            model=self.model_name,
            messages=full_messages,
            tools=self.tools,
            tool_choice="auto",
            stream=True,
        )

        # We accumulate partial function call data if it happens in multiple chunks
        active_tool_call = None

        for chunk in stream:
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta

            # Handle regular text content
            if delta.content is not None:
                yield {"type": "text", "content": delta.content}

            # Handle tool calls
            if delta.tool_calls:
                tool_call = delta.tool_calls[0]
                if active_tool_call is None:
                    active_tool_call = {
                        "id": tool_call.id,
                        "name": (
                            tool_call.function.name if tool_call.function.name else ""
                        ),
                        "arguments": (
                            tool_call.function.arguments
                            if tool_call.function.arguments
                            else ""
                        ),
                    }
                else:
                    if tool_call.function.name:
                        active_tool_call["name"] += tool_call.function.name
                    if tool_call.function.arguments:
                        active_tool_call["arguments"] += tool_call.function.arguments

        # Yield accumulated tool call if present
        if active_tool_call:
            yield {
                "type": "tool_call",
                "id": active_tool_call["id"],
                "name": active_tool_call["name"],
                "arguments": active_tool_call["arguments"],
            }
