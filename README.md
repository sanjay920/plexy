# Plexy

A CLI-based AI assistant with tool-calling capabilities.

## Features

- Interactive CLI interface
- OpenAI GPT integration
- Extensible tool system
- Step-by-step logging
- Easy to add new tools and model providers

## Installation

```bash
pip install -e .
```

## Usage

```bash
# Basic usage
plexy

# Use a specific model provider
plexy --model openai

# Load additional tools
plexy --tool-dir /path/to/tools
```

## Adding New Tools

Create a new Python file in the tools directory with:

```python
TOOL_NAME = "your_tool_name"

def run(**kwargs):
    # Implement your tool logic here
    return {"result": "your result"}
```

## License

MIT
