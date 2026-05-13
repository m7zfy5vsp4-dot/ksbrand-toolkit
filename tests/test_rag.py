"""RAG检索模块测试"""

import sys
from pathlib import Path

project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
import tempfile
import shutil
from src.rag.loader import DocumentLoader, Chunk


class TestDocumentLoader:
    """文档加载器测试"""

    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.loader = DocumentLoader(
            knowledge_base_dir=self.tmp_dir,
            chunk_size=200,
            chunk_overlap=50,
        )

    def teardown_method(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _create_file(self, rel_path: str, content: str):
        filepath = Path(self.tmp_dir) / rel_path
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content, encoding="utf-8")

    def test_load_empty_dir(self):
        chunks = self.loader.load_all()
        assert chunks == []

    def test_load_nonexistent_dir(self):
        loader = DocumentLoader(knowledge_base_dir="/nonexistent/path")
        chunks = loader.load_all()
        assert chunks == []

    def test_load_text_file(self):
        self._create_file("test/hello.txt", "这是测试内容")
        chunks = self.loader.load_all()
        assert len(chunks) > 0
        assert "测试内容" in chunks[0].content

    def test_load_markdown_file(self):
        self._create_file("brand/test.md", "# 标题\n\n金山云品牌规范")
        chunks = self.loader.load_all()
        assert len(chunks) > 0
        assert any("金山云" in c.content for c in chunks)

    def test_chunk_metadata(self):
        self._create_file("product_capabilities/cdn.txt", "金山云CDN产品能力介绍")
        chunks = self.loader.load_all()
        assert chunks[0].metadata.get("category") == "product_capabilities"
        assert chunks[0].source != ""

    def test_chunk_split_long_document(self):
        long_text = "这是一段很长的文本。" * 100  # ~1200字符
        self._create_file("data/long.txt", long_text)
        chunks = self.loader.load_all()
        assert len(chunks) > 1

    def test_chunk_has_source_info(self):
        self._create_file("test/source.txt", "来源测试")
        chunks = self.loader.load_all()
        assert chunks[0].source is not None
        assert "source.txt" in chunks[0].source

    def test_skip_unsupported_file(self):
        self._create_file("test/image.png", "not real png")
        # .png不在SUPPORTED_EXTENSIONS中，应被跳过
        chunks = self.loader.load_all()
        assert len(chunks) == 0


class TestChunk:
    """Chunk数据类测试"""

    def test_chunk_creation(self):
        chunk = Chunk(
            content="测试内容",
            source="test.md",
            chunk_index=0,
            metadata={"category": "test"},
        )
        assert chunk.content == "测试内容"
        assert chunk.source == "test.md"
        assert chunk.chunk_index == 0
        assert chunk.metadata["category"] == "test"
