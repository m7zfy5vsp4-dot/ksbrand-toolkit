"""内容生成模块测试"""

import sys
from pathlib import Path

project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from unittest.mock import patch, MagicMock
from src.generator.prompt_builder import PromptBuilder
from src.generator.llm_client import LLMClient
from src.generator.batch import BatchGenerator, GenerationResult
from src.compliance.validator import ComplianceValidator, ValidationResult
from src.rag.retriever import Retriever, RetrievalResult


class TestPromptBuilder:
    """Prompt构建器测试"""

    def test_build_returns_required_keys(self):
        # Mock retriever to return empty results
        mock_retriever = MagicMock(spec=Retriever)
        mock_retriever.search.return_value = []
        mock_retriever.format_context.return_value = "【注意】RAG知识库未检索到相关内容"
        mock_retriever.get_sources.return_value = []

        builder = PromptBuilder(retriever=mock_retriever)
        result = builder.build("模板内容 {{ product }}", {"product": "CDN"})

        assert "prompt" in result
        assert "system_prompt" in result
        assert "rag_context" in result
        assert "rag_sources" in result

    def test_build_contains_rag_context(self):
        mock_retriever = MagicMock(spec=Retriever)
        mock_retriever.search.return_value = []
        mock_retriever.format_context.return_value = "RAG上下文内容"
        mock_retriever.get_sources.return_value = []

        builder = PromptBuilder(retriever=mock_retriever)
        result = builder.build("模板", {})

        assert "RAG上下文内容" in result["prompt"]

    def test_build_system_prompt_contains_brand_name(self):
        mock_retriever = MagicMock(spec=Retriever)
        mock_retriever.search.return_value = []
        mock_retriever.format_context.return_value = ""
        mock_retriever.get_sources.return_value = []

        builder = PromptBuilder(retriever=mock_retriever)
        result = builder.build("模板", {})

        assert "金山云" in result["system_prompt"]
        assert "合规约束" in result["system_prompt"]

    def test_build_with_jinja2_params(self):
        mock_retriever = MagicMock(spec=Retriever)
        mock_retriever.search.return_value = []
        mock_retriever.format_context.return_value = ""
        mock_retriever.get_sources.return_value = []

        builder = PromptBuilder(retriever=mock_retriever)
        result = builder.build("产品: {{ product }}", {"product": "CDN"})

        assert "CDN" in result["prompt"]


class TestLLMClient:
    """LLM客户端测试"""

    def test_init_default_config(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            client = LLMClient()
            assert client.model is not None
            assert client.temperature is not None

    def test_generate_with_mock(self):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "测试输出"

        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            client = LLMClient(api_key="test-key")
            result = client.generate("测试prompt")
            assert result == "测试输出"


class TestBatchGenerator:
    """批量生成器测试"""

    def test_generate_single_missing_template(self):
        mock_tm = MagicMock()
        mock_tm.load_template.return_value = None

        generator = BatchGenerator(template_manager=mock_tm)
        result = generator.generate_single("nonexistent", {})

        assert result.compliance.passed is False
        assert "模板" in result.content and "不存在" in result.content

    def test_generation_result_to_dict(self):
        result = GenerationResult(
            template_name="test",
            params={"k": "v"},
            content="测试内容",
            compliance=ValidationResult(passed=True),
            rag_sources=[{"source": "test.md", "score": 0.9}],
        )
        d = result.to_dict()
        assert d["template_name"] == "test"
        assert d["compliance"]["passed"] is True
