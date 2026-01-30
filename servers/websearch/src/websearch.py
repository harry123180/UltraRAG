"""Web Search Server for UltraRAG.

This server provides web search capabilities using Gemini for external queries.
Since Gemini has training data up to a certain date, it can answer general knowledge
questions. For real-time information, consider using a dedicated search API.
"""
import asyncio
import os
from typing import Any, Dict, List, Optional

from ultrarag.server import UltraRAG_MCP_Server

app = UltraRAG_MCP_Server("websearch")


class WebSearch:
    """Web search class using Gemini for knowledge queries."""

    def __init__(self, mcp_inst: UltraRAG_MCP_Server):
        mcp_inst.tool(
            self.websearch_init,
            output="api_key,search_depth,max_results->None",
        )
        mcp_inst.tool(
            self.search,
            output="q_ls,search_depth,max_results->web_results",
        )
        mcp_inst.tool(
            self.batch_search,
            output="queries,search_depth,max_results->web_results_list",
        )

        self.client = None
        self.model = None
        self.default_max_results = 5
        self.timeout_seconds = 30  # Default timeout

    def websearch_init(
        self,
        api_key: Optional[str] = None,
        search_depth: str = "basic",
        max_results: int = 5,
        timeout_seconds: int = 30,
    ) -> None:
        """Initialize Gemini client for web knowledge queries.

        Args:
            api_key: Google API key (or set GOOGLE_API_KEY env var)
            search_depth: Not used (kept for compatibility)
            max_results: Maximum number of results per query
            timeout_seconds: Timeout for web search in seconds (default 30)
        """
        self.timeout_seconds = timeout_seconds
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError(
                "google-generativeai is not installed. "
                "Install with: pip install google-generativeai"
            )

        api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "api_key is required. Set GOOGLE_API_KEY env var or pass api_key parameter."
            )

        genai.configure(api_key=api_key)

        # Create model for web knowledge queries
        self.client = genai
        self.model = genai.GenerativeModel(model_name="gemini-3-pro-preview")
        self.default_max_results = max_results

        app.logger.info("Gemini WebSearch initialized")

    async def search(
        self,
        q_ls: List[str],
        search_depth: Optional[str] = None,
        max_results: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Perform web knowledge search using Gemini.

        Args:
            q_ls: List of query strings (uses first element)
            search_depth: Not used (kept for compatibility)
            max_results: Not used (kept for compatibility)

        Returns:
            Dictionary with 'web_results' containing search-like results
        """
        if self.model is None:
            raise RuntimeError("WebSearch not initialized. Call websearch_init first.")

        # Extract first query from list
        query = q_ls[0] if q_ls else ""

        try:
            # Use Gemini to answer the query as if searching the web
            search_prompt = f"""你是一個網路搜尋助手。請針對以下問題提供詳細的資訊：

問題：{query}

請提供：
1. 問題的直接答案
2. 相關的背景資訊
3. 如果是時事問題，請說明你的知識截止日期可能無法提供最新資訊

請用繁體中文回答。"""

            # Apply timeout to prevent long waits
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.model.generate_content,
                        search_prompt,
                    ),
                    timeout=self.timeout_seconds,
                )
            except asyncio.TimeoutError:
                app.logger.warning(f"Web search timeout ({self.timeout_seconds}s) for query: '{query}'")
                return {
                    "web_results": [[]],
                    "query": query,
                    "error": f"搜尋逾時 ({self.timeout_seconds}秒)",
                    "timeout": True,
                }

            answer_text = ""
            if response.candidates:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    answer_text = candidate.content.parts[0].text

            # Format as search results
            results = []
            if answer_text:
                # Split answer into chunks to simulate multiple search results
                paragraphs = [p.strip() for p in answer_text.split('\n\n') if p.strip()]

                for i, para in enumerate(paragraphs[:3]):  # Max 3 results
                    results.append({
                        "title": f"Gemini 知識庫 - 結果 {i+1}",
                        "url": "",
                        "content": para,
                        "score": 1.0 - (i * 0.1),
                    })

                # If no paragraphs, use whole answer
                if not results:
                    results.append({
                        "title": "Gemini 知識庫",
                        "url": "",
                        "content": answer_text[:1000],
                        "score": 1.0,
                    })

            app.logger.info(f"Gemini search completed for '{query}', found {len(results)} results")

            return {
                "web_results": [results],  # Wrapped in list for per-question format
                "query": query,
                "answer": answer_text,
            }

        except Exception as e:
            app.logger.error(f"Gemini search error for query '{query}': {e}")
            return {
                "web_results": [[]],  # Wrapped in list for per-question format
                "query": query,
                "error": str(e),
            }

    async def batch_search(
        self,
        queries: List[str],
        search_depth: Optional[str] = None,
        max_results: Optional[int] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Perform web search for multiple queries.

        Args:
            queries: List of search query strings
            search_depth: Not used (kept for compatibility)
            max_results: Not used (kept for compatibility)

        Returns:
            Dictionary with 'web_results_list' containing results for each query
        """
        if self.model is None:
            raise RuntimeError("WebSearch not initialized. Call websearch_init first.")

        results_list = []
        for query in queries:
            result = await self.search([query], search_depth, max_results)
            results_list.append(result)

        return {"web_results_list": results_list}


if __name__ == "__main__":
    WebSearch(app)
    app.run(transport="stdio")
