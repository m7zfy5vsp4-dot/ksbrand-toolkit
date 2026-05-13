"""合规规则加载模块"""

import re
import sys
from pathlib import Path

# 确保项目根目录在sys.path中
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import config


class ComplianceRules:
    """从config.py加载合规规则，供审核器使用"""

    def __init__(self):
        self.brand_name = config.BRAND_NAME
        self.brand_tone = config.BRAND_TONE
        self.forbidden_words = config.FORBIDDEN_WORDS
        self.forbidden_patterns = config.FORBIDDEN_PATTERNS
        self.required_disclaimers = config.REQUIRED_DISCLAIMERS
        self.product_names = config.PRODUCT_NAMES
        self.approved_claims = config.APPROVED_CLAIMS

    def get_forbidden_regex(self) -> re.Pattern:
        """将禁用词列表编译为正则表达式"""
        escaped = [re.escape(w) for w in self.forbidden_words]
        pattern = "|".join(escaped)
        return re.compile(pattern)

    def get_forbidden_pattern_regex(self) -> re.Pattern:
        """将禁用正则模式编译"""
        pattern = "|".join(f"({p})" for p in self.forbidden_patterns)
        return re.compile(pattern)

    def get_product_name_variants(self) -> dict[str, str]:
        """返回产品名别名→官方名的映射"""
        return dict(self.product_names)

    def get_tone_instruction(self) -> str:
        """生成文风约束指令文本"""
        tone = self.brand_tone
        do_items = "\n".join(f"  - {item}" for item in tone["do"])
        dont_items = "\n".join(f"  - {item}" for item in tone["dont"])
        return (
            f"【品牌文风要求】\n"
            f"文风: {tone['style']}\n"
            f"关键词: {', '.join(tone['keywords'])}\n"
            f"描述: {tone['description']}\n"
            f"应当:\n{do_items}\n"
            f"禁止:\n{dont_items}"
        )

    def get_compliance_prompt_section(self) -> str:
        """生成注入Prompt的合规约束段落"""
        forbidden_list = "、".join(self.forbidden_words[:20])  # 截取前20个避免过长
        return (
            f"【合规约束】\n"
            f"1. 品牌名必须使用「{self.brand_name}」官方写法\n"
            f"2. 严禁使用以下禁用词: {forbidden_list}等\n"
            f"3. 所有事实性宣称必须有RAG知识库来源支撑，不得编造\n"
            f"4. 文风必须遵循{self.brand_tone['style']}要求\n"
            f"5. 不得引用未经授权的竞品对比数据\n"
        )
