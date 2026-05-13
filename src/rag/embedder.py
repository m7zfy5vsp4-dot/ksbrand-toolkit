"""向量化与存储模块（ChromaDB）"""

import os
from pathlib import Path
from .loader import DocumentLoader, Chunk


class Embedder:
    """将文本块向量化并存入ChromaDB

    RAG索引统一使用ChromaDB默认embedding(all-MiniLM-L6-v2)，
    不依赖OPENAI_API_KEY。API key仅用于LLM内容生成。
    """

    def __init__(self, knowledge_base_dir: str = "knowledge_base",
                 chroma_persist_dir: str = ".chroma_db",
                 chunk_size: int = 500,
                 chunk_overlap: int = 100):
        self.knowledge_base_dir = knowledge_base_dir
        self.chroma_persist_dir = chroma_persist_dir
        self.loader = DocumentLoader(
            knowledge_base_dir=knowledge_base_dir,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        self._client = None
        self._collection = None

    def _get_chroma_client(self):
        """懒加载ChromaDB客户端"""
        if self._client is None:
            try:
                import chromadb
                self._client = chromadb.PersistentClient(path=self.chroma_persist_dir)
            except ImportError:
                print("[Embedder] chromadb未安装，请执行: pip install chromadb")
                return None
        return self._client

    def build_index(self) -> int:
        """构建/重建向量索引，返回索引文档数"""
        chunks = self.loader.load_all()
        if not chunks:
            print("[Embedder] 未找到任何文档，索引为空")
            return 0

        client = self._get_chroma_client()
        if client is None:
            return 0

        # 删除旧collection再重建
        try:
            client.delete_collection("ksbrand_knowledge")
        except Exception:
            pass

        # 始终使用默认embedding（all-MiniLM-L6-v2），确保读写一致
        collection = client.get_or_create_collection(name="ksbrand_knowledge")

        # 批量插入
        ids = [f"chunk_{i}" for i in range(len(chunks))]
        documents = [c.content for c in chunks]
        metadatas = [
            {"source": c.source, "category": c.metadata.get("category", "general"),
             "chunk_index": c.chunk_index}
            for c in chunks
        ]

        # ChromaDB单次插入有上限，分批处理
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            batch_docs = documents[i:i + batch_size]
            batch_metas = metadatas[i:i + batch_size]
            collection.add(
                ids=batch_ids,
                documents=batch_docs,
                metadatas=batch_metas,
            )

        self._collection = collection
        print(f"[Embedder] 索引构建完成，共 {len(chunks)} 个文本块")
        return len(chunks)

    def get_collection(self):
        """获取当前collection"""
        if self._collection is None:
            client = self._get_chroma_client()
            if client is None:
                return None
            try:
                self._collection = client.get_collection(name="ksbrand_knowledge")
            except ValueError:
                print("[Embedder] 知识库索引不存在，请先执行 rag build")
                return None
        return self._collection
