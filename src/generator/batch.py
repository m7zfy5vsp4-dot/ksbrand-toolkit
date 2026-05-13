"""批量量产引擎模块"""

import csv
import json
import time
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field, asdict

from .llm_client import LLMClient
from .prompt_builder import PromptBuilder
from src.compliance.validator import ComplianceValidator, ValidationResult
from src.rag.retriever import Retriever
from src.templates.manager import TemplateManager
from src.templates.renderer import TemplateRenderer


@dataclass
class GenerationResult:
    """单条生成结果"""
    template_name: str
    params: dict
    content: str
    compliance: ValidationResult
    rag_sources: list[dict] = field(default_factory=list)
    model: str = ""
    generated_at: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["compliance"] = {
            "passed": self.compliance.passed,
            "errors": self.compliance.errors,
            "warnings": self.compliance.warnings,
        }
        return d


class BatchGenerator:
    """批量量产引擎"""

    def __init__(self, llm_client: Optional[LLMClient] = None,
                 prompt_builder: Optional[PromptBuilder] = None,
                 validator: Optional[ComplianceValidator] = None,
                 template_manager: Optional[TemplateManager] = None):
        self.llm_client = llm_client or LLMClient()
        self.validator = validator or ComplianceValidator()
        self.template_manager = template_manager or TemplateManager()
        self.prompt_builder = prompt_builder or PromptBuilder(
            retriever=Retriever(),
            validator=self.validator,
        )
        self.renderer = TemplateRenderer()

    def generate_single(self, template_name: str,
                        params: dict) -> GenerationResult:
        """单条内容生成"""
        # 1. 加载模板
        template_content = self.template_manager.load_template(template_name)
        if template_content is None:
            return GenerationResult(
                template_name=template_name,
                params=params,
                content=f"[错误] 模板 '{template_name}' 不存在",
                compliance=ValidationResult(passed=False, errors=["模板不存在"]),
            )

        # 2. 构建Prompt
        build_result = self.prompt_builder.build(template_content, params)

        # 3. 调用LLM
        llm_result = self.llm_client.generate_with_sources(
            prompt=build_result["prompt"],
            system_prompt=build_result["system_prompt"],
        )

        content = llm_result["content"]

        # 4. 合规校验
        compliance = self.validator.validate(content)

        # 5. 返回结果
        return GenerationResult(
            template_name=template_name,
            params=params,
            content=content,
            compliance=compliance,
            rag_sources=build_result["rag_sources"],
            model=llm_result.get("model", ""),
            generated_at=time.strftime("%Y-%m-%d %H:%M:%S"),
        )

    def generate_batch(self, template_name: str,
                       csv_path: str) -> list[GenerationResult]:
        """从CSV文件批量量产"""
        results = []
        csv_file = Path(csv_path)
        if not csv_file.exists():
            print(f"[Batch] CSV文件不存在: {csv_path}")
            return results

        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, 1):
                print(f"[Batch] 正在生成第 {i} 条...")
                result = self.generate_single(template_name, dict(row))
                results.append(result)
                status = "✓ 合规" if result.compliance.passed else "✗ 不合规"
                print(f"  {status} | 模板: {template_name}")

        return results

    def save_results(self, results: list[GenerationResult],
                     output_dir: str = "output",
                     format: str = "json"):
        """保存生成结果"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        if format == "json":
            filepath = output_path / f"batch_{time.strftime('%Y%m%d_%H%M%S')}.json"
            data = [r.to_dict() for r in results]
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"[Batch] 结果已保存: {filepath}")

        return filepath if format == "json" else None
