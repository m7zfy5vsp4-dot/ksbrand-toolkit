"""Jinja2模板渲染模块"""

from jinja2 import Environment, FileSystemLoader, BaseLoader, TemplateError


class TemplateRenderer:
    """使用Jinja2渲染内容模板"""

    def __init__(self, templates_dir: str = "templates"):
        self.templates_dir = templates_dir
        self._env = None

    def _get_env(self, search_path: str | None = None) -> Environment:
        """获取Jinja2环境"""
        if self._env is None or search_path:
            path = search_path or self.templates_dir
            self._env = Environment(
                loader=FileSystemLoader(path),
                autoescape=False,
                keep_trailing_newline=True,
            )
        return self._env

    def render_file(self, template_name: str, **params) -> str:
        """从模板文件渲染内容"""
        try:
            env = self._get_env()
            template = env.get_template(template_name)
            return template.render(**params)
        except TemplateError as e:
            return f"[模板渲染错误] {e}"

    def render_string(self, template_content: str, **params) -> str:
        """从字符串渲染模板"""
        try:
            env = Environment(loader=BaseLoader(), autoescape=False)
            template = env.from_string(template_content)
            return template.render(**params)
        except TemplateError as e:
            return f"[模板渲染错误] {e}"

    def render_with_metadata(self, template_name: str, **params) -> dict:
        """渲染模板并附带元数据"""
        content = self.render_file(template_name, **params)
        return {
            "content": content,
            "template_name": template_name,
            "params": params,
        }
