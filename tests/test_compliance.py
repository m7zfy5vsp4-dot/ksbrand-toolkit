"""合规审核模块测试"""

import sys
from pathlib import Path

project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from src.compliance.rules import ComplianceRules
from src.compliance.validator import ComplianceValidator


class TestComplianceRules:
    """合规规则加载测试"""

    def test_load_brand_name(self):
        rules = ComplianceRules()
        assert rules.brand_name == "金山云"

    def test_load_forbidden_words(self):
        rules = ComplianceRules()
        assert len(rules.forbidden_words) > 0
        assert "最好" in rules.forbidden_words
        assert "第一" in rules.forbidden_words

    def test_load_product_names(self):
        rules = ComplianceRules()
        assert "cdn" in rules.product_names
        assert rules.product_names["cdn"] == "金山云CDN"

    def test_get_forbidden_regex(self):
        rules = ComplianceRules()
        regex = rules.get_forbidden_regex()
        assert regex.search("这是最好的产品")

    def test_get_tone_instruction(self):
        rules = ComplianceRules()
        instruction = rules.get_tone_instruction()
        assert "政企文风" in instruction
        assert "严谨" in instruction

    def test_get_compliance_prompt_section(self):
        rules = ComplianceRules()
        section = rules.get_compliance_prompt_section()
        assert "合规约束" in section
        assert "金山云" in section


class TestComplianceValidator:
    """合规校验器测试"""

    def setup_method(self):
        self.validator = ComplianceValidator()

    def test_pass_clean_content(self):
        result = self.validator.validate("金山云持续为政企客户提供稳定可靠的云服务。")
        assert result.passed is True
        assert len(result.errors) == 0

    def test_detect_forbidden_word_best(self):
        result = self.validator.validate("金山云是最好的云服务商")
        assert result.passed is False
        assert any("最好" in err for err in result.errors)

    def test_detect_forbidden_word_first(self):
        result = self.validator.validate("金山云是行业第一的云平台")
        assert result.passed is False
        assert any("第一" in err for err in result.errors)

    def test_detect_multiple_forbidden_words(self):
        result = self.validator.validate("金山云是最好、最强、唯一的云服务商")
        assert result.passed is False
        assert len(result.forbidden_word_hits) >= 2

    def test_detect_absolute_expressions(self):
        result = self.validator.validate("金山云百分之百可靠")
        assert result.passed is False

    def test_product_name_warning(self):
        result = self.validator.validate("金山云的ks3存储很好用")
        assert any("KS3" in w or "ks3" in w.lower() for w in result.warnings)

    def test_quick_check_pass(self):
        assert self.validator.quick_check("金山云提供云服务") is True

    def test_quick_check_fail(self):
        assert self.validator.quick_check("金山云是最好的") is False

    def test_disclaimer_warning_for_marketing(self):
        result = self.validator.validate("金山云CDN节点覆盖全国", content_type="marketing")
        assert len(result.warnings) > 0

    def test_validation_result_has_no_false_positives_on_normal_text(self):
        normal_text = (
            "金山云CDN提供高性能内容分发服务，"
            "节点覆盖全国，支持7×24小时运维保障，"
            "满足政企客户合规要求。"
        )
        result = self.validator.validate(normal_text)
        assert result.passed is True
