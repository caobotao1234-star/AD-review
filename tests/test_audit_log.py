"""测试审计日志"""

import json
import os
import tempfile
import pytest

from src.audit_log import AuditLogger
import src.config as config


@pytest.fixture
def temp_logs_dir(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setattr(config, "LOGS_DIR", tmpdir)
        import src.audit_log as al
        monkeypatch.setattr(al, "LOGS_DIR", tmpdir)
        yield tmpdir


class TestAuditLogger:
    def test_log_step(self):
        logger = AuditLogger("case_01")
        logger.log_step(step_type="thought", content="开始分析")
        assert len(logger.entries) == 1
        assert logger.entries[0].step_number == 1
        assert logger.entries[0].step_type == "thought"

    def test_step_counter_increments(self):
        logger = AuditLogger("case_01")
        logger.log_step(step_type="thought", content="a")
        logger.log_step(step_type="action", content="b", tool_name="vision")
        logger.log_step(step_type="observation", content="c")
        assert logger.entries[0].step_number == 1
        assert logger.entries[1].step_number == 2
        assert logger.entries[2].step_number == 3

    def test_save_creates_file(self, temp_logs_dir):
        logger = AuditLogger("case_test")
        logger.log_step(step_type="thought", content="test")
        logger.log_step(step_type="final_judgment", content="通过")
        filepath = logger.save()
        assert os.path.exists(filepath)
        assert "case_test" in filepath

    def test_saved_content(self, temp_logs_dir):
        logger = AuditLogger("c1")
        logger.log_step(step_type="action", tool_name="keyword_match",
                        tool_input={"text": "测试"}, tool_output="[]")
        filepath = logger.save()
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["tool_name"] == "keyword_match"
        assert data[0]["case_id"] == "c1"
