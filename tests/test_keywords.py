"""测试关键词检测工具"""

import pytest
from src.tools.keywords import keyword_match


class TestKeywordMatch:
    def test_single_hit(self):
        hits = keyword_match("这款产品全网最低价，赶紧抢购")
        assert len(hits) >= 1
        kws = [h.keyword for h in hits]
        assert "全网最低价" in kws

    def test_multiple_hits(self):
        text = "根治失眠，全网最低价，央视推荐"
        hits = keyword_match(text)
        kws = [h.keyword for h in hits]
        assert "根治" in kws
        assert "全网最低价" in kws
        assert "央视推荐" in kws

    def test_no_hit(self):
        hits = keyword_match("这是一款普通的日用品，质量不错")
        assert len(hits) == 0

    def test_empty_text(self):
        hits = keyword_match("")
        assert len(hits) == 0

    def test_violation_type_mapping(self):
        hits = keyword_match("根治百病")
        assert any(h.violation_type == "医疗暗示" for h in hits)

    def test_context_extraction(self):
        text = "我们的产品可以根治各种疾病"
        hits = keyword_match(text)
        root_hit = [h for h in hits if h.keyword == "根治"][0]
        assert "根治" in root_hit.context
        assert root_hit.position > 0

    def test_position_correct(self):
        text = "abc根治def"
        hits = keyword_match(text)
        assert hits[0].position == 3

    def test_absolute_terms(self):
        """绝对化用语检测"""
        texts_and_expected = [
            ("史上最强产品", "史上最强"),
            ("第一品牌值得信赖", "第一品牌"),
            ("国家级认证产品", "国家级"),
        ]
        for text, expected_kw in texts_and_expected:
            hits = keyword_match(text)
            kws = [h.keyword for h in hits]
            assert expected_kw in kws, f"未检测到 '{expected_kw}' in '{text}'"

    def test_fake_certification(self):
        """伪造资质检测"""
        text = "央视推荐品牌，国务院认证，驰名商标"
        hits = keyword_match(text)
        assert len(hits) >= 3
        assert all(h.violation_type == "资质伪造" for h in hits)
