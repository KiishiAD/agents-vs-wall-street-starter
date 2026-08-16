"""Tavily web-search client used by the signal extractor's sub-agents.

Each sub-agent web-searches for the evidence behind its signal before the
reasoning inspector checks whether the answer is grounded in what it read. When
`TAVILY_API_KEY` is set this issues a real Tavily query; otherwise it falls back
to the frozen corpus and records the query it *would* have run, so the run stays
deterministic and offline-reproducible while the web-search stage is always
visible in the trace.

Dependency-free (stdlib urllib); never raises into the pipeline — any transport
error degrades to an empty result set.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

TAVILY_ENDPOINT = "https://api.tavily.com/search"
DEFAULT_TIMEOUT = 8.0


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str


class TavilyClient:
    """Thin Tavily search client. Reads the key from `TAVILY_API_KEY` by default."""

    def __init__(self, api_key: str | None = None, *, timeout: float = DEFAULT_TIMEOUT) -> None:
        self.api_key = api_key or os.environ.get("TAVILY_API_KEY")
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def search(self, query: str, *, max_results: int = 5, search_depth: str = "basic") -> list[SearchResult]:
        """Return search results for `query`, or an empty list when disabled or on error."""
        if not self.enabled:
            return []
        payload = json.dumps(
            {
                "api_key": self.api_key,
                "query": query,
                "max_results": max_results,
                "search_depth": search_depth,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            TAVILY_ENDPOINT, data=payload, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError, OSError):
            return []
        results = data.get("results", []) if isinstance(data, dict) else []
        return [
            SearchResult(
                title=str(item.get("title", "")),
                url=str(item.get("url", "")),
                snippet=str(item.get("content", ""))[:280],
            )
            for item in results
            if isinstance(item, dict)
        ]


def evidence_query(company: str, signal: str, period: str) -> str:
    """The query a sub-agent runs to find the evidence behind a signal."""
    return f"{company} {signal} {period} guidance outlook"
