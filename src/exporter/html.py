"""HTML导出模块"""

from pathlib import Path
from typing import Optional
import html


class HTMLExporter:
    """导出内容为HTML格式"""

    TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - 金山云品牌内容</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 40px 20px;
            color: #333;
            line-height: 1.8;
        }}
        h1, h2, h3 {{ color: #1a1a1a; }}
        .metadata {{
            background: #f5f5f5;
            padding: 12px 16px;
            border-radius: 4px;
            font-size: 13px;
            color: #666;
            margin-bottom: 24px;
        }}
        .content {{
            margin-bottom: 32px;
        }}
        .sources {{
            border-top: 1px solid #eee;
            padding-top: 16px;
            font-size: 13px;
            color: #888;
        }}
        .sources h3 {{ font-size: 14px; color: #666; }}
        .disclaimer {{
            background: #fff8e1;
            padding: 12px 16px;
            border-radius: 4px;
            font-size: 12px;
            color: #8d6e00;
            margin-top: 24px;
        }}
    </style>
</head>
<body>
    {metadata_html}
    <div class="content">
        {content_html}
    </div>
    {sources_html}
    {disclaimer_html}
</body>
</html>"""

    def export(self, content: str, output_path: str,
               metadata: Optional[dict] = None,
               rag_sources: Optional[list[dict]] = None) -> str:
        """导出为HTML文件"""
        filepath = Path(output_path)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        title = metadata.get("template_name", "品牌内容") if metadata else "品牌内容"
        content_html = self._markdown_to_html_paragraphs(content)
        metadata_html = self._format_metadata(metadata)
        sources_html = self._format_sources(rag_sources)
        disclaimer_html = (
            '<div class="disclaimer">本内容由金山云AI量产助手生成，'
            '仅作内部参考使用，正式发布前请经品牌合规审核。</div>'
        )

        page = self.TEMPLATE.format(
            title=html.escape(title),
            metadata_html=metadata_html,
            content_html=content_html,
            sources_html=sources_html,
            disclaimer_html=disclaimer_html,
        )

        filepath.write_text(page, encoding="utf-8")
        return str(filepath)

    def _markdown_to_html_paragraphs(self, text: str) -> str:
        """简单将Markdown段落转为HTML段落"""
        import re
        lines = text.split("\n")
        html_parts = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("# "):
                html_parts.append(f"<h1>{html.escape(stripped[2:])}</h1>")
            elif stripped.startswith("## "):
                html_parts.append(f"<h2>{html.escape(stripped[3:])}</h2>")
            elif stripped.startswith("### "):
                html_parts.append(f"<h3>{html.escape(stripped[4:])}</h3>")
            elif stripped.startswith("- ") or stripped.startswith("* "):
                html_parts.append(f"<li>{html.escape(stripped[2:])}</li>")
            else:
                html_parts.append(f"<p>{html.escape(stripped)}</p>")
        return "\n".join(html_parts)

    def _format_metadata(self, metadata: Optional[dict]) -> str:
        if not metadata:
            return ""
        items = [f"<strong>{k}</strong>: {html.escape(str(v))}" for k, v in metadata.items()]
        return '<div class="metadata">' + " | ".join(items) + "</div>"

    def _format_sources(self, sources: Optional[list[dict]]) -> str:
        if not sources:
            return ""
        items = []
        for i, s in enumerate(sources, 1):
            items.append(
                f"{i}. {html.escape(s.get('source', 'unknown'))} "
                f"(类别: {html.escape(s.get('category', 'N/A'))}, "
                f"相关度: {s.get('score', 0):.2f})"
            )
        return (
            '<div class="sources"><h3>RAG来源标注</h3>'
            + "<br>".join(items) + "</div>"
        )
