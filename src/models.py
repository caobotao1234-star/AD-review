"""数据模型定义"""

from dataclasses import dataclass, field, asdict
from typing import Optional
import json


@dataclass
class CasePair:
    """审查案例输入"""
    case_id: str
    image_path: str
    json_path: str
    product_data: dict = field(default_factory=dict)


@dataclass
class VisualIndicator:
    """视觉违规线索"""
    indicator_type: str  # exaggerated_comparison, fake_stamp, misleading_chart
    description: str
    confidence: float = 0.0


@dataclass
class VisionResult:
    """视觉分析结果"""
    extracted_text: str = ""
    visual_indicators: list[VisualIndicator] = field(default_factory=list)


@dataclass
class KeywordHit:
    """关键词命中"""
    keyword: str
    violation_type: str
    context: str = ""
    position: int = 0


@dataclass
class LawArticle:
    """法条"""
    law_name: str
    chapter: str
    article_number: str
    content: str
    relevance_score: float = 0.0


@dataclass
class Contradiction:
    """图文矛盾点"""
    image_text_segment: str
    json_field: str
    json_value: str
    description: str


@dataclass
class CategoryRuleSet:
    """类目规则集"""
    category: str
    prohibited_claims: list[str] = field(default_factory=list)
    required_disclaimers: list[str] = field(default_factory=list)
    extra_keywords: list[str] = field(default_factory=list)
    severity_boost: bool = False


@dataclass
class ReviewResult:
    """审查结果"""
    case_id: str
    user_id: str
    violation_types: list[str] = field(default_factory=list)
    reasoning: str = ""
    legal_references: list[str] = field(default_factory=list)
    confidence_score: float = 0.0
    recommended_action: str = "通过"
    image_path: str = ""
    json_path: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> "ReviewResult":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ReviewQueueItem:
    """人工复核队列项"""
    case_id: str
    user_id: str
    violation_types: list[str] = field(default_factory=list)
    reasoning: str = ""
    legal_references: list[str] = field(default_factory=list)
    confidence_score: float = 0.0
    recommended_action: str = ""
    image_path: str = ""
    json_path: str = ""
    human_decision: Optional[str] = None
    review_notes: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> "ReviewQueueItem":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @classmethod
    def from_review_result(cls, result: ReviewResult) -> "ReviewQueueItem":
        return cls(
            case_id=result.case_id,
            user_id=result.user_id,
            violation_types=result.violation_types,
            reasoning=result.reasoning,
            legal_references=result.legal_references,
            confidence_score=result.confidence_score,
            recommended_action=result.recommended_action,
            image_path=result.image_path,
            json_path=result.json_path,
        )


@dataclass
class AuditLogEntry:
    """审计日志条目"""
    timestamp: str
    case_id: str
    step_number: int
    step_type: str  # thought / action / observation / final_judgment
    tool_name: Optional[str] = None
    tool_input: Optional[dict] = None
    tool_output: Optional[str] = None
    content: str = ""

    def to_dict(self) -> dict:
        return asdict(self)
