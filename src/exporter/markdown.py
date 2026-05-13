"""Markdown导出模块"""

import time
from pathlib import Path
from typing import Optional


class MarkdownExporter:
    """导出内容为Markdown格式"""

    def export(self, content: str, output_path: str,
               metadata: Optional[dict] = None,
               rag_sources: Optional[list[dict]] = None) -> str:
        """导出为Markdown文件"""
        filepath = Path(output_path)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        parts = []

        # 添加元数据头
        if metadata:
            parts.append(self._format_metadata(metadata))
            parts.append("---\n")

        # 主体内容
        parts.append(content)

        # 添加RAG来源标注
        if rag_sources:
            parts.append("\n\n---\n")
            parts.append(self._format_sources(rag_sources))

        filepath.write_text("\n".join(parts), encoding="utf-8")
        return str(filepath)

    def _format_metadata(self, metadata: dict) -> str:
        lines = ["---"]
        for key, value in metadata.items():
            lines.append(f"{key}: {value}")
        lines.append("---")
        return "\n".join(lines)

    def _format_sources(self, sources: list[dict]) -> str:
        lines = ["### RAG来源标注\n"]
        for i, source in enumerate(sources, 1):
            lines.append(
                f"{i}. 文件: `{source.get('source', 'unknown')}` | "
                f"类别: {source.get('category', 'N/A')} | "
                f"相关度: {source.get('score', 0):.2f}"
            )
        return "\n".join(lines)
