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
        :root {{
            --ks-blue: #0052D9;
            --ks-blue-light: #4E8BF9;
            --ks-blue-dark: #003DA5;
            --ks-orange: #FF7D00;
            --ks-orange-light: #FFA040;
            --ks-navy: #1A2332;
            --ks-bg: #F5F7FA;
            --ks-card: #FFFFFF;
            --ks-border: #E4E7ED;
            --ks-text: #1D2129;
            --ks-text-secondary: #4E5969;
            --ks-text-muted: #86909C;
            --ks-success: #00B42A;
            --ks-warning: #FF7D00;
            --ks-danger: #F53F3F;
            --ks-radius: 8px;
            --ks-shadow: 0 2px 12px rgba(0,0,0,0.06);
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif; background: var(--ks-bg); color: var(--ks-text); line-height: 1.6; }}

        /* Header */
        .header {{
            background: linear-gradient(135deg, var(--ks-navy) 0%, #0A3A6E 50%, var(--ks-blue) 100%);
            padding: 0;
            position: relative;
            overflow: hidden;
        }}
        .header::before {{
            content: '';
            position: absolute;
            top: -50%;
            right: -10%;
            width: 400px;
            height: 400px;
            background: radial-gradient(circle, rgba(255,125,0,0.15) 0%, transparent 70%);
            border-radius: 50%;
        }}
        .header::after {{
            content: '';
            position: absolute;
            bottom: -30%;
            left: 20%;
            width: 300px;
            height: 300px;
            background: radial-gradient(circle, rgba(78,139,249,0.2) 0%, transparent 70%);
            border-radius: 50%;
        }}
        .header-inner {{ position: relative; z-index: 1; max-width: 1200px; margin: 0 auto; padding: 28px 24px 24px; }}
        .header-brand {{ display: flex; align-items: center; gap: 16px; margin-bottom: 8px; }}
        .header-logo {{
            width: 44px; height: 44px; background: var(--ks-orange); border-radius: 10px;
            display: flex; align-items: center; justify-content: center;
            font-size: 20px; font-weight: 800; color: white; box-shadow: 0 4px 12px rgba(255,125,0,0.3);
        }}
        .header h1 {{ font-size: 22px; font-weight: 600; color: white; letter-spacing: 0.5px; }}
        .header-sub {{ font-size: 13px; color: rgba(255,255,255,0.65); margin-left: 60px; }}

        /* Stats bar */
        .stats-bar {{
            display: flex; gap: 24px; margin-top: 16px; padding-top: 16px;
            border-top: 1px solid rgba(255,255,255,0.1);
        }}
        .stat-item {{ display: flex; align-items: center; gap: 8px; }}
        .stat-dot {{ width: 6px; height: 6px; border-radius: 50%; }}
        .stat-dot.green {{ background: var(--ks-success); box-shadow: 0 0 6px var(--ks-success); }}
        .stat-dot.orange {{ background: var(--ks-warning); box-shadow: 0 0 6px var(--ks-warning); }}
        .stat-dot.red {{ background: var(--ks-danger); box-shadow: 0 0 6px var(--ks-danger); }}
        .stat-label {{ font-size: 12px; color: rgba(255,255,255,0.6); }}
        .stat-value {{ font-size: 13px; color: white; font-weight: 500; }}

        /* Container */
        .container {{ max-width: 1200px; margin: 0 auto; padding: 0 24px; }}

        /* Tabs */
        .tabs {{
            display: flex; gap: 0; margin-top: 24px;
            background: var(--ks-card); border-radius: var(--ks-radius) var(--ks-radius) 0 0;
            box-shadow: var(--ks-shadow); border-bottom: 1px solid var(--ks-border);
        }}
        .tab {{
            padding: 14px 28px; cursor: pointer; border: none; background: none;
            font-size: 14px; color: var(--ks-text-muted); font-weight: 500;
            border-bottom: 2px solid transparent; transition: all 0.25s;
            position: relative;
        }}
        .tab:hover {{ color: var(--ks-blue); }}
        .tab.active {{ color: var(--ks-blue); border-bottom-color: var(--ks-blue); font-weight: 600; }}
        .tab.active::after {{
            content: ''; position: absolute; bottom: -1px; left: 20%; right: 20%;
            height: 2px; background: var(--ks-blue); border-radius: 1px;
        }}
        .tab-icon {{ margin-right: 6px; font-size: 15px; }}

        /* Panels */
        .panel {{ display: none; background: var(--ks-card); padding: 24px; border-radius: 0 0 var(--ks-radius) var(--ks-radius); box-shadow: var(--ks-shadow); min-height: 400px; }}
        .panel.active {{ display: block; }}

        /* Cards */
        .card {{ background: var(--ks-bg); border: 1px solid var(--ks-border); border-radius: var(--ks-radius); padding: 20px; margin-bottom: 16px; transition: all 0.2s; }}
        .card:hover {{ border-color: var(--ks-blue-light); }}
        .card h3 {{ font-size: 15px; color: var(--ks-blue-dark); margin-bottom: 10px; display: flex; align-items: center; gap: 8px; }}
        .card h3::before {{ content: ''; width: 3px; height: 16px; background: var(--ks-orange); border-radius: 2px; }}

        /* Buttons */
        .btn {{
            display: inline-flex; align-items: center; gap: 6px;
            padding: 10px 24px; border-radius: 6px; border: none; font-size: 14px;
            cursor: pointer; transition: all 0.25s; font-weight: 500;
        }}
        .btn-primary {{ background: var(--ks-blue); color: white; box-shadow: 0 2px 8px rgba(0,82,217,0.25); }}
        .btn-primary:hover {{ background: var(--ks-blue-dark); transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,82,217,0.35); }}
        .btn-outline {{ background: white; color: var(--ks-blue); border: 1px solid var(--ks-blue); }}
        .btn-outline:hover {{ background: #F0F5FF; }}

        /* Forms */
        input, textarea, select {{
            width: 100%; padding: 10px 14px; border: 1px solid var(--ks-border);
            border-radius: 6px; font-size: 14px; transition: all 0.2s;
            background: white;
        }}
        input:focus, textarea:focus, select:focus {{
            outline: none; border-color: var(--ks-blue);
            box-shadow: 0 0 0 3px rgba(0,82,217,0.08);
        }}
        textarea {{ min-height: 120px; resize: vertical; font-family: inherit; }}
        label {{ display: block; font-size: 13px; font-weight: 600; color: var(--ks-text-secondary); margin-bottom: 6px; margin-top: 16px; }}
        .form-row {{ display: flex; gap: 16px; }}
        .form-row > div {{ flex: 1; }}

        /* Results */
        .result {{ background: var(--ks-bg); border: 1px solid var(--ks-border); border-radius: var(--ks-radius); padding: 20px; white-space: pre-wrap; font-size: 14px; line-height: 1.8; max-height: 500px; overflow-y: auto; }}
        .compliance-pass {{ color: var(--ks-success); font-weight: 600; }}
        .compliance-fail {{ color: var(--ks-danger); font-weight: 600; }}
        .sources {{ margin-top: 14px; padding-top: 14px; border-top: 1px solid var(--ks-border); font-size: 12px; color: var(--ks-text-muted); }}

        /* Status tags */
        .tag {{ display: inline-flex; align-items: center; gap: 4px; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 500; }}
        .tag-ok {{ background: #E8F7ED; color: var(--ks-success); }}
        .tag-warn {{ background: #FFF3E8; color: var(--ks-warning); }}
        .tag-err {{ background: #FFECE8; color: var(--ks-danger); }}

        /* Loading */
        .loading {{ display: none; text-align: center; padding: 48px; color: var(--ks-text-muted); }}
        .loading.show {{ display: block; }}
        .spinner {{
            width: 36px; height: 36px; border: 3px solid var(--ks-border);
            border-top-color: var(--ks-blue); border-radius: 50%;
            animation: spin 0.8s linear infinite; margin: 0 auto 12px;
        }}
        @keyframes spin {{ to {{ transform: rotate(360deg); }} }}

        /* Template grid */
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 14px; }}
        .template-card {{ cursor: pointer; transition: all 0.25s; }}
        .template-card:hover {{ border-color: var(--ks-blue-light); box-shadow: 0 4px 16px rgba(0,82,217,0.1); transform: translateY(-2px); }}
        .badge {{
            display: inline-flex; align-items: center; gap: 2px;
            background: #F0F5FF; color: var(--ks-blue); padding: 2px 8px;
            border-radius: 4px; font-size: 11px; font-weight: 500;
        }}
        .badge-orange {{ background: #FFF7E8; color: var(--ks-orange); }}

        /* Error / Warning boxes */
        .error-box {{ color: var(--ks-danger); background: #FFECE8; padding: 10px 14px; border-radius: 6px; margin-top: 10px; border-left: 3px solid var(--ks-danger); }}
        .warn-box {{ color: #A66800; background: #FFF7E8; padding: 10px 14px; border-radius: 6px; margin-top: 10px; border-left: 3px solid var(--ks-orange); }}
        .success-box {{ color: #008A40; background: #E8F7ED; padding: 10px 14px; border-radius: 6px; margin-top: 10px; border-left: 3px solid var(--ks-success); }}

        /* Footer */
        .footer {{ text-align: center; padding: 24px; color: var(--ks-text-muted); font-size: 12px; margin-top: 32px; }}
        .footer a {{ color: var(--ks-blue); text-decoration: none; }}

        /* Scrollbar */
        ::-webkit-scrollbar {{ width: 6px; }}
        ::-webkit-scrollbar-track {{ background: transparent; }}
        ::-webkit-scrollbar-thumb {{ background: #C9CDD4; border-radius: 3px; }}
        ::-webkit-scrollbar-thumb:hover {{ background: #86909C; }}
    </style>
</head>
<body>

<div class="header">
    <div class="header-inner">
        <div class="header-brand">
            <div class="header-logo">KS</div>
            <h1>金山云品牌内容量产工具</h1>
        </div>
        <div class="header-sub">Kingsoft Cloud Brand Content Toolkit | RAG知识库驱动 | 合规自动审核 | AI量产</div>
        <div class="stats-bar">
            <div class="stat-item">
                <span class="stat-dot {'green' if rag_ready else 'orange'}"></span>
                <span class="stat-label">RAG索引</span>
                <span class="stat-value">{'已就绪' if rag_ready else '未构建'}</span>
            </div>
            <div class="stat-item">
                <span class="stat-dot {'green' if api_configured else 'red'}"></span>
                <span class="stat-label">API</span>
                <span class="stat-value">{'已配置' if api_configured else '未配置'}</span>
            </div>
            <div class="stat-item">
                <span class="stat-dot green"></span>
                <span class="stat-label">知识库</span>
                <span class="stat-value">{kb_docs} 篇文档</span>
            </div>
            <div class="stat-item">
                <span class="stat-dot green"></span>
                <span class="stat-label">模型</span>
                <span class="stat-value">{config.LLM_CONFIG['model']}</span>
            </div>
        </div>
    </div>
</div>

<div class="container">
    <div class="tabs">
        <button class="tab active" onclick="switchTab('generate')"><span class="tab-icon">&#9998;</span>内容生成</button>
        <button class="tab" onclick="switchTab('rag')"><span class="tab-icon">&#128269;</span>知识库检索</button>
        <button class="tab" onclick="switchTab('check')"><span class="tab-icon">&#9989;</span>合规检查</button>
        <button class="tab" onclick="switchTab('templates')"><span class="tab-icon">&#128196;</span>模板管理</button>
    </div>

    <!-- 内容生成 -->
    <div id="generate" class="panel active">
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
                            <option value="markdown">Markdown (.md)</option>
                            <option value="html">HTML (.html)</option>
                            <option value="docx">Word (.docx)</option>
                        </select>
                    </div>
                </div>
                <label>模板参数（每行一个 key=value）</label>
                <textarea name="params" id="paramsInput" placeholder="brand_name=金山云&#10;product_name=CDN&#10;version=3.0&#10;product_category=内容分发&#10;product_capability=内容加速&#10;sla_level=99.9%"></textarea>
                <div style="margin-top:16px;">
                    <button type="submit" class="btn btn-primary">&#9654; 生成内容</button>
                </div>
            </form>
            <div id="genLoading" class="loading"><div class="spinner"></div><p>正在生成，请稍候...</p></div>
            <div id="genResult" style="display:none;margin-top:20px;">
                <h3 style="margin-bottom:12px;">生成结果 <span id="complianceTag"></span></h3>
                <div id="genContent" class="result"></div>
                <div id="genSources" class="sources"></div>
                <div id="genErrors" style="margin-top:10px;"></div>
            </div>
        </div>
    </div>

    <!-- 知识库检索 -->
    <div id="rag" class="panel">
        <div class="card">
            <h3>知识库管理</h3>
            <p style="font-size:13px;color:var(--ks-text-muted);margin-bottom:14px;">当前 <strong>{kb_docs}</strong> 篇文档 | 索引状态: <span class="tag {'tag-ok' if rag_ready else 'tag-warn'}">{'已构建' if rag_ready else '未构建'}</span></p>
            <button class="btn btn-primary" onclick="buildIndex()">&#128640; 构建/更新索引</button>
            <div id="buildResult" style="margin-top:10px;"></div>
        </div>
        <div class="card">
            <h3>知识库检索</h3>
            <div class="form-row">
                <div>
                    <label>检索关键词</label>
                    <input type="text" id="searchQuery" placeholder="例如: 金山云星流平台" value="金山云星流平台">
                </div>
                <div>
                    <label>类别筛选</label>
                    <select id="searchCategory">
                        <option value="">全部类别</option>
                        <option value="brand_guidelines">品牌规范</option>
                        <option value="product_capabilities">产品能力</option>
                        <option value="cases">案例库</option>
                        <option value="data">官方数据</option>
                        <option value="compliance">合规规范</option>
                    </select>
                </div>
            </div>
            <div style="margin-top:14px;">
                <button class="btn btn-primary" onclick="searchKB()">&#128270; 检索</button>
            </div>
            <div id="searchLoading" class="loading"><div class="spinner"></div><p>检索中...</p></div>
            <div id="searchResult" style="display:none;margin-top:20px;"></div>
        </div>
    </div>

    <!-- 合规检查 -->
    <div id="check" class="panel">
        <div class="card">
            <h3>内容合规检查</h3>
            <p style="font-size:13px;color:var(--ks-text-muted);margin-bottom:8px;">自动检测禁用词、品牌名规范、口径一致性</p>
            <label>待检查内容</label>
            <textarea id="checkContent" placeholder="粘贴要检查的内容...">金山云是最好的云服务商，行业第一，革命性的产品</textarea>
            <div style="margin-top:14px;">
                <button class="btn btn-primary" onclick="checkCompliance()">&#9989; 合规检查</button>
            </div>
        </div>
        <div id="checkResult" style="display:none;margin-top:20px;"></div>
    </div>

    <!-- 模板管理 -->
    <div id="templates" class="panel">
        <div class="grid">
            {''.join(f'''<div class="card template-card" onclick="showTemplate('{t["name"]}')">
                <span class="badge badge-orange">{t["category"]}</span>
                <h3>{t["name"]}</h3>
                <p style="font-size:12px;color:var(--ks-text-muted);margin-top:6px;">{t["filename"]}</p>
            </div>''' for t in templates)}
        </div>
        <div id="templateDetail" style="display:none;margin-top:20px;">
            <div class="card">
                <h3 id="templateTitle"></h3>
                <p id="templateVars" style="font-size:13px;color:var(--ks-text-secondary);margin:10px 0;"></p>
                <pre id="templateContent" style="background:var(--ks-bg);padding:14px;border-radius:6px;overflow-x:auto;font-size:13px;white-space:pre-wrap;border:1px solid var(--ks-border);"></pre>
            </div>
        </div>
    </div>
</div>

<div class="footer">
    <p>金山云品牌内容量产工具 v1.0 | Powered by RAG + LLM</p>
    <p style="margin-top:4px;"><a href="https://www.ksyun.com" target="_blank">www.ksyun.com</a></p>
</div>

<script>
function switchTab(id) {{
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    event.target.closest('.tab').classList.add('active');
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
            tag.innerHTML = '<span class="compliance-pass">&#10003; 合规通过</span>';
        }} else {{
            tag.innerHTML = '<span class="compliance-fail">&#10007; 合规未通过</span>';
        }}

        document.getElementById('genContent').textContent = data.content || '（无内容）';

        if (data.rag_sources && data.rag_sources.length > 0) {{
            document.getElementById('genSources').innerHTML = '<strong>RAG来源：</strong><br>' +
                data.rag_sources.map((s,i) => `${{i+1}}. ${{s.source}} (${{s.category}}, 相关度:${{(s.score||0).toFixed(2)}})`).join('<br>');
        }} else {{
            document.getElementById('genSources').innerHTML = '';
        }}

        let errHtml = '';
        if (data.compliance && data.compliance.errors.length > 0) {{
            errHtml += '<div class="error-box">' + data.compliance.errors.join('; ') + '</div>';
        }}
        if (data.compliance && data.compliance.warnings.length > 0) {{
            errHtml += '<div class="warn-box">' + data.compliance.warnings.join('; ') + '</div>';
        }}
        if (data.compliance && data.compliance.passed && data.compliance.warnings.length === 0) {{
            errHtml = '<div class="success-box">内容完全合规，可以发布。</div>';
        }}
        document.getElementById('genErrors').innerHTML = errHtml;
    }} catch(err) {{
        document.getElementById('genLoading').classList.remove('show');
        document.getElementById('genResult').style.display = 'block';
        document.getElementById('genContent').textContent = '生成失败: ' + err.message;
    }}
    return false;
}}

async function buildIndex() {{
    document.getElementById('buildResult').innerHTML = '<span style="color:var(--ks-blue);">构建中...</span>';
    try {{
        const resp = await fetch('/api/rag/build', {{method: 'POST'}});
        const data = await resp.json();
        document.getElementById('buildResult').innerHTML = '<div class="success-box">索引构建完成，共 ' + data.count + ' 个文本块</div>';
    }} catch(err) {{
        document.getElementById('buildResult').innerHTML = '<div class="error-box">构建失败: ' + err.message + '</div>';
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
                `<div class="card"><h3>结果 ${{i+1}} <span class="badge">相关度: ${{(r.score||0).toFixed(2)}}</span> <span class="badge badge-orange">${{r.category}}</span></h3>
                <p style="font-size:12px;color:var(--ks-text-muted);margin-bottom:6px;">来源: ${{r.source}}</p>
                <div style="white-space:pre-wrap;font-size:14px;line-height:1.8;">${{r.content}}</div></div>`
            ).join('');
        }} else {{
            document.getElementById('searchResult').innerHTML = '<div class="card"><p style="color:var(--ks-text-muted);">未检索到相关内容</p></div>';
        }}
    }} catch(err) {{
        document.getElementById('searchLoading').classList.remove('show');
        document.getElementById('searchResult').innerHTML = '<div class="error-box">检索失败: ' + err.message + '</div>';
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
            html += '<span class="compliance-pass">&#10003; 合规通过</span>';
        }} else {{
            html += '<span class="compliance-fail">&#10007; 合规未通过</span>';
        }}
        html += '</h3>';

        if (data.forbidden_word_hits && data.forbidden_word_hits.length > 0) {{
            html += '<div class="error-box" style="margin-top:12px;"><strong>命中禁用词:</strong> ' + data.forbidden_word_hits.join(', ') + '</div>';
        }}
        if (data.product_name_issues && data.product_name_issues.length > 0) {{
            html += '<div class="warn-box" style="margin-top:8px;"><strong>产品名问题:</strong> ' + data.product_name_issues.join(', ') + '</div>';
        }}
        if (data.errors && data.errors.length > 0) {{
            html += '<div class="error-box" style="margin-top:8px;">' + data.errors.join('; ') + '</div>';
        }}
        if (data.warnings && data.warnings.length > 0) {{
            html += '<div class="warn-box" style="margin-top:8px;">' + data.warnings.join('; ') + '</div>';
        }}
        if (data.passed && (!data.warnings || data.warnings.length === 0)) {{
            html += '<div class="success-box" style="margin-top:12px;">内容完全合规，可以发布。</div>';
        }}
        html += '</div>';
        document.getElementById('checkResult').innerHTML = html;
    }} catch(err) {{
        document.getElementById('checkResult').innerHTML = '<div class="error-box">检查失败: ' + err.message + '</div>';
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
