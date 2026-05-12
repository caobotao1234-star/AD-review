"""类目规则查询工具：根据商品类目返回加严审查规则"""

import json
import logging
from pathlib import Path

from src.config import CATEGORY_RULES_PATH
from src.models import CategoryRuleSet

logger = logging.getLogger(__name__)


def _load_category_rules() -> dict:
    """加载类目规则配置"""
    path = Path(CATEGORY_RULES_PATH)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_category_rules(category: str) -> CategoryRuleSet:
    """
    根据商品类目返回加严规则。

    Args:
        category: 商品类目名称

    Returns:
        该类目的审查规则集。未知类目返回通用规则。
    """
    rules = _load_category_rules()

    if category and category in rules:
        rule_data = rules[category]
        return CategoryRuleSet(
            category=category,
            prohibited_claims=rule_data.get("prohibited_claims", []),
            required_disclaimers=rule_data.get("required_disclaimers", []),
            extra_keywords=rule_data.get("extra_keywords", []),
            severity_boost=rule_data.get("severity_boost", False),
        )

    # 未知类目，使用默认规则
    if category:
        logger.warning(f"未知商品类目: {category}，使用通用规则")

    default = rules.get("_default", {})
    return CategoryRuleSet(
        category=category or "未知",
        prohibited_claims=default.get("prohibited_claims", []),
        required_disclaimers=default.get("required_disclaimers", []),
        extra_keywords=default.get("extra_keywords", []),
        severity_boost=default.get("severity_boost", False),
    )
