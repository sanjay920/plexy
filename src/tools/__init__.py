import os
import importlib
from typing import Dict, Optional
from .web_search import run as web_search_run

DEFAULT_TOOLS = {
    "web_search": web_search_run
}

def load_tools(tool_dir: Optional[str] = None) -> Dict:
    """Load all available tools from built-ins plus an optional directory."""
    tools = DEFAULT_TOOLS.copy()
    
    if tool_dir and os.path.exists(tool_dir):
        for filename in os.listdir(tool_dir):
            if filename.endswith('.py') and not filename.startswith('_'):
                module_name = filename[:-3]
                try:
                    spec = importlib.util.spec_from_file_location(
                        module_name,
                        os.path.join(tool_dir, filename)
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    if hasattr(module, 'TOOL_NAME') and hasattr(module, 'run'):
                        tools[module.TOOL_NAME] = module.run
                except Exception as e:
                    print(f"Error loading tool {filename}: {str(e)}")
    return tools

