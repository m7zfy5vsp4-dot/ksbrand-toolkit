"""文档加载与切分模块"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Chunk:
    """文本切分单元"""
    content: str
    source: str
    chunk_index: int
    metadata: dict = field(default_factory=dict)


class DocumentLoader:
    """从knowledge_base目录加载文档并切分"""

    SUPPORTED_EXTENSIONS = {".md", ".txt", ".pdf", ".docx"}

    def __init__(self, knowledge_base_dir: str = "knowledge_base",
                 chunk_size: int = 500, chunk_overlap: int = 100):
        self.knowledge_base_dir = Path(knowledge_base_dir)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def load_all(self) -> list[Chunk]:
        """加载知识库目录下所有支持的文档"""
        all_chunks = []
        if not self.knowledge_base_dir.exists():
            return all_chunks

        for root, _dirs, files in os.walk(self.knowledge_base_dir):
            for filename in files:
                filepath = Path(root) / filename
                if filepath.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                    text = self._load_file(filepath)
                    if text:
                        relative_path = filepath.relative_to(self.knowledge_base_dir)
                        category = relative_path.parts[0] if len(relative_path.parts) > 1 else "general"
                        chunks = self._split_text(
                            text,
                            source=str(filepath),
                            metadata={"category": category, "filename": filename}
                        )
                        all_chunks.extend(chunks)
        return all_chunks

    def _load_file(self, filepath: Path) -> Optional[str]:
        """根据文件类型加载内容"""
        ext = filepath.suffix.lower()
        if ext == ".md" or ext == ".txt":
            return self._load_text(filepath)
        elif ext == ".pdf":
            return self._load_pdf(filepath)
        elif ext == ".docx":
            return self._load_docx(filepath)
        return None

    def _load_text(self, filepath: Path) -> Optional[str]:
        """加载纯文本/Markdown文件"""
        try:
            return filepath.read_text(encoding="utf-8")
        except Exception as e:
            print(f"[Loader] 读取文件失败 {filepath}: {e}")
            return None

    def _load_pdf(self, filepath: Path) -> Optional[str]:
        """加载PDF文件"""
        try:
            import pymupdf  # type: ignore
            doc = pymupdf.open(str(filepath))
            text_parts = []
            for page in doc:
                text_parts.append(page.get_text())
            doc.close()
            return "\n".join(text_parts)
        except ImportError:
            print("[Loader] pymupdf未安装，无法加载PDF文件。请执行: pip install pymupdf")
            return None
        except Exception as e:
            print(f"[Loader] 读取PDF失败 {filepath}: {e}")
            return None

    def _load_docx(self, filepath: Path) -> Optional[str]:
        """加载DOCX文件"""
        try:
            import docx  # type: ignore
            doc = docx.Document(str(filepath))
            return "\n".join([para.text for para in doc.paragraphs])
        except ImportError:
            print("[Loader] python-docx未安装，无法加载DOCX文件。请执行: pip install python-docx")
            return None
        except Exception as e:
            print(f"[Loader] 读取DOCX失败 {filepath}: {e}")
            return None

    def _split_text(self, text: str, source: str,
                    metadata: dict | None = None) -> list[Chunk]:
        """将文本切分为固定大小的块"""
        if metadata is None:
            metadata = {}

        # 按段落优先切分，再按chunk_size切分
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        # 如果没有段落分隔，按单行或整体处理
        if len(paragraphs) <= 1 and len(text) > self.chunk_size:
            paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        if len(paragraphs) <= 1 and len(text) > self.chunk_size:
            # 强制按chunk_size切分
            return self._split_fixed(text, source, metadata)

        chunks = []
        current_text = ""
        chunk_index = 0

        for para in paragraphs:
            if len(current_text) + len(para) > self.chunk_size and current_text:
                chunks.append(Chunk(
                    content=current_text.strip(),
                    source=source,
                    chunk_index=chunk_index,
                    metadata={**metadata},
                ))
                chunk_index += 1
                # 保留overlap
                if self.chunk_overlap > 0 and len(current_text) > self.chunk_overlap:
                    current_text = current_text[-self.chunk_overlap:] + "\n\n" + para
                else:
                    current_text = para
            else:
                current_text = current_text + "\n\n" + para if current_text else para

        # 最后一块
        if current_text.strip():
            chunks.append(Chunk(
                content=current_text.strip(),
                source=source,
                chunk_index=chunk_index,
                metadata={**metadata},
            ))

        return chunks

    def _split_fixed(self, text: str, source: str,
                     metadata: dict) -> list[Chunk]:
        """当无段落分隔时，按固定大小切分"""
        chunks = []
        chunk_index = 0
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunk_text = text[start:end]
            chunks.append(Chunk(
                content=chunk_text.strip(),
                source=source,
                chunk_index=chunk_index,
                metadata={**metadata},
            ))
            chunk_index += 1
            start = end - self.chunk_overlap if end < len(text) else end
        return chunks
