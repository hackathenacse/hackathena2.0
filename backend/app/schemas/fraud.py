from typing import List, Optional
from pydantic import BaseModel, Field


class FraudEvidenceItem(BaseModel):
    phrase: str = Field(..., description="The matched phrase or keyword from transcript")
    start_s: float = Field(..., description="Start timestamp of the segment in seconds")
    end_s: float = Field(..., description="End timestamp of the segment in seconds")
    reason: Optional[str] = Field(None, description="Contextual reason this phrase was classified as evidence")


class FraudCategoryEvidence(BaseModel):
    category: str = Field(..., description="Fraud category name (e.g. AUTHORITY, URGENCY)")
    severity: str = Field(..., description="Severity level for this category: HIGH, MEDIUM, LOW")
    evidence: List[FraudEvidenceItem] = Field(default_factory=list, description="Extracted evidence phrases")


class FraudRequestedAction(BaseModel):
    action: str = Field(..., description="Specific action requested (e.g. SEND_MONEY, SHARE_OTP)")
    phrase: str = Field(..., description="The exact sentence or phrase demanding the action")
    start_s: float = Field(..., description="Start timestamp of the request")
    end_s: float = Field(..., description="End timestamp of the request")


class FraudResult(BaseModel):
    level: str = Field(..., description="Overall fraud intent risk: HIGH, MEDIUM, LOW, NOT_ASSESSABLE")
    categories: List[FraudCategoryEvidence] = Field(default_factory=list, description="Detected fraud categories")
    requested_actions: List[FraudRequestedAction] = Field(default_factory=list, description="Directed actions requested from the user")
    news_context_downgrade: bool = Field(default=False, description="True if educational or reported-speech context downgraded the score")

