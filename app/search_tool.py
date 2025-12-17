# search_tool.py
"""
Minimal wrapper using ddgs or duckduckgo_search.
Handles rate-limit gracefully and returns top results as list of dicts.
"""
from typing import List, Dict
import time

# prefer ddgs if available
try:
    from ddgs import DDGS
    DDGS_AVAILABLE = True
except Exception:
    DDGS_AVAILABLE = False

# fallback to duckduckgo_search
try:
    from duckduckgo_search import ddg
    DDG_FALLBACK = True
except Exception:
    DDG_FALLBACK = False

def web_search(query: str, limit: int = 3, pause: float = 0.5) -> List[Dict]:
    results = []
    try:
        if DDGS_AVAILABLE:
            with DDGS() as ddgs:
                for r in ddgs.text(query, timelimit=10, output="json"):
                    # ddgs yields multiple; break at limit
                    results.append({"title": r.get("title"), "body": r.get("body"), "url": r.get("href")})
                    if len(results) >= limit:
                        break
        elif DDG_FALLBACK:
            res = ddg(query, max_results=limit)
            for r in res:
                results.append({"title": r.get("title"), "body": r.get("body") or r.get("snippet"), "url": r.get("href")})
        else:
            return []
    except Exception as e:
        # graceful fallback
        return [{"error": f"search_error: {str(e)}"}]
    time.sleep(pause)
    return results
