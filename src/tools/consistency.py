"""图文一致性校验工具：对比图片提取文字与商品 JSON 数据"""

from openai import OpenAI
import json

from src.config import ARK_API_KEY, ARK_BASE_URL, ARK_REASONING_MODEL
from src.models import Contradiction

# 需要对比的关键字段
CHECK_FIELDS = ["price", "original_price", "efficacy_claims", "specifications", "origin", "title"]

CONSISTENCY_PROMPT = """你是一个广告合规审查专家。请对比以下广告图片中提取的文字和商品页结构化数据，找出矛盾之处。

## 图片提取文字：
{extracted_text}

## 商品页数据（JSON）：
{product_json}

请检查以下方面的矛盾：
1. 价格不一致（图片标价与 JSON 中 price/original_price 不符）
2. 功效声明不一致（图片宣称的功效与 JSON 中 efficacy_claims 不符）
3. 规格不一致（图片描述的规格与 JSON 中 specifications 不符）
4. 产地不一致（图片标注的产地与 JSON 中 origin 不符）
5. 标题/名称不一致

请以 JSON 格式返回矛盾列表：
```json
{{
  "contradictions": [
    {{
      "image_text_segment": "图片中的相关文案",
      "json_field": "矛盾的JSON字段名",
      "json_value": "JSON中该字段的值",
      "description": "矛盾描述"
    }}
  ]
}}
```

如果没有发现矛盾，返回空列表。只报告确实存在的矛盾，不要猜测。"""


def check_consistency(extracted_text: str, product_json: dict) -> list[Contradiction]:
    """
    对比图片提取文字与商品 JSON 数据，找出矛盾。

    Args:
        extracted_text: 从图片中提取的文字
        product_json: 商品页结构化数据

    Returns:
        矛盾点列表
    """
    if not extracted_text or not product_json:
        return []

    client = OpenAI(api_key=ARK_API_KEY, base_url=ARK_BASE_URL)

    # 只传入需要对比的字段
    relevant_data = {k: v for k, v in product_json.items() if k in CHECK_FIELDS}

    prompt = CONSISTENCY_PROMPT.format(
        extracted_text=extracted_text,
        product_json=json.dumps(relevant_data, ensure_ascii=False, indent=2),
    )

    response = client.chat.completions.create(
        model=ARK_REASONING_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )

    raw_content = response.choices[0].message.content
    return _parse_consistency_response(raw_content)


def _parse_consistency_response(raw_content: str) -> list[Contradiction]:
    """解析一致性检查的 JSON 返回"""
    content = raw_content.strip()
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return []

    contradictions = []
    for item in data.get("contradictions", []):
        contradictions.append(Contradiction(
            image_text_segment=item.get("image_text_segment", ""),
            json_field=item.get("json_field", ""),
            json_value=str(item.get("json_value", "")),
            description=item.get("description", ""),
        ))

    return contradictions
