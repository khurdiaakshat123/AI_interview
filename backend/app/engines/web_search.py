import re
import urllib.parse
from typing import List, Dict, Any, Optional
import httpx
from bs4 import BeautifulSoup

class WebSearchEngine:
    """
    Real-time web search engine for technical interview grounding.
    Extracts real interview questions, topics, and company standards
    to ground LLM question formulation and evaluation.
    """
    _cache: Dict[str, List[str]] = {}

    @classmethod
    def search_interview_trends(cls, company: str, role: str, max_results: int = 4) -> List[str]:
        query = f"{company} {role} technical interview questions interview experiences"
        cache_key = f"{company.lower()}:{role.lower()}"
        if cache_key in cls._cache:
            return cls._cache[cache_key]

        snippets = cls._fetch_duckduckgo_snippets(query, max_results=max_results)
        if not snippets:
            # Fallback query
            snippets = cls._fetch_duckduckgo_snippets(f"{role} interview questions technical deep dive", max_results=max_results)

        cls._cache[cache_key] = snippets
        return snippets

    @classmethod
    def _fetch_duckduckgo_snippets(cls, query: str, max_results: int = 4) -> List[str]:
        snippets: List[str] = []
        try:
            encoded_query = urllib.parse.quote_plus(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            with httpx.Client(timeout=5.0, follow_redirects=True) as client:
                resp = client.get(url, headers=headers)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    raw_snippets = soup.find_all("a", class_="result__snippet")
                    for s in raw_snippets[:max_results]:
                        text = s.get_text().strip()
                        text = re.sub(r"\s+", " ", text)
                        if len(text) > 30 and text not in snippets:
                            snippets.append(text)
        except Exception as e:
            print(f"[WebSearchEngine] Search failed for '{query}': {e}")

        return snippets
