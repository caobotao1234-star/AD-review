"""测试人工复核队列"""

import json
import os
import tempfile
import pytest

from src.models import ReviewResult
from src.review_queue import write_to_review_queue, read_review_decisions
import src.config as config


@pytest.fixture
def temp_review_dir(monkeypatch):
    """使用临时目录作为复核队列"""
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setattr(config, "REVIEW_QUEUE_DIR", tmpdir)
        # 也要 patch review_queue 模块里引用的
        import src.review_queue as rq
        monkeypatch.setattr(rq, "REVIEW_QUEUE_DIR", tmpdir)
        yield tmpdir


class TestWriteToReviewQueue:
    def test_write_creates_file(self, temp_review_dir):
        result = ReviewResult(
            case_id="case_test",
            user_id="user_test",
            violation_types=["绝对化用语"],
            confidence_score=0.4,
            recommended_action="限流",
        )
        filepath = write_to_review_queue(result)
        assert os.path.exists(filepath)
        assert "case_test" in filepath

    def test_written_content(self, temp_review_dir):
        result = ReviewResult(
            case_id="c1",
            user_id="u1",
            violation_types=["医疗暗示"],
            confidence_score=0.3,
        )
        filepath = write_to_review_queue(result)
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["case_id"] == "c1"
        assert data["human_decision"] is None
        assert data["violation_types"] == ["医疗暗示"]


class TestReadReviewDecisions:
    def test_no_decisions(self, temp_review_dir):
        # 写入但不填 human_decision
        result = ReviewResult(case_id="c1", user_id="u1")
        write_to_review_queue(result)
        decisions = read_review_decisions()
        assert len(decisions) == 0

    def test_with_decision(self, temp_review_dir):
        result = ReviewResult(case_id="c2", user_id="u2")
        filepath = write_to_review_queue(result)
        # 模拟复核员填写
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["human_decision"] = "通过"
        data["review_notes"] = "误判"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

        decisions = read_review_decisions()
        assert len(decisions) == 1
        assert decisions[0]["human_decision"] == "通过"
        assert decisions[0]["review_notes"] == "误判"
