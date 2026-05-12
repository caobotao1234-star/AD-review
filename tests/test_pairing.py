"""测试 Case_Pair 配对逻辑"""

import json
import os
import tempfile
import pytest

from src.pairing import find_case_pairs, validate_batch


@pytest.fixture
def temp_input_dir():
    """创建临时输入目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


def _create_file(dir_path, filename, content=None):
    """辅助：创建文件"""
    filepath = os.path.join(dir_path, filename)
    if filename.endswith(".json"):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(content or {"user_id": "test"}, f)
    else:
        with open(filepath, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n")  # PNG header
    return filepath


class TestFindCasePairs:
    def test_valid_pair(self, temp_input_dir):
        _create_file(temp_input_dir, "case_01.png")
        _create_file(temp_input_dir, "case_01.json")
        pairs, errors = find_case_pairs(temp_input_dir)
        assert len(pairs) == 1
        assert pairs[0].case_id == "case_01"
        assert not errors

    def test_multiple_pairs(self, temp_input_dir):
        for i in range(3):
            _create_file(temp_input_dir, f"ad_{i}.jpg")
            _create_file(temp_input_dir, f"ad_{i}.json")
        pairs, errors = find_case_pairs(temp_input_dir)
        assert len(pairs) == 3
        assert not errors

    def test_missing_json(self, temp_input_dir):
        _create_file(temp_input_dir, "case_01.png")
        pairs, errors = find_case_pairs(temp_input_dir)
        assert len(pairs) == 0
        assert len(errors) == 1
        assert "缺少 JSON" in errors[0]

    def test_missing_image(self, temp_input_dir):
        _create_file(temp_input_dir, "case_01.json")
        pairs, errors = find_case_pairs(temp_input_dir)
        assert len(pairs) == 0
        assert len(errors) == 1
        assert "缺少图片" in errors[0]

    def test_invalid_json(self, temp_input_dir):
        _create_file(temp_input_dir, "case_01.png")
        # 写入无效 JSON
        filepath = os.path.join(temp_input_dir, "case_01.json")
        with open(filepath, "w") as f:
            f.write("not valid json{{{")
        pairs, errors = find_case_pairs(temp_input_dir)
        assert len(pairs) == 0
        assert len(errors) == 1
        assert "JSON 解析失败" in errors[0]

    def test_empty_dir(self, temp_input_dir):
        pairs, errors = find_case_pairs(temp_input_dir)
        assert len(pairs) == 0
        assert not errors

    def test_nonexistent_dir(self):
        pairs, errors = find_case_pairs("/nonexistent/path")
        assert len(pairs) == 0
        assert len(errors) == 1
        assert "不存在" in errors[0]

    def test_mixed_extensions(self, temp_input_dir):
        """jpg 和 jpeg 都应该被识别"""
        _create_file(temp_input_dir, "a.jpg")
        _create_file(temp_input_dir, "a.json")
        _create_file(temp_input_dir, "b.jpeg")
        _create_file(temp_input_dir, "b.json")
        pairs, errors = find_case_pairs(temp_input_dir)
        assert len(pairs) == 2
        assert not errors


class TestValidateBatch:
    def test_within_limit(self, temp_input_dir):
        for i in range(10):
            _create_file(temp_input_dir, f"c_{i}.png")
            _create_file(temp_input_dir, f"c_{i}.json")
        pairs, errors = find_case_pairs(temp_input_dir)
        pairs, errors = validate_batch(pairs, errors)
        assert len(pairs) == 10

    def test_exceeds_limit(self, temp_input_dir):
        for i in range(11):
            _create_file(temp_input_dir, f"c_{i}.png")
            _create_file(temp_input_dir, f"c_{i}.json")
        pairs, errors = find_case_pairs(temp_input_dir)
        pairs, errors = validate_batch(pairs, errors)
        assert len(pairs) == 0
        assert any("超限" in e for e in errors)
