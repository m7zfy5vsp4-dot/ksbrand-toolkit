"""FastAPI Web应用 - 金山云品牌内容量产工具"""

import sys
import os
import json
import time
from pathlib import Path
from typing import Optional

project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import config
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

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

app = FastAPI(title="金山云品牌内容量产工具", version="1.0.0")

# 全局组件
validator = ComplianceValidator()
template_manager = TemplateManager()
renderer = TemplateRenderer()
embedder = Embedder(
    knowledge_base_dir=config.RAG_CONFIG["knowledge_base_dir"],
    chroma_persist_dir=config.RAG_CONFIG["chroma_persist_dir"],
)
retriever = Retriever(embedder=embedder)


@app.get("/", response_class=HTMLResponse)
async def index():
    """主页"""
    templates = template_manager.list_templates()
    rules = ComplianceRules()
    forbidden_sample = "、".join(rules.forbidden_words[:15]) + " 等"

    # 读取知识库文档数量
    kb_docs = 0
    kb_dir = Path(config.RAG_CONFIG["knowledge_base_dir"])
    if kb_dir.exists():
        for root, _dirs, files in os.walk(kb_dir):
            kb_docs += len(files)

    # 检查RAG索引状态
    rag_ready = embedder.get_collection() is not None

    # 检查API配置
    api_configured = bool(os.environ.get("OPENAI_API_KEY", ""))

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>金山云品牌内容量产工具</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f0f2f5; color: #333; }}
        .header {{ background: linear-gradient(135deg, #1a3a5c 0%, #2d6da3 100%); color: white; padding: 20px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.15); }}
        .header h1 {{ font-size: 24px; font-weight: 600; }}
        .header p {{ font-size: 13px; opacity: 0.85; margin-top: 4px; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 0 20px; }}
        .tabs {{ display: flex; gap: 0; background: white; border-radius: 8px 8px 0 0; margin-top: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); overflow: hidden; }}
        .tab {{ padding: 12px 24px; cursor: pointer; border: none; background: none; font-size: 14px; color: #666; border-bottom: 2px solid transparent; transition: all 0.2s; }}
        .tab:hover {{ color: #2d6da3; }}
        .tab.active {{ color: #2d6da3; border-bottom-color: #2d6da3; font-weight: 600; }}
        .panel {{ display: none; background: white; padding: 24px; border-radius: 0 0 8px 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); min-height: 400px; }}
        .panel.active {{ display: block; }}
        .card {{ background: #fafbfc; border: 1px solid #e8e8e8; border-radius: 6px; padding: 16px; margin-bottom: 12px; }}
        .card h3 {{ font-size: 15px; color: #1a3a5c; margin-bottom: 8px; }}
        .status {{ display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 12px; font-weight: 500; }}
        .status.ok {{ background: #e6f7e6; color: #389e0d; }}
        .status.warn {{ background: #fff8e1; color: #d48806; }}
        .status.err {{ background: #fff1f0; color: #cf1322; }}
        .btn {{ display: inline-block; padding: 8px 20px; border-radius: 4px; border: none; font-size: 14px; cursor: pointer; transition: all 0.2s; font-weight: 500; }}
        .btn-primary {{ background: #2d6da3; color: white; }}
        .btn-primary:hover {{ background: #1a3a5c; }}
        .btn-outline {{ background: white; color: #2d6da3; border: 1px solid #2d6da3; }}
        .btn-outline:hover {{ background: #f0f7ff; }}
        input, textarea, select {{ width: 100%; padding: 8px 12px; border: 1px solid #d9d9d9; border-radius: 4px; font-size: 14px; transition: border 0.2s; }}
        input:focus, textarea:focus, select:focus {{ outline: none; border-color: #2d6da3; box-shadow: 0 0 0 2px rgba(45,109,163,0.1); }}
        textarea {{ min-height: 100px; resize: vertical; font-family: inherit; }}
        label {{ display: block; font-size: 13px; font-weight: 500; color: #555; margin-bottom: 4px; margin-top: 12px; }}
        .form-row {{ display: flex; gap: 12px; }}
        .form-row > * {{ flex: 1; }}
        .result {{ background: #fafbfc; border: 1px solid #e8e8e8; border-radius: 6px; padding: 16px; white-space: pre-wrap; font-size: 14px; line-height: 1.8; max-height: 500px; overflow-y: auto; }}
        .compliance-pass {{ color: #389e0d; font-weight: 600; }}
        .compliance-fail {{ color: #cf1322; font-weight: 600; }}
        .sources {{ margin-top: 12px; padding-top: 12px; border-top: 1px solid #eee; font-size: 12px; color: #888; }}
        .loading {{ display: none; text-align: center; padding: 40px; color: #999; }}
        .loading.show {{ display: block; }}
        .spinner {{ display: inline-block; width: 32px; height: 32px; border: 3px solid #e8e8e8; border-top-color: #2d6da3; border-radius: 50%; animation: spin 0.8s linear infinite; }}
        @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }}
        .template-card {{ cursor: pointer; }}
        .template-card:hover {{ border-color: #2d6da3; background: #f0f7ff; }}
        .badge {{ display: inline-block; background: #e6f7ff; color: #1890ff; padding: 1px 6px; border-radius: 3px; font-size: 11px; margin-right: 4px; }}
        .output-box {{ background: #f6f8fa; border: 1px solid #e8e8e8; border-radius: 6px; padding: 16px; margin-top: 12px; }}
        .error {{ color: #cf1322; background: #fff1f0; padding: 8px 12px; border-radius: 4px; margin-top: 8px; }}
    </style>
</head>
<body>
<div class="header">
    <div class="container">
        <h1>金山云品牌内容量产工具</h1>
        <p>品牌官方AI量产助手 | RAG知识库驱动 | 合规自动审核</p>
    </div>
</div>

<div class="container">
    <div class="tabs">
        <button class="tab active" onclick="switchTab('generate')">内容生成</button>
        <button class="tab" onclick="switchTab('rag')">知识库检索</button>
        <button class="tab" onclick="switchTab('check')">合规检查</button>
        <button class="tab" onclick="switchTab('templates')">模板管理</button>
    </div>

    <!-- 内容生成面板 -->
    <div id="generate" class="panel active">
        <div class="card">
            <h3>系统状态</h3>
            <div style="display:flex;gap:16px;flex-wrap:wrap;">
                <span>RAG索引: <span class="status {'ok' if rag_ready else 'warn'}">{'已就绪' if rag_ready else '未构建'}</span></span>
                <span>API配置: <span class="status {'ok' if api_configured else 'err'}">{'已配置' if api_configured else '未配置'}</span></span>
                <span>知识库: <span class="status ok">{kb_docs} 篇文档</span></span>
                <span>模型: <span class="status ok">{config.LLM_CONFIG['model']}</span></span>
            </div>
        </div>

        <div class="card">
            <h3>单条内容生成</h3>
            <form id="genForm" onsubmit="return generateContent(event)">
                <div class="form-row">
                    <div>
                        <label>选择模板</label>
                        <select name="template" id="templateSelect">
                            {''.join(f'<option value="{t["name"]}">{t["name"]}</option>' for t in templates)}
                        </select>
                    </div>
                    <div>
                        <label>导出格式</label>
                        <select name="format">
                            <option value="markdown">Markdown</option>
                            <option value="html">HTML</option>
                            <option value="docx">Word</option>
                        </select>
                    </div>
                </div>
                <label>模板参数（每行一个 key=value）</label>
                <textarea name="params" id="paramsInput" placeholder="brand_name=金山云&#10;product_name=CDN&#10;version=3.0&#10;product_category=内容分发&#10;product_capability=内容加速&#10;sla_level=99.9%"></textarea>
                <div style="margin-top:12px;">
                    <button type="submit" class="btn btn-primary">生成内容</button>
                </div>
            </form>
            <div id="genLoading" class="loading"><div class="spinner"></div><p style="margin-top:8px;">正在生成，请稍候...</p></div>
            <div id="genResult" style="display:none;margin-top:16px;">
                <h3>生成结果 <span id="complianceTag"></span></h3>
                <div id="genContent" class="result"></div>
                <div id="genSources" class="sources"></div>
                <div id="genErrors" style="margin-top:8px;"></div>
            </div>
        </div>
    </div>

    <!-- RAG检索面板 -->
    <div id="rag" class="panel">
        <div class="card">
            <h3>知识库管理</h3>
            <p style="font-size:13px;color:#666;margin-bottom:12px;">当前 {kb_docs} 篇文档 | 索引状态: <span class="status {'ok' if rag_ready else 'warn'}">{'已构建' if rag_ready else '未构建'}</span></p>
            <button class="btn btn-primary" onclick="buildIndex()">构建/更新索引</button>
            <div id="buildResult" style="margin-top:8px;"></div>
        </div>
        <div class="card">
            <h3>知识库检索</h3>
            <div class="form-row">
                <div>
                    <label>检索关键词</label>
                    <input type="text" id="searchQuery" placeholder="例如: 金山云CDN" value="金山云CDN">
                </div>
                <div>
                    <label>类别筛选</label>
                    <select id="searchCategory">
                        <option value="">全部</option>
                        <option value="brand_guidelines">品牌规范</option>
                        <option value="product_capabilities">产品能力</option>
                        <option value="cases">案例库</option>
                        <option value="data">官方数据</option>
                        <option value="compliance">合规规范</option>
                    </select>
                </div>
            </div>
            <div style="margin-top:12px;">
                <button class="btn btn-primary" onclick="searchKB()">检索</button>
            </div>
            <div id="searchLoading" class="loading"><div class="spinner"></div><p style="margin-top:8px;">检索中...</p></div>
            <div id="searchResult" style="display:none;margin-top:16px;"></div>
        </div>
    </div>

    <!-- 合规检查面板 -->
    <div id="check" class="panel">
        <div class="card">
            <h3>内容合规检查</h3>
            <p style="font-size:13px;color:#666;margin-bottom:8px;">自动检测禁用词、品牌名规范、口径一致性</p>
            <label>待检查内容</label>
            <textarea id="checkContent" placeholder="粘贴要检查的内容...">金山云是最好的云服务商，行业第一，革命性的产品</textarea>
            <div style="margin-top:12px;">
                <button class="btn btn-primary" onclick="checkCompliance()">合规检查</button>
            </div>
        </div>
        <div id="checkResult" style="display:none;margin-top:16px;"></div>
    </div>

    <!-- 模板管理面板 -->
    <div id="templates" class="panel">
        <div class="grid">
            {''.join(f'''<div class="card template-card" onclick="showTemplate('{t["name"]}')">
                <span class="badge">{t["category"]}</span>
                <h3>{t["name"]}</h3>
                <p style="font-size:12px;color:#999;margin-top:4px;">{t["filename"]}</p>
            </div>''' for t in templates)}
        </div>
        <div id="templateDetail" style="display:none;margin-top:16px;">
            <div class="card">
                <h3 id="templateTitle"></h3>
                <p id="templateVars" style="font-size:13px;color:#666;margin:8px 0;"></p>
                <pre id="templateContent" style="background:#f6f8fa;padding:12px;border-radius:4px;overflow-x:auto;font-size:13px;white-space:pre-wrap;"></pre>
            </div>
        </div>
    </div>
</div>

<script>
function switchTab(id) {{
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    event.target.classList.add('active');
    document.getElementById(id).classList.add('active');
}}

async function generateContent(e) {{
    e.preventDefault();
    const form = new FormData(e.target);
    const template = form.get('template');
    const format = form.get('format');
    const paramsText = form.get('params');

    const params = {{}};
    paramsText.trim().split('\\n').forEach(line => {{
        if (line.includes('=')) {{
            const [k, v] = line.split('=', 2);
            params[k.trim()] = v.trim();
        }}
    }});

    document.getElementById('genLoading').classList.add('show');
    document.getElementById('genResult').style.display = 'none';

    try {{
        const resp = await fetch('/api/generate', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{template, params, format}})
        }});
        const data = await resp.json();
        document.getElementById('genLoading').classList.remove('show');
        document.getElementById('genResult').style.display = 'block';

        const tag = document.getElementById('complianceTag');
        if (data.compliance && data.compliance.passed) {{
            tag.innerHTML = '<span class="compliance-pass">合规通过</span>';
        }} else {{
            tag.innerHTML = '<span class="compliance-fail">合规未通过</span>';
        }}

        document.getElementById('genContent').textContent = data.content || '（无内容）';

        if (data.rag_sources && data.rag_sources.length > 0) {{
            document.getElementById('genSources').innerHTML = '<strong>RAG来源：</strong><br>' +
                data.rag_sources.map((s,i) => `${{i+1}}. ${{s.source}} (${{s.category}}, 相关度:${{(s.score||0).toFixed(2)}})`).join('<br>');
        }} else {{
            document.getElementById('genSources').innerHTML = '';
        }}

        if (data.compliance && (data.compliance.errors.length > 0 || data.compliance.warnings.length > 0)) {{
            let html = '';
            if (data.compliance.errors.length) html += '<div class="error">错误: ' + data.compliance.errors.join('; ') + '</div>';
            if (data.compliance.warnings.length) html += '<div style="color:#d48806;background:#fff8e1;padding:8px 12px;border-radius:4px;margin-top:4px;">警告: ' + data.compliance.warnings.join('; ') + '</div>';
            document.getElementById('genErrors').innerHTML = html;
        }} else {{
            document.getElementById('genErrors').innerHTML = '';
        }}
    }} catch(err) {{
        document.getElementById('genLoading').classList.remove('show');
        document.getElementById('genResult').style.display = 'block';
        document.getElementById('genContent').textContent = '生成失败: ' + err.message;
    }}
    return false;
}}

async function buildIndex() {{
    document.getElementById('buildResult').innerHTML = '<span style="color:#2d6da3;">构建中...</span>';
    try {{
        const resp = await fetch('/api/rag/build', {{method: 'POST'}});
        const data = await resp.json();
        document.getElementById('buildResult').innerHTML = '<span class="status ok">索引构建完成，共 ' + data.count + ' 个文本块</span>';
    }} catch(err) {{
        document.getElementById('buildResult').innerHTML = '<span class="error">构建失败: ' + err.message + '</span>';
    }}
}}

async function searchKB() {{
    const query = document.getElementById('searchQuery').value;
    const category = document.getElementById('searchCategory').value;
    document.getElementById('searchLoading').classList.add('show');
    document.getElementById('searchResult').style.display = 'none';

    try {{
        const resp = await fetch('/api/rag/search', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{query, category}})
        }});
        const data = await resp.json();
        document.getElementById('searchLoading').classList.remove('show');
        document.getElementById('searchResult').style.display = 'block';

        if (data.results && data.results.length > 0) {{
            document.getElementById('searchResult').innerHTML = data.results.map((r,i) =>
                `<div class="card"><h3>结果 ${{i+1}} <span class="badge">相关度: ${{(r.score||0).toFixed(2)}}</span> <span class="badge">${{r.category}}</span></h3>
                <p style="font-size:12px;color:#999;margin-bottom:4px;">来源: ${{r.source}}</p>
                <div style="white-space:pre-wrap;font-size:14px;line-height:1.8;">${{r.content}}</div></div>`
            ).join('');
        }} else {{
            document.getElementById('searchResult').innerHTML = '<div class="card"><p>未检索到相关内容</p></div>';
        }}
    }} catch(err) {{
        document.getElementById('searchLoading').classList.remove('show');
        document.getElementById('searchResult').innerHTML = '<div class="error">检索失败: ' + err.message + '</div>';
    }}
}}

async function checkCompliance() {{
    const content = document.getElementById('checkContent').value;
    try {{
        const resp = await fetch('/api/check', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{content}})
        }});
        const data = await resp.json();
        document.getElementById('checkResult').style.display = 'block';

        let html = '<div class="card"><h3>检查结果: ';
        if (data.passed) {{
            html += '<span class="compliance-pass">合规通过</span>';
        }} else {{
            html += '<span class="compliance-fail">合规未通过</span>';
        }}
        html += '</h3>';

        if (data.forbidden_word_hits && data.forbidden_word_hits.length > 0) {{
            html += '<p style="color:#cf1322;margin-top:8px;"><strong>命中禁用词:</strong> ' + data.forbidden_word_hits.join(', ') + '</p>';
        }}
        if (data.product_name_issues && data.product_name_issues.length > 0) {{
            html += '<p style="color:#d48806;margin-top:4px;"><strong>产品名问题:</strong> ' + data.product_name_issues.join(', ') + '</p>';
        }}
        if (data.errors && data.errors.length > 0) {{
            html += '<p style="color:#cf1322;margin-top:4px;"><strong>错误:</strong> ' + data.errors.join('; ') + '</p>';
        }}
        if (data.warnings && data.warnings.length > 0) {{
            html += '<p style="color:#d48806;margin-top:4px;"><strong>警告:</strong> ' + data.warnings.join('; ') + '</p>';
        }}
        if (data.passed && (!data.warnings || data.warnings.length === 0)) {{
            html += '<p style="color:#389e0d;margin-top:8px;">内容完全合规，可以发布。</p>';
        }}
        html += '</div>';
        document.getElementById('checkResult').innerHTML = html;
    }} catch(err) {{
        document.getElementById('checkResult').innerHTML = '<div class="error">检查失败: ' + err.message + '</div>';
    }}
}}

function showTemplate(name) {{
    fetch('/api/template/' + encodeURIComponent(name))
        .then(r => r.json())
        .then(data => {{
            document.getElementById('templateDetail').style.display = 'block';
            document.getElementById('templateTitle').textContent = data.name;
            document.getElementById('templateVars').textContent = data.variables && data.variables.length > 0
                ? '变量: ' + data.variables.join(', ') : '无变量';
            document.getElementById('templateContent').textContent = data.content;
        }});
}}
</script>
</body>
</html>"""


# === API 接口 ===

@app.post("/api/generate")
async def api_generate(request: Request):
    """内容生成接口"""
    body = await request.json()
    template_name = body.get("template", "")
    params = body.get("params", {})
    fmt = body.get("format", "markdown")

    try:
        generator = BatchGenerator()
        result = generator.generate_single(template_name, params)

        # 导出
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_dir = Path(config.EXPORT_CONFIG["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)

        ext = {"markdown": ".md", "html": ".html", "docx": ".docx"}.get(fmt, ".md")
        filepath = output_dir / f"{template_name.replace('/', '_')}_{timestamp}{ext}"

        metadata = {
            "template_name": template_name,
            "generated_at": result.generated_at,
            "model": result.model,
            "compliance_passed": result.compliance.passed,
        }

        exporter = {"markdown": MarkdownExporter, "html": HTMLExporter, "docx": DocxExporter}.get(fmt, MarkdownExporter)()
        exporter.export(
            content=result.content,
            output_path=str(filepath),
            metadata=metadata,
            rag_sources=result.rag_sources,
        )

        return {
            "content": result.content,
            "compliance": {
                "passed": result.compliance.passed,
                "errors": result.compliance.errors,
                "warnings": result.compliance.warnings,
                "forbidden_word_hits": result.compliance.forbidden_word_hits,
                "product_name_issues": result.compliance.product_name_issues,
            },
            "rag_sources": result.rag_sources,
            "output_file": str(filepath),
        }
    except Exception as e:
        return JSONResponse({"content": f"生成失败: {e}", "compliance": {"passed": False, "errors": [str(e)], "warnings": [], "forbidden_word_hits": [], "product_name_issues": []}, "rag_sources": []}, status_code=500)


@app.post("/api/rag/build")
async def api_rag_build():
    """构建RAG索引"""
    count = embedder.build_index()
    return {"count": count}


@app.post("/api/rag/search")
async def api_rag_search(request: Request):
    """RAG检索"""
    body = await request.json()
    query = body.get("query", "")
    category = body.get("category", "") or None
    results = retriever.search(query, category=category)
    return {
        "results": [
            {"content": r.content, "source": r.source, "category": r.category,
             "score": r.score, "chunk_index": r.chunk_index}
            for r in results
        ]
    }


@app.post("/api/check")
async def api_check(request: Request):
    """合规检查"""
    body = await request.json()
    content = body.get("content", "")
    result = validator.validate(content)
    return {
        "passed": result.passed,
        "errors": result.errors,
        "warnings": result.warnings,
        "forbidden_word_hits": result.forbidden_word_hits,
        "product_name_issues": result.product_name_issues,
    }


@app.get("/api/template/{name}")
async def api_template_detail(name: str):
    """模板详情"""
    info = template_manager.get_template_info(name)
    if info is None:
        return JSONResponse({"error": "模板不存在"}, status_code=404)
    return info
