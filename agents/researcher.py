import time
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from config.settings import GOOGLE_API_KEY
from tools.search import perform_search
from memory.state import AgentState

# Bug 1 note: gemini-3.5-flash IS the correct model for this API key.
# Live model list confirmed it is available and supported for generateContent.
llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash",
    api_key=GOOGLE_API_KEY,
    temperature=0.2
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


def researcher_node(state: AgentState) -> dict:
    """The Researcher Agent executes a search and synthesis loop for a specific topic."""
    topic = state.get("current_topic", "")

    # Runtime key guard — surfaces a clear error via the graph rather than a crash.
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY is not set. Check your .env file.")

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
    # Normalise content: Gemini may return a list of content blocks.
    raw_content = response.content
    if isinstance(raw_content, list):
        raw_content = "".join(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in raw_content
        )

    # 3. Format for memory insertion.
    # Bug 2 fixed: use raw_content (normalised string) not response.content
    # (which could still be a list of dicts, causing silent data corruption).
    new_research = [f"### Sub-Topic: {topic}\n{raw_content}\n"]

    # operator.add in the State schema will append this to the existing list.
    # Bug 4 fix: increment loop_count so the router can enforce the loop cap.
    return {
        "collected_research": new_research,
        "loop_count": state.get("loop_count", 0) + 1
    }