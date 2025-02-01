# Plexy

**Plexy** is a command line AI assistant that leverages an iterative pipeline to refine answers using large language models and real-time web search. It combines decision-making with dynamic tool integration to deliver contextually relevant responses complete with inline citations.

---

## Features

- **Iterative Decision Pipeline:** Continuously refines responses by alternating between LLM decisions and web search results.
- **Web Search Integration:** Uses the Tavily API to perform web searches and enrich results with caching (via Redis) and deduplication.
- **Tool Registry:** Supports built-in and external tools, enabling extensibility for additional capabilities.
- **LLM Integration:** Integrates with OpenAI’s models to drive decision making.
- **Inline Citations:** Answers include inline citations with a final references section based solely on the retrieved sources.
- **Enhanced Document Quality:** Re-ranks search results using Cohere and enriches content via Crawl4AI when needed.

---

## Getting Started

### Prerequisites

- **Python:** 3.11 or higher
- **Redis and Crawl4AI:** Both services need to be running. You can set these up using Docker.
- **API Keys:**  
  - [OpenAI](https://openai.com/)  
  - [Tavily](https://tavily.ai/)  
  - [Cohere](https://cohere.ai/)  

  You can set these environment variables directly in your shell or use the provided `.env` file.

### Installation

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/yourusername/plexy.git
   cd plexy
   ```

2. **Install Dependencies:**

   If using [Poetry](https://python-poetry.org/):

   ```bash
   poetry install
   ```

   Or, if you prefer using `pip` (make sure to generate a `requirements.txt` if needed):

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**

   You can either export the required environment variables in your shell:

   ```bash
   export OPENAI_API_KEY=sk-your-key-here
   export TAVILY_API_KEY=tvly-your-key-here
   export COHERE_API_KEY=your-cohere-key-here
   export CRAWL4AI_API_TOKEN=your_secret_token
   export REDIS_HOST=localhost
   export REDIS_PORT=6379
   ```

   **OR**

   Copy the example environment file and update it:

   ```bash
   cp .env.example .env
   ```

---

## Running Dependencies with Docker

Plexy relies on both Redis and Crawl4AI being available. You can quickly set these up using Docker:

1. **Run Redis** in Docker:

   ```bash
   docker run -d --name my-redis -p 6379:6379 redis
   ```

   This starts Redis on port 6379. Check logs with:

   ```bash
   docker logs my-redis
   ```

2. **Run Crawl4AI** in Docker:

   ```bash
   docker run -d -p 11235:11235 -e CRAWL4AI_API_TOKEN=your_secret_token unclecode/crawl4ai:basic
   ```

   Verify that it’s accessible at [http://localhost:11235](http://localhost:11235).

---

## Usage

Since Plexy currently only supports the OpenAI model, you can run it directly from the command line without specifying a model.

### Running the CLI

```bash
plexy --debug --max-iters 2
```

### Command Line Options

- `--tool-dir`: Provide a path to a folder containing extra tools (optional).
- `--debug`: Enable debug output for troubleshooting.
- `--max-iters`: Set the maximum number of decision iterations before forcing an answer (default: `2`).

After starting Plexy, type your questions at the prompt. To exit, enter `exit`, `q`, or `quit`.

---

## Development

For development, ensure that your environment variables are correctly set in your shell or in the `.env` file, and that both Redis and Crawl4AI are running.
