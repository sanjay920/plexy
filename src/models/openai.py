import json
from typing import List, Dict, Generator
from openai import OpenAI

from core.config import OPENAI_API_KEY
from core.logger import log
from .base import BaseModel


class OpenAIModel(BaseModel):
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model_name = "gpt-4o"
        # Define our tool for web searching.
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "web_search_tool",
                    "description": "Search the web for current information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "queries": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of search queries",
                            },
                        },
                        "required": ["queries"],
                    },
                },
            }
        ]

    def stream_chat(
        self, messages: List[Dict[str, str]], debug: bool = False
    ) -> Generator[Dict, None, None]:
        """
        Streams chat responses from OpenAI.
        We rely on the messages passed in -- we do NOT prepend
        a separate system message here. This matches the notebook flow.
        """
        if debug:
            log("Sending streaming request to OpenAI with messages:")
            log(json.dumps(messages, indent=2))

        stream = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            tools=self.tools,
            tool_choice="auto",
            stream=True,
        )

        accumulated_tool_call = None
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta

            # If there's text content, yield it
            if delta.content is not None:
                yield {"type": "text", "content": delta.content}

            # If there's a tool call, accumulate its partial data
            if delta.tool_calls:
                tool_call = delta.tool_calls[0]
                if accumulated_tool_call is None:
                    accumulated_tool_call = {
                        "id": tool_call.id,
                        "name": tool_call.function.name or "",
                        "arguments": tool_call.function.arguments or "",
                    }
                else:
                    if tool_call.function.name:
                        accumulated_tool_call["name"] += tool_call.function.name
                    if tool_call.function.arguments:
                        accumulated_tool_call[
                            "arguments"
                        ] += tool_call.function.arguments

        # At the end, if we accumulated a tool call, yield it
        if accumulated_tool_call:
            yield {
                "type": "tool_call",
                "id": accumulated_tool_call["id"],
                "name": accumulated_tool_call["name"],
                "arguments": accumulated_tool_call["arguments"],
            }
