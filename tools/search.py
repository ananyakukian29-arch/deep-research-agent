from tavily import TavilyClient
from config.settings import TAVILY_API_KEY

# Bug 6 fix: instantiate the client once at module load and reuse it.
# Re-creating TavilyClient on every search call wastes connection setup time
# and prevents TCP keep-alive reuse across the 3 sub-topic searches.
_client = TavilyClient(api_key=TAVILY_API_KEY) if TAVILY_API_KEY else None


def perform_search(query: str, max_results: int = 3) -> str:
    """
    Executes a search using the Tavily API and returns a formatted string of results.
    """
    if not _client:
        return "Error: Tavily API key not found. Check your .env file."

    try:
        # We use search_depth="advanced" to get better contextual snippets
        response = _client.search(
            query=query,
            search_depth="advanced",
            max_results=max_results
        )

        results = response.get("results", [])
        if not results:
            return "No relevant results found."

        # Format the output so the LLM can easily read it
        formatted_results = ""
        for res in results:
            formatted_results += f"Source: {res['url']}\nContent: {res['content']}\n\n"

        return formatted_results

    except Exception as e:
        return f"Search execution failed: {str(e)}"