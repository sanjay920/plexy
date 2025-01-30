import os
import sys
import importlib
from typing import Dict, Any
from .logger import log

class ToolRegistry:
    def __init__(self, tool_dir: str | None = None):
        self.tools = {}
        self._load_builtin_tools()
        if tool_dir:
            self._load_external_tools(tool_dir)

    def _load_builtin_tools(self):
        """Load built-in tools from the tools directory."""
        from ..tools import web_search

        self.tools["web_search"] = web_search.run
        log("Loaded built-in tool: web_search")

    def _load_external_tools(self, tool_dir: str):
        """Load external tools from the specified directory."""
        if not os.path.exists(tool_dir):
            log(f"Tool directory not found: {tool_dir}", error=True)
            return

        sys.path.append(tool_dir)
        for file in os.listdir(tool_dir):
            if file.endswith(".py") and not file.startswith("_"):
                module_name = file[:-3]
                try:
                    module = importlib.import_module(module_name)
                    if hasattr(module, "TOOL_NAME") and hasattr(module, "run"):
                        self.tools[module.TOOL_NAME] = module.run
                        log(f"Loaded external tool: {module.TOOL_NAME}")
                except Exception as e:
                    log(f"Error loading tool {module_name}: {e}", error=True)

    def run_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Run a tool by name with the given arguments."""
        if tool_name not in self.tools:
            raise ValueError(f"Tool not found: {tool_name}")

        log(f"Executing tool: {tool_name} with arguments: {args}")
        return self.tools[tool_name](**args)

