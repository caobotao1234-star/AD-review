"""关键词检测工具：匹配文本中的违规关键词"""

import json
from pathlib import Path

from src.config import KEYWORDS_PATH
from src.models import KeywordHit


def _load_keywords() -> list[dict]:
    """加载关键词库"""
    path = Path(KEYWORDS_PATH)
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("keywords", [])


def keyword_match(text: str) -> list[KeywordHit]:
    """
    匹配文本中的违规关键词。

    Args:
        text: 待检测文本

    Returns:
        命中关键词列表，每项包含关键词、违规类型、上下文
    """
    if not text:
        return []

    keywords = _load_keywords()
    hits: list[KeywordHit] = []

    for entry in keywords:
        kw = entry["keyword"]
        pos = text.find(kw)
        if pos != -1:
            # 提取上下文（前后各20字符）
            start = max(0, pos - 20)
            end = min(len(text), pos + len(kw) + 20)
            context = text[start:end]

            hits.append(KeywordHit(
                keyword=kw,
                violation_type=entry["violation_type"],
                context=context,
                position=pos,
            ))

    return hits
