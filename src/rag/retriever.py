"""检索与排序模块"""

from dataclasses import dataclass
from typing import Optional
from .embedder import Embedder


@dataclass
class RetrievalResult:
    """检索结果"""
    content: str
    source: str
    category: str
    score: float
    chunk_index: int


class Retriever:
    """从ChromaDB中检索相关文档片段"""

    def __init__(self, embedder: Optional[Embedder] = None,
                 knowledge_base_dir: str = "knowledge_base",
                 chroma_persist_dir: str = ".chroma_db",
                 embedding_model: str = "text-embedding-3-small",
                 top_k: int = 5):
        if embedder:
            self.embedder = embedder
        else:
            self.embedder = Embedder(
                knowledge_base_dir=knowledge_base_dir,
                chroma_persist_dir=chroma_persist_dir,
                embedding_model=embedding_model,
            )
        self.top_k = top_k

    def search(self, query: str, top_k: Optional[int] = None,
               category: Optional[str] = None) -> list[RetrievalResult]:
        """检索与query最相关的文档片段"""
        collection = self.embedder.get_collection()
        if collection is None:
            return []

        k = top_k or self.top_k

        # 构建查询参数
        query_params: dict = {
            "query_texts": [query],
            "n_results": k,
        }
        if category:
            query_params["where"] = {"category": category}

        try:
            results = collection.query(**query_params)
        except Exception as e:
            print(f"[Retriever] 检索失败: {e}")
            return []

        # 解析结果
        retrieval_results = []
        if not results["ids"] or not results["ids"][0]:
            return retrieval_results

        ids = results["ids"][0]
        documents = results["documents"][0] if results["documents"] else [""] * len(ids)
        distances = results["distances"][0] if results["distances"] else [0.0] * len(ids)
        metadatas = results["metadatas"][0] if results["metadatas"] else [{}] * len(ids)

        for i, doc_id in enumerate(ids):
            meta = metadatas[i] if i < len(metadatas) else {}
            # ChromaDB返回的是距离，越小越相似；转换为相似度分数
            distance = distances[i] if i < len(distances) else 1.0
            score = max(0, 1 - distance)

            retrieval_results.append(RetrievalResult(
                content=documents[i] if i < len(documents) else "",
                source=meta.get("source", "unknown"),
                category=meta.get("category", "general"),
                score=score,
                chunk_index=meta.get("chunk_index", 0),
            ))

        # 按相似度降序排列
        retrieval_results.sort(key=lambda x: x.score, reverse=True)
        return retrieval_results

    def format_context(self, results: list[RetrievalResult]) -> str:
        """将检索结果格式化为可注入Prompt的上下文文本"""
        if not results:
            return "【注意】RAG知识库未检索到相关内容，请仅使用已有品牌规范信息作答。"

        context_parts = []
        for i, r in enumerate(results, 1):
            context_parts.append(
                f"[来源{i}] 文件: {r.source} (类别: {r.category}, 相关度: {r.score:.2f})\n{r.content}"
            )

        return "\n\n".join(context_parts)

    def get_sources(self, results: list[RetrievalResult]) -> list[dict]:
        """提取RAG来源标注信息"""
        seen = set()
        sources = []
        for r in results:
            key = (r.source, r.chunk_index)
            if key not in seen:
                seen.add(key)
                sources.append({
                    "source": r.source,
                    "category": r.category,
                    "chunk_index": r.chunk_index,
                    "score": r.score,
                })
        return sources
