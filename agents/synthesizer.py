import time
import os
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from config.settings import GROQ_API_KEY
from memory.state import AgentState

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Initializing Groq's Llama 3 with temperature=0.0 for deterministic compliance
llm = ChatGroq(
    model="openai/gpt-oss-120b",
    api_key=GROQ_API_KEY,
    temperature=0.0
)


def invoke_with_backoff(llm, messages, max_retries=5):
    """Traps rate limits AND network/DNS blips with exponential backoff retries."""
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


def synthesizer_node(state: AgentState) -> dict:
    """The Synthesizer Agent compiles collected research into a final compliant Markdown report."""
    research_list = state.get("collected_research", [])
    research_data = "\n".join(research_list)
    user_request = state.get("user_request", "Generate a detailed report.")

    # Runtime key guard
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set. Check your .env file.")

    # Prevent TPM blowouts by capping the raw research text length
    MAX_RESEARCH_CHARS = 8000
    if len(research_data) > MAX_RESEARCH_CHARS:
        research_data = research_data[:MAX_RESEARCH_CHARS] + "\n...[Research text truncated to comply with API limits]..."

    # System prompt sets the role. The actual rules go at the bottom now.
    sys_prompt = (
        "You are an elite technical writer. Synthesize the provided research into a highly structured, "
        "professional Markdown report."
    )

    # THE SANDWICH: Put the massive data dump first, and the critical rules LAST.
    msg = f"""
Compiled Research Data:
{research_data}

=========================================
FINAL INSTRUCTION REMINDER:
You are answering the following user request: "{user_request}"

CRITICAL COMPLIANCE CHECK - YOU MUST FOLLOW THESE RULES:
1. KEYWORDS & ENTITIES: Dedicate sections or bullet points to specific frameworks (e.g., ExecuTorch, TFLite) if requested.
2. HARDWARE METRICS: You MUST include FPS/latency and RAM/memory usage if comparing models. If missing, state they are unavailable and estimate based on architecture.
3. DEFINITIONS: Explicitly define 'nodes' and 'edges' with domain examples (e.g., warehouses) if asked.
4. LENGTH TARGET: If a word limit is specified (e.g., 'under 500 words'), target EXACTLY 300 to 350 words. Do not write a massive essay. Keep paragraphs short and use concise bullet points.
5. FORMATTING: Use clean Markdown with headers and bold text.
"""

    response = invoke_with_backoff(
        llm=llm,
        messages=[
            SystemMessage(content=sys_prompt),
            HumanMessage(content=msg)
        ]
    )

    # Extract string content whether returned as a string or list of content blocks
    raw_content = response.content
    if isinstance(raw_content, list):
        raw_content = "".join(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in raw_content
        )

    return {"final_report": raw_content}