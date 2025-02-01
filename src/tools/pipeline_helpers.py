import os
import json
import redis
import requests
import time
import concurrent.futures
from datetime import datetime
from typing import Optional, List

from cohere import Client as CohereClient
from tavily import TavilyClient
from pydantic import BaseModel

from core.logger import log
from core.config import (
    TAVILY_API_KEY,
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    OPENAI_API_KEY,
)
from models.openai import OpenAIModel
from core.decision import Decision

##############################################################################
# 1) Redis + Crawl4AI caching
##############################################################################

CRAWL4AI_BASE_URL = os.getenv("CRAWL4AI_BASE_URL", "http://localhost:11235")
CRAWL4AI_API_TOKEN = os.getenv("CRAWL4AI_API_TOKEN", "your_secret_token")

rclient = redis.Redis(
    host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True
)


def cache_key_for_url(url: str) -> str:
    return f"crawl4ai:markdown:{url}"


def fetch_markdown_with_crawl4ai(
    url: str, priority: int = 10, timeout_sec: int = 240
) -> Optional[str]:
    headers = {}
    if CRAWL4AI_API_TOKEN:
        headers["Authorization"] = f"Bearer {CRAWL4AI_API_TOKEN}"
    resp = requests.post(
        f"{CRAWL4AI_BASE_URL}/crawl",
        headers=headers,
        json={"urls": url, "priority": priority},
    )
    resp.raise_for_status()
    task_id = resp.json()["task_id"]
    start_time = time.time()
    while True:
        if time.time() - start_time > timeout_sec:
            raise TimeoutError(f"Crawl job timed out for {url}")
        status_resp = requests.get(
            f"{CRAWL4AI_BASE_URL}/task/{task_id}", headers=headers
        )
        status_resp.raise_for_status()
        js = status_resp.json()
        if js["status"] == "completed":
            if "markdown" in js["result"]:
                return js["result"]["markdown"]
            return None
        elif js["status"] == "failed":
            raise RuntimeError(
                f"Crawl4AI job failed for {url}: {js.get('error', 'unknown')}"
            )
        time.sleep(2)


def get_webpage_text(url: str) -> Optional[str]:
    key = cache_key_for_url(url)
    cached_val = rclient.get(key)
    if cached_val:
        return cached_val
    try:
        text = fetch_markdown_with_crawl4ai(url)
        if text:
            rclient.set(key, text, ex=60 * 60 * 24 * 14)
            return text
        else:
            return None
    except Exception as e:
        log(f"Error crawling {url}: {e}", error=True)
        return None


def enrich_docs_with_cache(docs: list) -> list:
    """
    If the doc has short content, try to fetch from crawl4ai.
    Store it in doc['content'] if we successfully get more text.
    """
    MIN_TEXT_LEN = 100
    for doc in docs:
        # doc.get(...,"") ensures we won't crash if 'content' is missing
        curr_content = doc.get("content", "")
        if len(curr_content) < MIN_TEXT_LEN:
            url = doc.get("url", "")
            if url.startswith("http"):
                new_text = get_webpage_text(url)
                if new_text and len(new_text) > len(curr_content):
                    doc["content"] = new_text
    return docs


##############################################################################
# 2) Tavily + Score-based Filter
##############################################################################


def single_tavily_search(query: str) -> list:
    tv_client = TavilyClient(api_key=TAVILY_API_KEY)
    response = tv_client.search(
        query=query,
        include_answer=False,
        include_raw_content=True,
        max_results=20,
    )
    results = response.get("results", [])
    docs = []
    for item in results:
        doc_text = item.get("raw_content") or item.get("content") or ""
        score_val = item.get("score", 0.0)
        docs.append(
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                # store in content for consistency
                "content": doc_text,
                "score": score_val,
            }
        )
    return docs


def filter_by_score_dropoff(docs: list, drop_threshold: float = 0.15) -> list:
    if not docs:
        return []
    sorted_docs = sorted(docs, key=lambda x: x["score"], reverse=True)
    top_score = sorted_docs[0]["score"]
    cutoff = top_score - drop_threshold
    return [d for d in sorted_docs if d["score"] >= cutoff]


def tavily_in_parallel(search_queries: List[str], pages_to_fetch: int = 1) -> list:
    """
    Run Tavily searches in parallel for the provided queries.
    Added pages_to_fetch for possible pagination, but it’s optional.
    """
    all_docs = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for q in search_queries:
            for page in range(1, pages_to_fetch + 1):
                futures.append(executor.submit(single_tavily_search, q))
        for future in concurrent.futures.as_completed(futures):
            all_docs.extend(future.result())

    return filter_by_score_dropoff(all_docs, drop_threshold=0.15)


##############################################################################
# 3) Deduplicate + Cohere Re-Rank
##############################################################################


def deduplicate_docs(docs: list) -> list:
    unique = []
    seen = set()
    for d in docs:
        key = (d.get("url", ""), d.get("title", ""))
        if key not in seen:
            seen.add(key)
            unique.append(d)
    return unique


cohere_client = CohereClient(os.getenv("COHERE_API_KEY", ""))


def cohere_rerank(user_query: str, docs: list, top_n: int = 10) -> list:
    """
    Re-rank the documents with Cohere.
    Skip docs that have 'error' or no 'content'.
    """
    if not docs:
        return []

    valid_docs = []
    for d in docs:
        if "error" in d:
            log(f"Skipping doc with error: {d['error']}", error=False)
            continue
        if "content" not in d:
            log(f"Skipping doc missing 'content' field: {d}", error=False)
            continue
        valid_docs.append(d)

    if not valid_docs:
        log("No valid docs to re-rank, returning empty list.", error=False)
        return []

    doc_texts = [doc["content"] for doc in valid_docs]
    query_with_date = f"{user_query} [Date: {datetime.now().strftime('%Y-%m-%d')}]"

    try:
        resp = cohere_client.rerank(
            model="rerank-v3.5",
            query=query_with_date,
            documents=doc_texts,
            top_n=min(top_n, len(doc_texts)),
        )
    except Exception as e:
        log(f"Cohere re-rank error: {e}", error=True)
        return []

    sorted_indices = [r.index for r in resp.results]
    return [valid_docs[i] for i in sorted_indices]


##############################################################################
# 4) Decision Step - Calling the LLM for a structured Decision
##############################################################################


def call_decision_llm(conversation_history: list, debug: bool = False) -> Decision:
    """
    Single entry point for structured 'Decision' JSON from the LLM.

    * We do NOT rely on a separate final-answer function.
    * The 'system' messages in conversation_history must contain the inline-citation instructions
      if we want the final answer to contain [1], [2], etc.
    """
    if debug:
        from core.logger import log

        log(f"Decision prompt messages: {conversation_history}", error=False)

    model = OpenAIModel()
    try:
        # We'll parse as a 'Decision' pydantic object
        completion = model.client.beta.chat.completions.parse(
            model=model.model_name,
            messages=conversation_history,
            response_format=Decision,
            temperature=0.0,  # keep it zero for less creative disobedience
            max_tokens=500,
        )
    except Exception as e:
        if debug:
            log(f"Decision LLM parse error: {e}", error=True)
        return None

    choice = completion.choices[0].message
    if hasattr(choice, "refusal") and choice.refusal:
        conversation_history.append(
            {
                "role": "assistant",
                "content": "I'm sorry, but I cannot fulfill that request.",
            }
        )
        return None

    return choice.parsed
