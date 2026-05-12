"""测试数据模型"""

import json
import pytest
from src.models import (
    ReviewResult,
    ReviewQueueItem,
    AuditLogEntry,
    CasePair,
    VisionResult,
    VisualIndicator,
)


class TestReviewResult:
    def test_to_dict(self):
        r = ReviewResult(
            case_id="case_01",
            user_id="user_001",
            violation_types=["绝对化用语"],
            reasoning="使用了最字",
            legal_references=["《广告法》第九条"],
            confidence_score=0.85,
            recommended_action="限流",
            image_path="input/case_01.png",
            json_path="input/case_01.json",
        )
        d = r.to_dict()
        assert d["case_id"] == "case_01"
        assert d["violation_types"] == ["绝对化用语"]
        assert d["confidence_score"] == 0.85

    def test_to_json(self):
        r = ReviewResult(case_id="t", user_id="u")
        j = r.to_json()
        parsed = json.loads(j)
        assert parsed["case_id"] == "t"
        assert parsed["recommended_action"] == "通过"

    def test_from_dict(self):
        data = {
            "case_id": "x",
            "user_id": "y",
            "violation_types": ["医疗暗示"],
            "reasoning": "test",
            "legal_references": [],
            "confidence_score": 0.5,
            "recommended_action": "下架",
            "image_path": "a.png",
            "json_path": "a.json",
        }
        r = ReviewResult.from_dict(data)
        assert r.case_id == "x"
        assert r.recommended_action == "下架"

    def test_no_violation_defaults(self):
        r = ReviewResult(case_id="ok", user_id="u")
        assert r.violation_types == []
        assert r.recommended_action == "通过"
        assert r.confidence_score == 0.0


class TestReviewQueueItem:
    def test_from_review_result(self):
        r = ReviewResult(
            case_id="c1",
            user_id="u1",
            violation_types=["价格欺诈"],
            confidence_score=0.4,
            recommended_action="标注",
        )
        item = ReviewQueueItem.from_review_result(r)
        assert item.case_id == "c1"
        assert item.human_decision is None
        assert item.review_notes is None
        assert item.violation_types == ["价格欺诈"]

    def test_serialization_roundtrip(self):
        item = ReviewQueueItem(
            case_id="c2",
            user_id="u2",
            violation_types=["虚构承诺"],
            confidence_score=0.3,
            recommended_action="限流",
            human_decision="通过",
            review_notes="误判",
        )
        j = item.to_json()
        parsed = json.loads(j)
        restored = ReviewQueueItem.from_dict(parsed)
        assert restored.human_decision == "通过"
        assert restored.review_notes == "误判"


class TestAuditLogEntry:
    def test_to_dict(self):
        entry = AuditLogEntry(
            timestamp="2025-01-01T00:00:00",
            case_id="c1",
            step_number=1,
            step_type="thought",
            content="分析图片",
        )
        d = entry.to_dict()
        assert d["step_number"] == 1
        assert d["tool_name"] is None

    def test_with_tool_call(self):
        entry = AuditLogEntry(
            timestamp="2025-01-01T00:00:01",
            case_id="c1",
            step_number=2,
            step_type="action",
            tool_name="keyword_match",
            tool_input={"text": "测试"},
            tool_output="[]",
            content="",
        )
        d = entry.to_dict()
        assert d["tool_name"] == "keyword_match"
        assert d["tool_input"] == {"text": "测试"}
