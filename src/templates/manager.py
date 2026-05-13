"""模板CRUD管理模块"""

import os
from pathlib import Path
from typing import Optional


class TemplateManager:
    """管理内容模板的增删改查"""

    TEMPLATE_CATEGORIES = [
        "social_media",
        "press_release",
        "product_announce",
        "marketing",
    ]

    def __init__(self, templates_dir: str = "templates"):
        self.templates_dir = Path(templates_dir)

    def list_templates(self, category: Optional[str] = None) -> list[dict]:
        """列出所有模板"""
        templates = []

        search_dirs = []
        if category:
            cat_dir = self.templates_dir / category
            if cat_dir.exists():
                search_dirs = [cat_dir]
        else:
            for cat in self.TEMPLATE_CATEGORIES:
                cat_dir = self.templates_dir / cat
                if cat_dir.exists():
                    search_dirs.append(cat_dir)

        for cat_dir in search_dirs:
            cat_name = cat_dir.name
            for filename in sorted(os.listdir(cat_dir)):
                if filename.endswith(".j2") or filename.endswith(".jinja2"):
                    filepath = cat_dir / filename
                    name = filename.rsplit(".", 1)[0]
                    templates.append({
                        "name": f"{cat_name}/{name}",
                        "category": cat_name,
                        "filename": filename,
                        "path": str(filepath),
                    })

        return templates

    def load_template(self, template_name: str) -> Optional[str]:
        """加载模板内容

        Args:
            template_name: 格式为 "category/name" 或完整路径
        """
        # 尝试 category/name 格式
        if "/" in template_name:
            parts = template_name.split("/", 1)
            category, name = parts[0], parts[1]
            for ext in [".j2", ".jinja2"]:
                filepath = self.templates_dir / category / (name + ext)
                if filepath.exists():
                    return filepath.read_text(encoding="utf-8")

        # 尝试直接搜索
        for cat in self.TEMPLATE_CATEGORIES:
            cat_dir = self.templates_dir / cat
            if not cat_dir.exists():
                continue
            for filename in os.listdir(cat_dir):
                if (filename.endswith(".j2") or filename.endswith(".jinja2")):
                    name = filename.rsplit(".", 1)[0]
                    if name == template_name or f"{cat}/{name}" == template_name:
                        return (cat_dir / filename).read_text(encoding="utf-8")

        return None

    def get_template_info(self, template_name: str) -> Optional[dict]:
        """获取模板详细信息"""
        content = self.load_template(template_name)
        if content is None:
            return None

        # 解析模板中的变量
        from jinja2 import Environment, BaseLoader
        env = Environment(loader=BaseLoader())
        try:
            ast = env.parse(content)
            variables = list(env.find_undeclared_variables(ast))
        except Exception:
            variables = []

        # 提取模板头部注释
        description = ""
        lines = content.strip().split("\n")
        if lines and lines[0].startswith("{#"):
            for line in lines:
                description += line.replace("{#", "").replace("#}", "").strip() + " "
                if "#}" in line:
                    break

        return {
            "name": template_name,
            "content": content,
            "variables": variables,
            "description": description.strip(),
        }

    def create_template(self, category: str, name: str,
                        content: str) -> str:
        """创建新模板"""
        if category not in self.TEMPLATE_CATEGORIES:
            raise ValueError(f"不支持的模板分类: {category}")

        cat_dir = self.templates_dir / category
        cat_dir.mkdir(parents=True, exist_ok=True)

        filepath = cat_dir / f"{name}.j2"
        if filepath.exists():
            raise FileExistsError(f"模板已存在: {category}/{name}")

        filepath.write_text(content, encoding="utf-8")
        return f"{category}/{name}"
