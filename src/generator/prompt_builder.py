"""Prompt构建模块（注入RAG上下文+合规约束）"""

import sys
from pathlib import Path
from typing import Optional

project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import config
from src.rag.retriever import Retriever, RetrievalResult
from src.compliance.validator import ComplianceValidator
from src.compliance.rules import ComplianceRules


class PromptBuilder:
    """构建完整的LLM Prompt，包含模板占位符、RAG上下文、合规约束、文风指令"""

    def __init__(self, retriever: Optional[Retriever] = None,
                 validator: Optional[ComplianceValidator] = None):
        self.retriever = retriever or Retriever()
        self.validator = validator or ComplianceValidator()
        self.rules = self.validator.rules

    def build(self, template_content: str, params: dict,
              query: Optional[str] = None) -> dict:
        """构建完整Prompt

        Returns:
            dict with keys: prompt, system_prompt, rag_context, rag_sources
        """
        # 1. 用Jinja2渲染模板占位符
        from jinja2 import Template
        template = Template(template_content)
        rendered = template.render(**params)

        # 2. 检索RAG知识库
        search_query = query or rendered[:200]
        rag_results = self.retriever.search(search_query)
        rag_context = self.retriever.format_context(rag_results)
        rag_sources = self.retriever.get_sources(rag_results)

        # 3. 组装Prompt
        system_prompt = self._build_system_prompt()
        prompt = self._build_user_prompt(rendered, rag_context)

        return {
            "prompt": prompt,
            "system_prompt": system_prompt,
            "rag_context": rag_context,
            "rag_sources": rag_sources,
        }

    def _build_system_prompt(self) -> str:
        """构建系统级Prompt"""
        return (
            f"你是{config.BRAND_NAME}品牌官方AI量产助手。\n\n"
            f"{self.rules.get_tone_instruction()}\n\n"
            f"{self.rules.get_compliance_prompt_section()}\n\n"
            "【核心原则】\n"
            "1. 所有事实性内容必须基于RAG知识库检索结果，严禁编造\n"
            "2. 未在RAG上下文中出现的数据、案例、口径不得引用\n"
            "3. 如RAG上下文不足以支撑回答，须明确说明并建议人工核实\n"
            "4. 每条事实性陈述须标注RAG来源\n"
        )

    def _build_user_prompt(self, rendered_template: str,
                           rag_context: str) -> str:
        """构建用户级Prompt"""
        return (
            f"【RAG知识库上下文】\n{rag_context}\n\n"
            f"【内容模板】\n{rendered_template}\n\n"
            "请根据以上RAG知识库上下文和内容模板，生成符合品牌规范的内容。\n"
            "确保：\n"
            "- 事实性内容有RAG来源标注\n"
            "- 不使用任何禁用词\n"
            "- 遵循品牌文风要求\n"
            "- 产品名使用官方规范写法\n"
        )
