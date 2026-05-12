"""多模态视觉分析工具：调用 Doubao-1.5-vision-pro-32k 提取文字和视觉违规线索"""

import base64
import json
from pathlib import Path

from openai import OpenAI

from src.config import ARK_API_KEY, ARK_BASE_URL, ARK_VISION_MODEL
from src.models import VisionResult, VisualIndicator

VISION_PROMPT = """你是一个广告合规审查专家。请分析这张广告图片，完成以下任务：

1. **文字提取**：提取图片中所有可见的文字内容（包括标题、正文、标签、水印等）
2. **视觉违规线索识别**：识别以下类型的视觉违规：
   - exaggerated_comparison: 夸张的前后对比图
   - fake_stamp: 伪造的认证印章、奖章、证书
   - misleading_chart: 误导性的图表、数据展示
   - medical_imagery: 不当使用医疗相关图像
   - fake_endorsement: 伪造的名人/机构背书

请以 JSON 格式返回结果：
```json
{
  "extracted_text": "图片中的所有文字内容",
  "visual_indicators": [
    {
      "indicator_type": "类型",
      "description": "具体描述",
      "confidence": 0.0-1.0
    }
  ]
}
```

如果没有发现视觉违规线索，visual_indicators 返回空列表。"""


def _encode_image(image_path: str) -> str:
    """将图片编码为 base64"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _get_image_media_type(image_path: str) -> str:
    """根据文件扩展名获取 MIME 类型"""
    suffix = Path(image_path).suffix.lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }
    return mime_map.get(suffix, "image/png")


def vision_analyze(image_path: str) -> VisionResult:
    """
    调用 Doubao-1.5-vision-pro-32k 分析广告图片。

    Args:
        image_path: 广告图片文件路径

    Returns:
        VisionResult: 提取文字 + 视觉违规线索

    Raises:
        Exception: API 调用失败时抛出
    """
    if not Path(image_path).exists():
        raise FileNotFoundError(f"图片文件不存在: {image_path}")

    client = OpenAI(api_key=ARK_API_KEY, base_url=ARK_BASE_URL)

    image_b64 = _encode_image(image_path)
    media_type = _get_image_media_type(image_path)

    response = client.chat.completions.create(
        model=ARK_VISION_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": VISION_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{image_b64}"
                        },
                    },
                ],
            }
        ],
        temperature=0.1,
    )

    # 解析返回
    raw_content = response.choices[0].message.content
    return _parse_vision_response(raw_content)


def _parse_vision_response(raw_content: str) -> VisionResult:
    """解析视觉模型的 JSON 返回"""
    # 尝试从 markdown code block 中提取 JSON
    content = raw_content.strip()
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        # 如果解析失败，把整个返回当作提取文字
        return VisionResult(extracted_text=raw_content, visual_indicators=[])

    indicators = []
    for ind in data.get("visual_indicators", []):
        indicators.append(VisualIndicator(
            indicator_type=ind.get("indicator_type", "unknown"),
            description=ind.get("description", ""),
            confidence=float(ind.get("confidence", 0.0)),
        ))

    return VisionResult(
        extracted_text=data.get("extracted_text", ""),
        visual_indicators=indicators,
    )
