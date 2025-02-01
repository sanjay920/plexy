import json
import sys
from typing import Dict, List
from rich.console import Console
from rich.markdown import Markdown
from datetime import datetime
from zoneinfo import ZoneInfo

from .logger import log
from .tool_registry import ToolRegistry
from .decision import Decision

# import your pipeline helpers
from tools.pipeline_helpers import (
    tavily_in_parallel,
    enrich_docs_with_cache,
    deduplicate_docs,
    cohere_rerank,
    call_decision_llm,
)

console = Console()


class Agent:
    """
    Agent that calls the decision LLM repeatedly.
    We keep exactly ONE system message in self.conversation[0].
    After a 'search', we append references to that single system message
    so the model is forced to produce inline citations if it decides to answer.
    """

    def __init__(
        self,
        model_provider: str = "openai",
        tool_dir: str = "",
        debug: bool = False,
        max_iters: int = 2,
    ):
        self.tool_registry = ToolRegistry(tool_dir)
        self.conversation: List[Dict] = []

        self.debug = debug
        self.max_iters = max_iters

        # Start with a single system prompt
        current_datetime = datetime.now(tz=ZoneInfo("America/Los_Angeles")).strftime(
            "%Y-%m-%d %H:%M:%S %Z"
        )
        self.system_content = (
            f"You are Plexy, a helpful AI assistant with web_search capability. "
            f"Current date and time is {current_datetime}.\n\n"
            "You can either:\n"
            "1) Provide a final answer => action='answer'\n"
            "2) Provide web search queries => action='search'\n\n"
            "If action='search', provide 1-5 queries in 'search_queries'.\n"
            "Use 'scratchpad' for short reasoning if you want.\n\n"
            "Return strict JSON for the Decision schema. (No extra keys!)\n"
            "When you eventually provide a final answer (action='answer'), you MUST:\n"
            "1) Base your answer ONLY on the references we have added below.\n"
            "2) Use inline citations like [1], [2], etc.\n"
            "3) Your response must end with a 'References' section listing the sources cited. For example:\n"
            "References:\n"
            "[1] https://example.com/source1\n"
            "[2] https://example.com/source2\n"
            "Obviously, dont include any references that are not cited in the body of your response.\n"
        )
        # Place it as the single system message
        self.conversation.append({"role": "system", "content": self.system_content})

    def run_pipeline(self, user_query: str):
        """
        Iterative pipeline:
         1) Add user query
         2) Repeatedly call decision LLM
         3) If it says 'search', run search tool, store results
         4) If 'answer', yield final LLM response
         5) If we exceed max_iters, forcibly produce a final
        """
        # Add the user query
        self.conversation.append({"role": "user", "content": user_query})

        last_top_docs = []

        for iteration in range(self.max_iters):
            decision = call_decision_llm(self.conversation, debug=self.debug)
            if not decision:
                yield "\n**(No valid decision from LLM - halting.)**\n"
                return

            if decision.scratchpad:
                # Show scratchpad
                yield "\n"
                yield from self._markdown_stream(
                    f"**Scratchpad iteration={iteration+1}**: {decision.scratchpad}"
                )
                yield "\n"

            if decision.action == "answer":
                if decision.message:
                    yield "\n"
                    yield from self._markdown_stream(decision.message)
                    yield "\n"
                    self.conversation.append(
                        {"role": "assistant", "content": decision.message}
                    )
                    return
                else:
                    yield "\nNo message from the LLM. Stopping.\n"
                    return

            # If action == "search"
            if self.debug:
                log(f"[DEBUG] Searching with queries: {decision.search_queries}")

            yield "\n(Performing web searches...)\n"

            docs = tavily_in_parallel(decision.search_queries)
            docs = enrich_docs_with_cache(docs)
            docs = deduplicate_docs(docs)
            top_docs = cohere_rerank(user_query, docs, top_n=10)
            last_top_docs = top_docs

            # Store the tool calls in conversation
            # Convert arguments dict to JSON string for OpenAI API
            self.conversation.append(
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": f"search_{iteration}",
                            "type": "function",
                            "function": {
                                "name": "web_search_tool",
                                "arguments": json.dumps(
                                    {"queries": decision.search_queries}
                                ),
                            },
                        }
                    ],
                }
            )
            self.conversation.append(
                {
                    "role": "tool",
                    "tool_call_id": f"search_{iteration}",
                    "content": json.dumps(top_docs, indent=2),
                }
            )

            # Build enumerated references text
            enumerated_list = []
            for i, doc in enumerate(top_docs, start=1):
                enumerated_list.append(
                    f"{i}. Title: {doc.get('title','Untitled')}\n"
                    f"   URL: {doc.get('url','#')}\n"
                    f"   Snippet:\n   \"{doc.get('content','')}\"\n---\n"
                )
            if enumerated_list:
                # Append references to the single system message
                reference_block = "\n\n".join(enumerated_list)
                updated_refs = (
                    f"\n\nHere are new references (iteration={iteration+1}):\n"
                    f"{reference_block}"
                    "#---------------------------------------#\n"
                )
                self.system_content += updated_refs
                # Overwrite system message [0]
                self.conversation[0] = {
                    "role": "system",
                    "content": self.system_content,
                }

        # Force final if we exit loop
        yield "\nReached max iterations. Force-producing final answer...\n"
        self.conversation.append(
            {
                "role": "user",
                "content": (
                    "Please now provide your final answer with inline citations [1], [2], etc., referencing only the references above, "
                    "and end with a 'References' section."
                ),
            }
        )
        forced_decision = call_decision_llm(self.conversation, debug=self.debug)
        if forced_decision and forced_decision.message:
            yield from self._markdown_stream(forced_decision.message)
            yield "\n"
        else:
            yield "\nNo final forced answer produced.\n"

    def _markdown_stream(self, md_text: str):
        md_renderable = Markdown(md_text)
        with console.capture() as capture:
            console.print(md_renderable)
        yield capture.get()
