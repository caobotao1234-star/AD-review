"""置信度评估：通过两次独立推理 + 一致性校验得出置信度"""

import json

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from src.config import ARK_API_KEY, ARK_BASE_URL, ARK_REASONING_MODEL, CONFIDENCE_THRESHOLD


JUDGE_PROMPT_A = """你是一个严格的广告合规审查员。基于以下证据，判断该广告是否违规。
请直接给出结论，不要犹豫。

## 证据：
{evidence}

请以 JSON 格式输出：
```json
{{
  "is_violation": true/false,
  "violation_types": ["违规类型"],
  "recommended_action": "下架/限流/标注/通过",
  "reasoning": "简要理由"
}}
```"""

JUDGE_PROMPT_B = """你是一个广告合规审查的复核员。请从消费者保护的角度，独立判断以下广告是否存在虚假宣传。
注意：宁可误判也不要放过真正的违规。

## 证据：
{evidence}

请以 JSON 格式输出：
```json
{{
  "is_violation": true/false,
  "violation_types": ["违规类型"],
  "recommended_action": "下架/限流/标注/通过",
  "reasoning": "简要理由"
}}
```"""


def evaluate_confidence(evidence: str) -> tuple[float, dict, dict]:
    """
    对同一证据做两次独立推理，比较一致性得出置信度。

    Args:
        evidence: 收集到的所有证据文本

    Returns:
        (confidence_score, judgment_a, judgment_b)
    """
    llm = ChatOpenAI(
        model=ARK_REASONING_MODEL,
        api_key=ARK_API_KEY,
        base_url=ARK_BASE_URL,
        temperature=0.3,
    )

    # 第一次推理
    resp_a = llm.invoke([HumanMessage(content=JUDGE_PROMPT_A.format(evidence=evidence))])
    judgment_a = _parse_judgment(resp_a.content)

    # 第二次推理（不同 prompt 视角）
    resp_b = llm.invoke([HumanMessage(content=JUDGE_PROMPT_B.format(evidence=evidence))])
    judgment_b = _parse_judgment(resp_b.content)

    # 计算一致性
    score = _calculate_consistency(judgment_a, judgment_b)

    return score, judgment_a, judgment_b


def _parse_judgment(content: str) -> dict:
    """解析判断结果 JSON"""
    text = content.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {
            "is_violation": False,
            "violation_types": [],
            "recommended_action": "通过",
            "reasoning": content,
        }


def _calculate_consistency(a: dict, b: dict) -> float:
    """
    计算两次判断的一致性分数。

    一致性维度：
    1. 是否违规的结论一致 (权重 0.5)
    2. 违规类型重叠度 (权重 0.3)
    3. 处理建议一致 (权重 0.2)
    """
    score = 0.0

    # 1. 违规结论一致性
    if a.get("is_violation") == b.get("is_violation"):
        score += 0.5

    # 2. 违规类型重叠度
    types_a = set(a.get("violation_types", []))
    types_b = set(b.get("violation_types", []))
    if types_a or types_b:
        union = types_a | types_b
        intersection = types_a & types_b
        overlap = len(intersection) / len(union) if union else 1.0
        score += 0.3 * overlap
    else:
        # 都没有违规类型（都判定通过），完全一致
        score += 0.3

    # 3. 处理建议一致性
    if a.get("recommended_action") == b.get("recommended_action"):
        score += 0.2

    return round(score, 2)


def needs_human_review(confidence_score: float) -> bool:
    """判断是否需要人工复核"""
    return confidence_score < CONFIDENCE_THRESHOLD
