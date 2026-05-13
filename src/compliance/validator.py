"""合规校验器模块"""

import re
from dataclasses import dataclass, field
from .rules import ComplianceRules


@dataclass
class ValidationResult:
    """校验结果"""
    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    forbidden_word_hits: list[str] = field(default_factory=list)
    product_name_issues: list[str] = field(default_factory=list)
    claim_issues: list[str] = field(default_factory=list)


class ComplianceValidator:
    """对生成内容进行合规审核"""

    def __init__(self, rules: ComplianceRules | None = None):
        self.rules = rules or ComplianceRules()
        self._forbidden_regex = self.rules.get_forbidden_regex()
        self._forbidden_pattern_regex = self.rules.get_forbidden_pattern_regex()
        self._product_variants = self.rules.get_product_name_variants()

    def validate(self, text: str, content_type: str = "general") -> ValidationResult:
        """执行完整合规校验"""
        result = ValidationResult(passed=True)

        self._check_forbidden_words(text, result)
        self._check_forbidden_patterns(text, result)
        self._check_product_names(text, result)
        self._check_brand_name(text, result)
        self._check_disclaimer(text, content_type, result)

        if result.errors:
            result.passed = False
        return result

    def _check_forbidden_words(self, text: str, result: ValidationResult):
        """检测禁用词"""
        matches = self._forbidden_regex.findall(text)
        if matches:
            unique_matches = list(set(matches))
            result.forbidden_word_hits = unique_matches
            result.errors.append(
                f"检测到禁用词: {', '.join(unique_matches)}"
            )

    def _check_forbidden_patterns(self, text: str, result: ValidationResult):
        """检测禁用正则模式"""
        matches = self._forbidden_pattern_regex.findall(text)
        if matches:
            unique_matches = list(set(str(m) for m in matches if m))
            if unique_matches:
                result.errors.append(
                    f"检测到禁用表达模式: {', '.join(unique_matches)}"
                )

    def _check_product_names(self, text: str, result: ValidationResult):
        """检测非官方产品名写法"""
        for alias, official in self._product_variants.items():
            # 检查文本中是否出现了非官方写法（但不是官方名本身）
            # 仅当alias不等于official时才检查
            if alias != official and alias in text.lower():
                # 避免误报：如果官方名已经在文本中，跳过
                if official not in text:
                    result.product_name_issues.append(
                        f"产品名不规范: 建议将「{alias}」改为「{official}」"
                    )
                    result.warnings.append(
                        f"产品名不规范: 建议将「{alias}」改为「{official}」"
                    )

    def _check_brand_name(self, text: str, result: ValidationResult):
        """检查品牌名是否规范"""
        brand = self.rules.brand_name
        # 检查是否包含不规范写法
        if "金山云" in text and f"{brand}" not in text:
            # 如果只是部分匹配，给出警告
            result.warnings.append("请确保品牌名使用完整官方写法「金山云」")

    def _check_disclaimer(self, text: str, content_type: str,
                          result: ValidationResult):
        """检查是否包含必要的免责声明"""
        disclaimer = self.rules.required_disclaimers.get(content_type)
        if disclaimer and disclaimer not in text:
            result.warnings.append(
                f"缺少{content_type}类型的合规声明，建议添加"
            )

    def quick_check(self, text: str) -> bool:
        """快速检查文本是否包含禁用词（不生成详细报告）"""
        return not bool(self._forbidden_regex.search(text))

    def get_compliance_prompt_section(self) -> str:
        """返回注入Prompt的合规约束段落"""
        return self.rules.get_compliance_prompt_section()
