import time
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from config.settings import GROQ_API_KEY
from memory.state import AgentState

# Initializing Groq's Llama 3 for high-speed document synthesis
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=GROQ_API_KEY,
    temperature=0.3
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


def synthesizer_node(state: AgentState) -> dict:
    """The Synthesizer Agent compiles the collected research into a final polished document."""
    research_data = "\n".join(state.get("collected_research", []))
    user_request = state.get("user_request", "Generate a detailed report.")

    # Runtime key guard — surfaces a clear error via the graph rather than a crash.
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set. Check your .env file.")

    sys_prompt = (
        "You are an expert technical writer. Your task is to synthesize the provided research data into "
        "a highly structured, professional Markdown report that answers the original user request. "
        "Include an Introduction, Detailed Body Sections with clear headings, and a Conclusion."
    )

    msg = f"Original Request: {user_request}\n\nCompiled Research Data:\n{research_data}"

    response = invoke_with_backoff(
        llm=llm,
        messages=[
            SystemMessage(content=sys_prompt),
            HumanMessage(content=msg)  # <-- Use 'msg' here, not 'request'
        ]
    )

    # Safely extract string content whether returned as string or list
    raw_content = response.content
    if isinstance(raw_content, list):
        raw_content = "".join(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in raw_content
        )

    return {"final_report": raw_content}