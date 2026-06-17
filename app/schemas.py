from pydantic import BaseModel, field_validator
from typing import Optional
from enum import Enum


class Category(str, Enum):
    AUTOMATION = "automation"
    INTEGRATION = "integration"
    REPORT_ANALYTICS = "report/analytics"
    BUG_SUPPORT = "bug/support"
    QUESTION_CONSULTATION = "question/consultation"
    OUT_OF_SCOPE = "out of scope"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class LLMOutput(BaseModel):
    category: Category
    target_department: Optional[str] = None
    priority: Priority
    short_summary: str
    requested_actions: list[str]
    needs_clarification: bool
    estimated_effort: Optional[str] = None
    confidence_score: Optional[float] = None

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence(cls, v):
        if v is not None and not (0.0 <= v <= 1.0):
            raise ValueError("confidence_score must be between 0 and 1")
        return v


class RequestResult(LLMOutput):
    id: str
    channel: str
    timestamp: str
    raw_text: str
    llm_error: Optional[str] = None