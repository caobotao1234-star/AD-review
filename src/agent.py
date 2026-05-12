"""
广告合规审查 Agent 主控

基于 LangGraph 实现 ReAct 架构，自主决定工具调用顺序。
"""

import json
from dataclasses import asdict
from typing import Annotated

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from src.config import (
    ARK_API_KEY,
    ARK_BASE_URL,
    ARK_REASONING_MODEL,
)
from src.models import CasePair, ReviewResult
from src.tools.vision import vision_analyze
from src.tools.keywords import keyword_match
from src.tools.rag import rag_search
from src.tools.consistency import check_consistency
from src.tools.category import get_category_rules

# ============================================================
# LangGraph 工具定义（用 @tool 装饰器包装）
# ============================================================


@tool
def tool_vision_analyze(image_path: str) -> str:
    """分析广告图片，提取所有文字内容并识别视觉违规线索（如夸张对比图、伪造印章、误导性图表）。"""
    try:
        result = vision_analyze(image_path)
        return json.dumps({
            "extracted_text": result.extracted_text,
            "visual_indicators": [asdict(v) for v in result.visual_indicators],
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@tool
def tool_keyword_match(text: str) -> str:
    """检测文本中的违规关键词。输入为从图片中提取的文字或商品描述文本。返回命中的关键词及其违规类型。"""
    hits = keyword_match(text)
    return json.dumps([asdict(h) for h in hits], ensure_ascii=False)


@tool
def tool_rag_search(query: str) -> str:
    """检索相关法律条款。输入为违规描述或关键词，返回最相关的法条（含法规名、条款号、原文）。"""
    articles = rag_search(query, top_k=3)
    return json.dumps([asdict(a) for a in articles], ensure_ascii=False)


@tool
def tool_check_consistency(extracted_text: str, product_json_str: str) -> str:
    """对比广告图片文字与商品页数据，找出价格、功效、规格、产地等方面的矛盾。product_json_str 为 JSON 字符串。"""
    try:
        product_json = json.loads(product_json_str)
    except json.JSONDecodeError:
        return json.dumps({"error": "product_json_str 不是有效的 JSON"}, ensure_ascii=False)
    contradictions = check_consistency(extracted_text, product_json)
    return json.dumps([asdict(c) for c in contradictions], ensure_ascii=False)


@tool
def tool_get_category_rules(category: str) -> str:
    """查询商品类目的加严审查规则。输入为类目名称（如"医疗器械"、"保健食品"、"金融"、"教育培训"）。"""
    rules = get_category_rules(category)
    return json.dumps(asdict(rules), ensure_ascii=False)


# ============================================================
# Agent 系统提示词
# ============================================================

SYSTEM_PROMPT = """你是一个专业的广告合规审查 Agent。你的任务是审查抖音平台上的广告是否存在虚假宣传。

## 你的工作流程：
1. 首先使用 tool_vision_analyze 分析广告图片，提取文字和视觉违规线索
2. 使用 tool_keyword_match 检测提取文字中的违规关键词
3. 使用 tool_get_category_rules 查询该商品类目的加严规则
4. 使用 tool_check_consistency 对比图片文字与商品页数据的一致性
5. 如果发现疑似违规，使用 tool_rag_search 检索相关法条作为依据

## 判断原则：
- 关键词命中是强信号，但不能仅凭关键词判定违规，需要结合上下文
- 图文矛盾是虚假宣传的重要证据
- 敏感类目（医疗、金融等）要从严判断
- 所有违规判定必须引用具体法条

## 违规类型：
- 绝对化用语：使用"最""第一""国家级"等绝对化表述
- 虚构承诺：承诺无法兑现的效果
- 虚假对比：与竞品进行无依据的对比
- 医疗暗示：非医疗产品暗示治疗效果
- 价格欺诈：虚构原价、虚假折扣
- 资质伪造：伪造认证、奖项、推荐

## 处理分级：
- 下架：严重违规（虚假医疗声明、伪造国家机关背书等）
- 限流：中度违规（绝对化用语、夸大宣传等）
- 标注：轻度违规（表述不够严谨但未构成实质误导）
- 通过：未发现违规

## 输出要求：
完成分析后，请输出 JSON 格式的审查结论：
```json
{
  "violation_types": ["违规类型列表"],
  "reasoning": "详细推理过程",
  "legal_references": ["《法规名》第X条第Y项"],
  "recommended_action": "下架/限流/标注/通过"
}
```
"""


# ============================================================
# Agent 构建和执行
# ============================================================

TOOLS = [
    tool_vision_analyze,
    tool_keyword_match,
    tool_rag_search,
    tool_check_consistency,
    tool_get_category_rules,
]


def _build_agent():
    """构建 LangGraph ReAct Agent"""
    llm = ChatOpenAI(
        model=ARK_REASONING_MODEL,
        api_key=ARK_API_KEY,
        base_url=ARK_BASE_URL,
        temperature=0.1,
    )

    agent = create_react_agent(
        model=llm,
        tools=TOOLS,
        prompt=SYSTEM_PROMPT,
    )
    return agent


def review_case(case: CasePair) -> tuple[dict, list[dict]]:
    """
    审查单个 Case_Pair。

    Args:
        case: 待审查案例

    Returns:
        (result_dict, steps): 审查结论字典 + 推理步骤列表（用于审计日志）
    """
    agent = _build_agent()

    # 构建输入消息
    user_message = f"""请审查以下广告案例：

案例 ID: {case.case_id}
用户 ID: {case.product_data.get('user_id', 'unknown')}
图片路径: {case.image_path}
商品类目: {case.product_data.get('category', '未知')}
商品数据: {json.dumps(case.product_data, ensure_ascii=False)}

请按照工作流程逐步分析，最后给出审查结论。"""

    # 执行 Agent
    steps = []
    result_dict = {
        "violation_types": [],
        "reasoning": "",
        "legal_references": [],
        "recommended_action": "通过",
    }

    try:
        response = agent.invoke(
            {"messages": [HumanMessage(content=user_message)]}
        )

        # 收集推理步骤
        for msg in response.get("messages", []):
            step_info = {
                "role": getattr(msg, "type", "unknown"),
                "content": getattr(msg, "content", ""),
            }
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                step_info["tool_calls"] = [
                    {"name": tc["name"], "args": tc["args"]}
                    for tc in msg.tool_calls
                ]
            steps.append(step_info)

        # 解析最终结论（从最后一条 AI 消息中提取 JSON）
        final_content = ""
        for msg in reversed(response.get("messages", [])):
            if getattr(msg, "type", "") == "ai" and getattr(msg, "content", ""):
                final_content = msg.content
                break

        if final_content:
            result_dict = _parse_final_judgment(final_content, result_dict)

    except Exception as e:
        result_dict["reasoning"] = f"Agent 执行异常: {str(e)}"
        steps.append({"role": "error", "content": str(e)})

    return result_dict, steps


def _parse_final_judgment(content: str, default: dict) -> dict:
    """从 Agent 最终输出中解析 JSON 结论"""
    text = content.strip()

    # 尝试提取 JSON block
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        parts = text.split("```")
        for part in parts[1::2]:  # 奇数索引是 code block 内容
            part = part.strip()
            if part.startswith("{"):
                text = part
                break

    try:
        parsed = json.loads(text)
        return {
            "violation_types": parsed.get("violation_types", []),
            "reasoning": parsed.get("reasoning", ""),
            "legal_references": parsed.get("legal_references", []),
            "recommended_action": parsed.get("recommended_action", "通过"),
        }
    except json.JSONDecodeError:
        # 如果无法解析 JSON，把整个内容作为 reasoning
        default["reasoning"] = content
        return default
