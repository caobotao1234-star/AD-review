"""人工复核队列：低置信度案例写入和管理"""

import json
import os
from pathlib import Path

from src.config import REVIEW_QUEUE_DIR
from src.models import ReviewResult, ReviewQueueItem


def ensure_review_dir():
    """确保复核队列目录存在"""
    Path(REVIEW_QUEUE_DIR).mkdir(parents=True, exist_ok=True)


def write_to_review_queue(result: ReviewResult) -> str:
    """
    将低置信度案例写入复核队列。

    Args:
        result: 审查结果

    Returns:
        写入的文件路径
    """
    ensure_review_dir()

    item = ReviewQueueItem.from_review_result(result)
    filename = f"{item.case_id}_review.json"
    filepath = os.path.join(REVIEW_QUEUE_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(item.to_json())

    return filepath


def read_review_decisions() -> list[dict]:
    """
    读取复核队列中已填写 human_decision 的案例。

    Returns:
        已复核的案例列表
    """
    review_path = Path(REVIEW_QUEUE_DIR)
    if not review_path.exists():
        return []

    reviewed = []
    for f in review_path.glob("*_review.json"):
        with open(f, "r", encoding="utf-8") as jf:
            data = json.load(jf)
        if data.get("human_decision") is not None:
            reviewed.append(data)

    return reviewed
