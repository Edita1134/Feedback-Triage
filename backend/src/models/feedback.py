from enum import Enum
from typing import Literal, Optional, List
from pydantic import BaseModel, Field, validator
from datetime import datetime


class FeedbackCategory(str, Enum):
    BUG_REPORT = "Bug Report"
    FEATURE_REQUEST = "Feature Request"
    PRAISE_POSITIVE = "Praise/Positive Feedback"
    GENERAL_INQUIRY = "General Inquiry"


class UrgencyScore(int, Enum):
    NOT_URGENT = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    CRITICAL = 5


class FeedbackRequest(BaseModel):
    text: str = Field(..., max_length=1000, description="The feedback text to analyze")
    category: Optional[str] = Field(None, description="User-selected category (optional)")
    
    @validator('text')
    def validate_text(cls, v):
        if not v.strip():
            raise ValueError("Text cannot be empty")
        return v.strip()
    
    @validator('category')
    def validate_category(cls, v):
        if v and v.strip():
            # Validate that the category is one of the allowed values
            valid_categories = [cat.value for cat in FeedbackCategory]
            if v not in valid_categories:
                raise ValueError(f"Invalid category. Must be one of: {valid_categories}")
        return v


class FeedbackResponse(BaseModel):
    feedback_text: str
    category: FeedbackCategory
    urgency_score: UrgencyScore


class ErrorResponse(BaseModel):
    error: str
    message: str
    status_code: int


class LLMResponse(BaseModel):
    category: FeedbackCategory
    urgency_score: UrgencyScore
    reasoning: str = Field(default="", description="Optional reasoning from the LLM")
    confidence_score: Optional[float] = Field(default=None, description="Confidence score 0-1")


class FeedbackHistoryResponse(BaseModel):
    id: int
    feedback_text: str
    category: FeedbackCategory
    urgency_score: UrgencyScore
    confidence_score: Optional[float]
    processing_time: Optional[float]
    llm_provider: Optional[str]
    created_at: datetime
    user_ip: Optional[str]


class DashboardStats(BaseModel):
    total_feedback: int
    categories: dict
    urgency_distribution: dict
    avg_processing_time: Optional[float]
    recent_feedback: List[FeedbackHistoryResponse]
