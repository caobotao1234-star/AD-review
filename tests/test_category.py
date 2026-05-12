"""测试类目规则查询工具"""

import pytest
from src.tools.category import get_category_rules


class TestGetCategoryRules:
    def test_medical_device(self):
        rules = get_category_rules("医疗器械")
        assert rules.category == "医疗器械"
        assert rules.severity_boost is True
        assert "治愈" in rules.prohibited_claims
        assert len(rules.required_disclaimers) > 0

    def test_health_food(self):
        rules = get_category_rules("保健食品")
        assert rules.severity_boost is True
        assert "治疗" in rules.prohibited_claims

    def test_finance(self):
        rules = get_category_rules("金融")
        assert "保本保息" in rules.prohibited_claims
        assert "投资有风险" in rules.required_disclaimers

    def test_education(self):
        rules = get_category_rules("教育培训")
        assert "包过" in rules.prohibited_claims
        assert rules.severity_boost is False

    def test_unknown_category(self):
        rules = get_category_rules("未知类目xyz")
        assert rules.category == "未知类目xyz"
        assert rules.severity_boost is False
        assert rules.prohibited_claims == []

    def test_empty_category(self):
        rules = get_category_rules("")
        assert rules.category == "未知"
        assert rules.severity_boost is False

    def test_none_category(self):
        rules = get_category_rules(None)
        assert rules.severity_boost is False
