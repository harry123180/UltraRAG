"""Agent Router Server for Enterprise Agent POC.

This server provides simple routing logic to determine whether a query
should be answered directly, use RAG, or use web search.
"""
import re
from typing import Any, Dict, List, Optional

from ultrarag.server import UltraRAG_MCP_Server

app = UltraRAG_MCP_Server("agent_router")


# Simple greeting patterns
GREETING_PATTERNS = [
    r'^(hi|hello|hey|嗨|哈囉|你好|您好|早安|午安|晚安)[\s!！。]*$',
    r'^(謝謝|感謝|thank|thanks)[\s!！。]*$',
    r'^(bye|goodbye|再見|掰掰)[\s!！。]*$',
]

# Keywords indicating need for internal docs
INTERNAL_KEYWORDS = [
    # 企業文件
    'SOP', '標準作業', '內部', '公司', '企業', '流程', '規定', '規範',
    '辦法', '守則', '部門', '員工', '人資', 'HR', '請假', '報銷',
    '出差', '考勤', '績效', '薪資', '採購', '報價', '合約',
    '知識庫', '文件', '文檔', '資料庫', 'knowledge', 'document',
    # 技術文件關鍵字 (達明機器人)
    'TMScript', 'TMflow', 'TM', '達明', '手臂', '機器人', 'robot',
    '指令', '函數', '函式', '語法', 'API', 'EIH', 'script',
    '暫停', 'Pause', 'Resume', 'Stop', 'Wait', '節點', 'node',
    '座標', '運動', '移動', 'PTP', 'Line', 'Circle',
    '變數', '參數', '設定', '程式', '程序', '執行',
]

# Keywords indicating need for external/latest info
EXTERNAL_KEYWORDS = [
    '最新', '今天', '昨天', '新聞', '消息', '現在', '目前', '最近',
    '即時', '什麼是', '介紹', '歷史', '全球', '世界', '國際',
]


class AgentRouter:
    """Simple agent router for query classification."""

    def __init__(self, mcp_inst: UltraRAG_MCP_Server):
        mcp_inst.tool(
            self.router_init,
            output="internal_keywords,external_indicators,confidence_threshold->None",
        )
        mcp_inst.tool(
            self.classify_query,
            output="q_ls,ret_psg->route_decision,route",
        )

        self.internal_keywords = INTERNAL_KEYWORDS
        self.external_keywords = EXTERNAL_KEYWORDS
        self.confidence_threshold = 0.15  # Lower threshold to prefer internal docs

    def router_init(
        self,
        internal_keywords: Optional[List[str]] = None,
        external_indicators: Optional[List[str]] = None,
        confidence_threshold: float = 0.15,
    ) -> None:
        """Initialize router with custom keywords."""
        if internal_keywords:
            self.internal_keywords = internal_keywords
        if external_indicators:
            self.external_keywords = external_indicators
        self.confidence_threshold = confidence_threshold
        app.logger.info("AgentRouter initialized")

    def _is_greeting(self, query: str) -> bool:
        """Check if query is a simple greeting."""
        query_lower = query.lower().strip()
        for pattern in GREETING_PATTERNS:
            if re.match(pattern, query_lower, re.IGNORECASE):
                return True
        return False

    def _has_internal_keywords(self, query: str) -> bool:
        """Check if query contains internal document keywords."""
        query_lower = query.lower()
        for kw in self.internal_keywords:
            if kw.lower() in query_lower:
                return True
        return False

    def _has_external_keywords(self, query: str) -> bool:
        """Check if query contains external/news keywords."""
        query_lower = query.lower()
        for kw in self.external_keywords:
            if kw.lower() in query_lower:
                return True
        return False

    def _has_retrieved_documents(self, ret_psg: Any) -> bool:
        """Check if there are any retrieved documents."""
        if not ret_psg:
            return False

        # Handle nested list structure: [[passage1, passage2, ...]]
        passages = ret_psg
        if isinstance(passages, list) and passages:
            if isinstance(passages[0], list):
                passages = passages[0]

        if not passages:
            return False

        # Check if any passage has actual content
        for psg in passages[:5]:
            if isinstance(psg, dict):
                content = str(psg.get("contents", "") or psg.get("content", ""))
            else:
                content = str(psg) if psg else ""

            if content and len(content.strip()) > 50:  # Has meaningful content
                return True

        return False

    def _tokenize(self, text: str) -> set:
        """Simple tokenization that works for both Chinese and English."""
        text = text.lower()
        # Split by whitespace for English
        words = set(text.split())
        # Also add individual Chinese characters and n-grams
        chars = set()
        for i, char in enumerate(text):
            if '\u4e00' <= char <= '\u9fff':  # Chinese character
                chars.add(char)
                # Add 2-grams and 3-grams for Chinese
                if i + 1 < len(text):
                    chars.add(text[i:i+2])
                if i + 2 < len(text):
                    chars.add(text[i:i+3])
        return words | chars

    def _check_retrieval_quality(self, query: str, ret_psg: Any) -> float:
        """Check if retrieved passages are relevant."""
        if not ret_psg:
            return 0.0

        # Handle nested list structure: [[passage1, passage2, ...]]
        passages = ret_psg
        if isinstance(passages, list) and passages:
            if isinstance(passages[0], list):
                passages = passages[0]

        if not passages:
            return 0.0

        # Use improved tokenization for Chinese support
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return 0.0

        total_overlap = 0
        valid_passages = 0
        for psg in passages[:3]:
            # Handle both string and dict formats
            if isinstance(psg, dict):
                content = str(psg.get("contents", "") or psg.get("content", ""))
            else:
                content = str(psg) if psg else ""

            if content:
                content_tokens = self._tokenize(content)
                overlap = len(query_tokens & content_tokens)
                total_overlap += overlap
                valid_passages += 1

        if valid_passages == 0:
            return 0.0

        # Calculate score based on how many query tokens are found
        return min(total_overlap / (len(query_tokens) * valid_passages) * 2, 1.0)

    async def classify_query(
        self,
        q_ls: List[str],
        ret_psg: Any = None,
    ) -> Dict[str, Any]:
        """Classify query and determine routing decision.

        Returns route in router format: [{"data": query, "state": "branch_name"}, ...]
        This format is required for UltraRAG branch routing.
        """
        results = []

        for i, query in enumerate(q_ls):
            # Get corresponding passages for this query
            query_psg = None
            if ret_psg:
                if isinstance(ret_psg, list) and i < len(ret_psg):
                    query_psg = ret_psg[i]
                elif i == 0:
                    query_psg = ret_psg

            app.logger.info(f"Classifying query: '{query}'")

            # Check if it's a simple greeting
            if self._is_greeting(query):
                app.logger.info("Route: greeting (direct answer)")
                results.append({
                    "data": query,
                    "state": "greeting",
                })
                continue

            # Check retrieval quality
            retrieval_score = self._check_retrieval_quality(query, query_psg)
            has_internal_kw = self._has_internal_keywords(query)
            has_external_kw = self._has_external_keywords(query)

            # Check if we have any retrieved documents
            has_documents = self._has_retrieved_documents(query_psg)

            app.logger.info(
                f"Scores - retrieval: {retrieval_score:.2f}, has_docs: {has_documents}, "
                f"internal_kw: {has_internal_kw}, external_kw: {has_external_kw}"
            )

            # Decision logic - STRONGLY prioritize using retrieved documents
            # If we found ANY documents, use internal (knowledge base) route
            if has_documents:
                route = "internal"
                if retrieval_score > self.confidence_threshold:
                    reason = "找到高度相關的內部文件"
                elif has_internal_kw:
                    reason = "查詢包含企業內部關鍵字，且有相關文件"
                else:
                    reason = "知識庫中有相關文件，優先使用"
            elif has_internal_kw:
                route = "internal"
                reason = "查詢包含企業內部關鍵字"
            elif has_external_kw:
                route = "external"
                reason = "查詢涉及外部資訊，使用網路搜尋"
            else:
                route = "internal"
                reason = "嘗試使用內部文件"

            app.logger.info(f"Route: {route} - {reason}")

            results.append({
                "data": query,
                "state": route,
            })

        return {
            "route": results,
        }


if __name__ == "__main__":
    AgentRouter(app)
    app.run(transport="stdio")
