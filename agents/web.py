"""F4 — Web agent: fresh external info via Tavily (optional, graceful skip)."""

import sys

import config


def run(question: str) -> str:
    if not config.TAVILY_API_KEY:
        return "(web agent skipped: TAVILY_API_KEY not set)"
    try:
        from tavily import TavilyClient
        res = TavilyClient(api_key=config.TAVILY_API_KEY).search(question, max_results=3)
        return "\n---\n".join(f"[{r['url']}]\n{r['content'][:400]}"
                              for r in res.get("results", [])) or "(no web results)"
    except Exception as e:
        return f"(web agent error: {e})"


if __name__ == "__main__":
    print(run(" ".join(sys.argv[1:]) or "digital banking churn trends 2026"))
