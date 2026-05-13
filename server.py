#!/usr/bin/env python3
"""启动Web服务"""

import sys
import os
from pathlib import Path

project_root = str(Path(__file__).resolve().parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import uvicorn

if __name__ == "__main__":
    host = os.environ.get("KSBRAND_HOST", "0.0.0.0")
    port = int(os.environ.get("KSBRAND_PORT", "8000"))
    print(f"启动金山云品牌内容量产工具 Web界面...")
    print(f"访问地址: http://localhost:{port}")
    print(f"按 Ctrl+C 停止服务")
    uvicorn.run("src.web.app:app", host=host, port=port, reload=False)
