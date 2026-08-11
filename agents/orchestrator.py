import re
import json
import time
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from config.settings import GOOGLE_API_KEY
from memory.state import AgentState

# Bug 1 note: gemini-3.5-flash IS the correct model for this API key.
# Live model list confirmed it is available and supported for generateContent.
llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash",
    api_key=GOOGLE_API_KEY,
    temperature=0.1
)


def invoke_with_backoff(llm, messages, max_retries=3):
    for attempt in range(max_retries):
        try:
            return llm.invoke(messages)
        except Exception as e:
            if "429" in str(e).lower() or "resource_exhausted" in str(e).lower():
                print(f"429 Rate Limit Hit. Sleeping 16s... (Attempt {attempt + 1})")
                time.sleep(16)
            else:
                raise
    raise Exception("CRITICAL: Max retries exceeded.")


def orchestrator_node(state: AgentState) -> dict:
    """The Orchestrator Agent scopes the user prompt and generates a research plan."""
    request = state.get("user_request", "")

    # Runtime key guard — surfaces a clear error via the graph rather than a crash.
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY is not set. Check your .env file.")

    sys_prompt = (
        "You are a master research planner. Break the user's request into exactly 3 distinct, "
        "searchable sub-topics. Return ONLY a valid JSON list of strings. Do not include markdown formatting or commentary."
    )

    response = invoke_with_backoff(
        llm=llm,
        messages=[
            SystemMessage(content=sys_prompt),
            HumanMessage(content=request),
        ],
    )

    # Normalise content: Gemini may return a list of content blocks.
    raw_content = response.content
    if isinstance(raw_content, list):
        raw_content = "".join(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in raw_content
        )

    # Bug 3 fix: use regex to strip markdown fences as literal substrings,
    # NOT str.strip(chars) which strips individual characters and corrupts JSON.
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

