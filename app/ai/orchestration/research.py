from typing import Any

import httpx


class ResearchEngine:

    SEMANTIC_SCHOLAR = (
        "https://api.semanticscholar.org/graph/v1/paper/search"
    )

    CROSSREF = (
        "https://api.crossref.org/works"
    )

    def __init__(self, timeout=15.0):

        self.timeout = timeout

    def _get(self, url, params):

        try:

            response = httpx.get(
                url,
                params=params,
                timeout=self.timeout,
                follow_redirects=True,
                headers={
                    "User-Agent":
                    "J-SGENT/1.0 research-agent"
                },
            )

            response.raise_for_status()

            return response.json()

        except Exception as exc:

            return {
                "error": str(exc)
            }

    def search_papers(
        self,
        query: str,
        limit: int = 8,
    ):

        data = self._get(
            self.SEMANTIC_SCHOLAR,
            {
                "query": query,
                "limit": min(limit, 20),
                "fields": (
                    "title,"
                    "abstract,"
                    "year,"
                    "authors,"
                    "url,"
                    "citationCount,"
                    "openAccessPdf,"
                    "externalIds"
                ),
            },
        )

        if "error" in data:
            return data

        papers = []

        for paper in data.get(
            "data",
            []
        ):

            papers.append({

                "title":
                    paper.get("title"),

                "year":
                    paper.get("year"),

                "abstract":
                    paper.get("abstract"),

                "url":
                    paper.get("url"),

                "citation_count":
                    paper.get(
                        "citationCount",
                        0
                    ),

                "open_access_pdf":
                    (
                        paper.get(
                            "openAccessPdf"
                        ) or {}
                    ).get("url"),

                "doi":
                    (
                        paper.get(
                            "externalIds"
                        ) or {}
                    ).get("DOI"),

            })

        return papers

    def search_crossref(
        self,
        query: str,
        limit: int = 8,
    ):

        data = self._get(
            self.CROSSREF,
            {
                "query.bibliographic": query,
                "rows": min(limit, 20),
            },
        )

        if "error" in data:
            return data

        results = []

        for item in (
            data
            .get("message", {})
            .get("items", [])
        ):

            results.append({

                "title":
                    (
                        item.get("title")
                        or [None]
                    )[0],

                "doi":
                    item.get("DOI"),

                "published":
                    item.get(
                        "published-print"
                    )
                    or item.get(
                        "published-online"
                    ),

                "journal":
                    item.get(
                        "container-title",
                        [None]
                    )[0],

                "publisher":
                    item.get(
                        "publisher"
                    ),

                "url":
                    item.get("URL"),

                "type":
                    item.get("type"),

            })

        return results

    def research(
        self,
        query: str,
    ) -> dict[str, Any]:

        return {

            "query": query,

            "semantic_scholar":
                self.search_papers(query),

            "crossref":
                self.search_crossref(query),

        }
