import time
import os
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from backend.config import settings
from backend.tools.search import perform_search
from backend.memory.state import AgentState


GROQ_API_KEY = settings.GROQ_API_KEY

# Groq Pricing for llama-3.1-8b-instant (Per 1M Tokens)
INPUT_COST_1M = 0.05
OUTPUT_COST_1M = 0.08

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    api_key=GROQ_API_KEY,
    temperature=0.0
)


def invoke_with_backoff(llm, messages, max_retries=5):
    """Traps rate limits AND network/DNS blips with retries."""
    for attempt in range(max_retries):
        try:
            return llm.invoke(messages)
        except Exception as e:
            error_str = str(e).lower()
            is_rate_limit = "429" in error_str or "resource_exhausted" in error_str
            is_network_error = any(
                k in error_str for k in ("getaddrinfo", "connecterror", "connection", "timeout", "unavailable")
            )
            
            if is_rate_limit or is_network_error:
                sleep_time = 16 if is_rate_limit else (5 * (attempt + 1))
                reason = "429 Rate Limit" if is_rate_limit else "Network/DNS Failure"
                print(f"\n[!] {reason} detected. Sleeping {sleep_time}s... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(sleep_time)
            else:
                raise
    raise Exception("CRITICAL: Max retries exceeded due to persistent network or rate-limit failures.")


def researcher_node(state: AgentState) -> dict:
    """The Researcher Agent executes a search and synthesis loop for a specific topic."""
    start_time = time.perf_counter()
    topic = state.get("current_topic", "")
    metrics = state.get("metrics", {"total_cost": 0.0, "total_prompt_tokens": 0, "total_completion_tokens": 0, "node_latencies": {}})
    loop_count = state.get("loop_count", 0)

    # Runtime key guard — surfaces a clear error via the graph rather than a crash.
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set. Check your .env file.")

    # 1. Execute the search tool
    search_results = perform_search(topic)

    # 2. Evaluate and extract core facts
    sys_prompt = (
        "You are an analytical research assistant. Read the provided search data and extract the most critical facts. "
        "Ignore fluff and marketing language. Write a concise, bulleted summary."
    )
    msg = f"Topic: {topic}\n\nSearch Data:\n{search_results}\n\nExtract and summarize the core facts."

    response = invoke_with_backoff(
        llm=llm,
        messages=[
            SystemMessage(content=sys_prompt),
            HumanMessage(content=msg),
        ],
    )

    # Normalise content
    raw_content = response.content
    if isinstance(raw_content, list):
        raw_content = "".join(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in raw_content
        )

    # 3. Format for memory insertion.
    new_research = [f"### Sub-Topic: {topic}\n{raw_content}\n"]

    # Metrics Extraction & Calculation
    latency = round(time.perf_counter() - start_time, 2)
    prompt_tokens = 0
    completion_tokens = 0

    if hasattr(response, "usage_metadata") and response.usage_metadata:
        prompt_tokens = response.usage_metadata.get("input_tokens", 0)
        completion_tokens = response.usage_metadata.get("output_tokens", 0)
    elif hasattr(response, "response_metadata") and "token_usage" in response.response_metadata:
        prompt_tokens = response.response_metadata["token_usage"].get("prompt_tokens", 0)
        completion_tokens = response.response_metadata["token_usage"].get("completion_tokens", 0)

    cost = ((prompt_tokens / 1_000_000) * INPUT_COST_1M) + ((completion_tokens / 1_000_000) * OUTPUT_COST_1M)

    metrics["total_cost"] += cost
    metrics["total_prompt_tokens"] += prompt_tokens
    metrics["total_completion_tokens"] += completion_tokens
    metrics["node_latencies"][f"researcher_loop_{loop_count}"] = latency

    return {
        "collected_research": new_research,
        "loop_count": loop_count + 1,
        "metrics": metrics
    }