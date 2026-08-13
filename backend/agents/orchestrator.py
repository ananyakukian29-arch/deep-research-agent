import re
import json
import time
import os
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from backend.config import settings
from backend.memory.state import AgentState

GROQ_API_KEY = settings.GROQ_API_KEY

# Bypassing the Google daily cap by using Groq. 
# Temperature locked to 0.0 for deterministic, strict outputs.
llm = ChatGroq(
    model="llama-3.1-8b-instant",
    api_key=GROQ_API_KEY,
    temperature=0.0
)

# Groq Pricing for llama-3.1-8b-instant (Per 1M Tokens)
INPUT_COST_1M = 0.05
OUTPUT_COST_1M = 0.08

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

def orchestrator_node(state: AgentState) -> dict:
    """The Orchestrator Agent scopes the user prompt and generates a research plan."""
    start_time = time.perf_counter()
    request = state.get("user_request", "")
    
    # Initialize metrics if missing from state
    metrics = state.get("metrics", {"total_cost": 0.0, "total_prompt_tokens": 0, "total_completion_tokens": 0, "node_latencies": {}})

    # Runtime key guard
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set. Check your .env file.")

    # The STRICT, deterministic system prompt
    sys_prompt = (
        "You are a precise technical research planner. Analyze the user prompt and extract ALL specific terms, "
        "frameworks (e.g., ExecuTorch, TFLite), metrics (e.g., RAM usage, inference speed, FPS), definitions "
        "(e.g., nodes, edges), and hardware constraints.\n\n"
        "Break the user request into exactly 3 searchable sub-topics. EVERY sub-topic MUST explicitly include "
        "the exact keywords and metrics extracted from the prompt so the web search agent is forced to look for them.\n\n"
        "Return ONLY a raw JSON array of 3 strings. Example: [\"topic 1\", \"topic 2\", \"topic 3\"]"
    )

    response = invoke_with_backoff(
        llm=llm,
        messages=[
            SystemMessage(content=sys_prompt),
            HumanMessage(content=request),
        ],
    )

    # Normalise content
    raw_content = response.content
    if isinstance(raw_content, list):
        raw_content = "".join(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in raw_content
        )

    # JSON Parsing with robust regex fallback
    try:
        clean_json = re.sub(r"^```(?:json)?\s*", "", raw_content.strip())
        clean_json = re.sub(r"\s*```$", "", clean_json).strip()
        plan = json.loads(clean_json)
        if not isinstance(plan, list):
            raise ValueError("Parsed value is not a list")
    except (json.JSONDecodeError, ValueError):
        # Graceful fallback: treat the entire request as a single topic.
        plan = [request]

    # Metrics Extraction & Calculation
    latency = round(time.perf_counter() - start_time, 2)
    
    prompt_tokens = 0
    completion_tokens = 0
    
    # Safely extract tokens depending on LangChain version metadata structure
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        prompt_tokens = response.usage_metadata.get("input_tokens", 0)
        completion_tokens = response.usage_metadata.get("output_tokens", 0)
    elif hasattr(response, "response_metadata") and "token_usage" in response.response_metadata:
        prompt_tokens = response.response_metadata["token_usage"].get("prompt_tokens", 0)
        completion_tokens = response.response_metadata["token_usage"].get("completion_tokens", 0)

    # Calculate actual cost in dollars
    cost = ((prompt_tokens / 1_000_000) * INPUT_COST_1M) + ((completion_tokens / 1_000_000) * OUTPUT_COST_1M)
    
    # Update state metrics
    metrics["total_cost"] += cost
    metrics["total_prompt_tokens"] += prompt_tokens
    metrics["total_completion_tokens"] += completion_tokens
    metrics["node_latencies"]["orchestrator"] = latency

    return {"research_plan": plan, "metrics": metrics}