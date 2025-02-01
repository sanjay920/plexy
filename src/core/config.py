import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root
env_path = Path(__file__).parents[2] / ".env"
load_dotenv(env_path)

# List of environment variables that must be provided (i.e. those without defaults)
REQUIRED_VARS = [
    "OPENAI_API_KEY",
    "TAVILY_API_KEY",
    "COHERE_API_KEY",
]

missing_vars = [var for var in REQUIRED_VARS if not os.getenv(var)]
if missing_vars:
    raise ValueError(
        f"Missing required environment variables: {', '.join(missing_vars)}"
    )

# Export required environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")

# Redis configuration with sensible defaults
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

# Crawl4AI configuration with sensible defaults
CRAWL4AI_BASE_URL = os.getenv("CRAWL4AI_BASE_URL", "http://localhost:11235")
CRAWL4AI_API_TOKEN = os.getenv("CRAWL4AI_API_TOKEN", "your_secret_token")
