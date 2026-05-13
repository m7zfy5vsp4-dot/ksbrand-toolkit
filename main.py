#!/usr/bin/env python3
"""金山云品牌内容模板库-官方量产工具 CLI入口"""

import sys
import json
import time
from pathlib import Path

import click

# 确保项目根目录在sys.path中
project_root = str(Path(__file__).resolve().parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import config
from src.rag.loader import DocumentLoader
from src.rag.embedder import Embedder
from src.rag.retriever import Retriever
from src.compliance.validator import ComplianceValidator
from src.compliance.rules import ComplianceRules
from src.generator.llm_client import LLMClient
from src.generator.prompt_builder import PromptBuilder
from src.generator.batch import BatchGenerator
from src.templates.manager import TemplateManager
from src.templates.renderer import TemplateRenderer
from src.exporter.markdown import MarkdownExporter
from src.exporter.html import HTMLExporter
from src.exporter.docx import DocxExporter


@click.group()
@click.version_option(version="1.0.0", prog_name="ksbrand")
def cli():
    """金山云品牌内容模板库-官方量产工具"""
    pass


# === RAG命令组 ===
@cli.group()
def rag():
    """RAG知识库管理"""
    pass


@rag.command("build")
def rag_build():
    """构建/更新知识库向量索引"""
    click.echo("正在构建知识库索引...")
    embedder = Embedder(
        knowledge_base_dir=config.RAG_CONFIG["knowledge_base_dir"],
        chroma_persist_dir=config.RAG_CONFIG["chroma_persist_dir"],
        embedding_model=config.RAG_CONFIG["embedding_model"],
        chunk_size=config.RAG_CONFIG["chunk_size"],
        chunk_overlap=config.RAG_CONFIG["chunk_overlap"],
    )
    count = embedder.build_index()
    if count > 0:
        click.echo(f"知识库索引构建完成，共索引 {count} 个文本块")
    else:
        click.echo("知识库为空，请检查 knowledge_base/ 目录下是否有文档")


@rag.command("search")
@click.argument("query")
@click.option("--top-k", default=5, help="返回结果数量")
@click.option("--category", default=None, help="限定知识库类别")
def rag_search(query, top_k, category):
    """检索知识库"""
    retriever = Retriever(
        knowledge_base_dir=config.RAG_CONFIG["knowledge_base_dir"],
        chroma_persist_dir=config.RAG_CONFIG["chroma_persist_dir"],
        embedding_model=config.RAG_CONFIG["embedding_model"],
        top_k=top_k,
    )
    results = retriever.search(query, category=category)
    if not results:
        click.echo("未检索到相关内容，请先执行 ksbrand rag build")
        return

    click.echo(f"\n检索结果（查询: {query}）:\n")
    for i, r in enumerate(results, 1):
        click.echo(f"--- 结果 {i} (相关度: {r.score:.2f}) ---")
        click.echo(f"来源: {r.source} | 类别: {r.category}")
        click.echo(f"{r.content}\n")


# === 模板命令组 ===
@cli.group()
def template():
    """模板管理"""
    pass


@template.command("list")
@click.option("--category", default=None, help="按分类筛选")
def template_list(category):
    """列出所有可用模板"""
    manager = TemplateManager()
    templates = manager.list_templates(category=category)
    if not templates:
        click.echo("暂无模板，请检查 templates/ 目录")
        return

    click.echo("\n可用模板:\n")
    current_cat = ""
    for t in templates:
        if t["category"] != current_cat:
            current_cat = t["category"]
            click.echo(f"  [{current_cat}]")
        click.echo(f"    - {t['name']}")


@template.command("show")
@click.argument("name")
def template_show(name):
    """查看模板详情"""
    manager = TemplateManager()
    info = manager.get_template_info(name)
    if info is None:
        click.echo(f"模板 '{name}' 不存在")
        return

    click.echo(f"\n模板: {info['name']}")
    if info["description"]:
        click.echo(f"描述: {info['description']}")
    click.echo(f"变量: {', '.join(info['variables']) if info['variables'] else '无'}")
    click.echo(f"\n--- 模板内容 ---\n{info['content']}")


# === 生成命令组 ===
@cli.group()
def generate():
    """内容生成"""
    pass


@generate.command("single")
@click.argument("template_name")
@click.option("--params", multiple=True, help="模板参数 key=value")
@click.option("--format", "fmt", default="markdown", type=click.Choice(["markdown", "html", "docx"]))
@click.option("--output-dir", default="output", help="输出目录")
def generate_single(template_name, params, fmt, output_dir):
    """单条内容生成"""
    # 解析参数
    params_dict = {}
    for p in params:
        if "=" in p:
            k, v = p.split("=", 1)
            params_dict[k.strip()] = v.strip()

    click.echo(f"正在生成: 模板={template_name}, 参数={params_dict}")

    generator = BatchGenerator()
    result = generator.generate_single(template_name, params_dict)

    # 输出合规状态
    if result.compliance.passed:
        click.echo("合规校验: 通过")
    else:
        click.echo("合规校验: 未通过")
        for err in result.compliance.errors:
            click.echo(f"  错误: {err}")
    for warn in result.compliance.warnings:
        click.echo(f"  警告: {warn}")

    # 导出
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    metadata = {
        "template_name": template_name,
        "generated_at": result.generated_at,
        "model": result.model,
        "compliance_passed": result.compliance.passed,
    }

    exporter = _get_exporter(fmt)
    ext = _get_extension(fmt)
    filepath = Path(output_dir) / f"{template_name.replace('/', '_')}_{timestamp}{ext}"
    exporter.export(
        content=result.content,
        output_path=str(filepath),
        metadata=metadata,
        rag_sources=result.rag_sources,
    )
    click.echo(f"\n输出已保存: {filepath}")


@cli.command("batch")
@click.argument("template_name")
@click.option("--csv", "csv_path", required=True, help="参数CSV文件路径")
@click.option("--format", "fmt", default="markdown", type=click.Choice(["markdown", "html", "docx"]))
@click.option("--output-dir", default="output", help="输出目录")
def batch_generate(template_name, csv_path, fmt, output_dir):
    """批量量产（从CSV读取参数）"""
    click.echo(f"批量生成: 模板={template_name}, CSV={csv_path}")

    generator = BatchGenerator()
    results = generator.generate_batch(template_name, csv_path)

    passed = sum(1 for r in results if r.compliance.passed)
    click.echo(f"\n生成完成: {len(results)} 条, 合规 {passed} 条, 不合规 {len(results) - passed} 条")

    # 保存结果
    generator.save_results(results, output_dir, format="json")
    click.echo(f"结果已保存至 {output_dir}/")


# === 合规检查命令 ===
@cli.command("check")
@click.argument("file_path")
def check_compliance(file_path):
    """检查已有内容的合规性"""
    filepath = Path(file_path)
    if not filepath.exists():
        click.echo(f"文件不存在: {file_path}")
        return

    content = filepath.read_text(encoding="utf-8")
    validator = ComplianceValidator()
    result = validator.validate(content)

    click.echo(f"\n合规检查结果: {'通过' if result.passed else '未通过'}\n")
    if result.forbidden_word_hits:
        click.echo(f"禁用词: {', '.join(result.forbidden_word_hits)}")
    if result.product_name_issues:
        click.echo(f"产品名问题: {', '.join(result.product_name_issues)}")
    if result.errors:
        click.echo("错误:")
        for err in result.errors:
            click.echo(f"  - {err}")
    if result.warnings:
        click.echo("警告:")
        for warn in result.warnings:
            click.echo(f"  - {warn}")


# === 导出命令 ===
@cli.command("export")
@click.argument("output_dir")
@click.option("--format", "fmt", default="markdown", type=click.Choice(["markdown", "html", "docx"]))
@click.option("--input", "input_file", default=None, help="指定输入JSON结果文件")
def export_output(output_dir, fmt, input_file):
    """导出生成结果"""
    if input_file is None:
        # 查找最新的结果文件
        output_path = Path("output")
        json_files = sorted(output_path.glob("batch_*.json"), reverse=True)
        if not json_files:
            click.echo("未找到生成结果，请先执行 generate 或 batch 命令")
            return
        input_file = str(json_files[0])

    click.echo(f"从 {input_file} 导出为 {fmt} 格式...")

    with open(input_file, "r", encoding="utf-8") as f:
        results = json.load(f)

    exporter = _get_exporter(fmt)
    ext = _get_extension(fmt)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    for i, result in enumerate(results, 1):
        filename = f"{result.get('template_name', 'output')}_{i}{ext}"
        filepath = out_path / filename
        exporter.export(
            content=result.get("content", ""),
            output_path=str(filepath),
            metadata={
                "template_name": result.get("template_name", ""),
                "generated_at": result.get("generated_at", ""),
                "model": result.get("model", ""),
            },
            rag_sources=result.get("rag_sources"),
        )
        click.echo(f"  已导出: {filepath}")


# === 辅助函数 ===
def _get_exporter(fmt: str):
    if fmt == "markdown":
        return MarkdownExporter()
    elif fmt == "html":
        return HTMLExporter()
    elif fmt == "docx":
        return DocxExporter()
    raise ValueError(f"不支持的格式: {fmt}")


def _get_extension(fmt: str) -> str:
    extensions = {"markdown": ".md", "html": ".html", "docx": ".docx"}
    return extensions.get(fmt, ".md")


if __name__ == "__main__":
    cli()
