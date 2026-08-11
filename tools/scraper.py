import requests
from bs4 import BeautifulSoup

def scrape_url(url: str) -> str:
    """Scrapes paragraph text from a given URL."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract text from paragraphs
        paragraphs = soup.find_all('p')
        text = "\n".join([p.get_text() for p in paragraphs])
        
        # Truncate to avoid massive token usage on single pages
        return text[:5000] if text else "No readable content found."
    except Exception as e:
        return f"Failed to scrape {url}: {str(e)}"