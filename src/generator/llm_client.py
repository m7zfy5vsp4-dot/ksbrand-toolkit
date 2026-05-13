"""LLM调用客户端模块"""

import os
import json
from typing import Optional


class LLMClient:
    """OpenAI兼容API客户端，支持金山云内部大模型"""

    def __init__(self, api_base: Optional[str] = None,
                 api_key: Optional[str] = None,
                 model: Optional[str] = None,
                 temperature: Optional[float] = None,
                 max_tokens: Optional[int] = None,
                 timeout: Optional[int] = None):
        import sys
        from pathlib import Path
        project_root = str(Path(__file__).resolve().parent.parent.parent)
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        import config

        self.api_base = api_base or os.environ.get("OPENAI_API_BASE", config.LLM_CONFIG["api_base"])
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.model = model or config.LLM_CONFIG["model"]
        self.temperature = temperature if temperature is not None else config.LLM_CONFIG["temperature"]
        self.max_tokens = max_tokens or config.LLM_CONFIG["max_tokens"]
        self.timeout = timeout or config.LLM_CONFIG["timeout"]

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """调用LLM生成内容"""
        try:
            from openai import OpenAI
            import httpx
        except ImportError:
            raise ImportError("请安装openai包: pip install openai")

        client = OpenAI(
            api_key=self.api_key,
            base_url=self.api_base,
            timeout=httpx.Timeout(self.timeout, connect=10.0),
        )

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise RuntimeError(f"LLM调用失败: {e}")

    def generate_with_sources(self, prompt: str,
                              system_prompt: Optional[str] = None) -> dict:
        """调用LLM生成内容（来源标注已集成在prompt_builder中）"""
        content = self.generate(prompt, system_prompt)
        return {
            "content": content,
            "model": self.model,
            "api_base": self.api_base,
        }
