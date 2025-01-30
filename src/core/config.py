import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
env_path = Path(__file__).parents[2] / '.env'
load_dotenv(env_path)

# Required environment variables
REQUIRED_VARS = [
    'OPENAI_API_KEY',
    'TAVILY_API_KEY'
]

# Check for required environment variables
missing_vars = [var for var in REQUIRED_VARS if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Export environment variables
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
TAVILY_API_KEY = os.getenv('TAVILY_API_KEY')

