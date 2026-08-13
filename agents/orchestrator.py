import re
import json
import time
import os
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from config.settings import GROQ_API_KEY
from memory.state import AgentState

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Bypassing the Google daily cap by using Groq. 
# Temperature locked to 0.0 for deterministic, strict outputs.
llm = ChatGroq(
    model="llama-3.1-8b-instant",
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

def orchestrator_node(state: AgentState) -> dict:
    """The Orchestrator Agent scopes the user prompt and generates a research plan."""
    request = state.get("user_request", "")

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

    return {"research_plan": plan}