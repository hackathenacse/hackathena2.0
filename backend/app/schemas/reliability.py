from typing import List
from pydantic import BaseModel, Field


class ReliabilityResult(BaseModel):
    """
    Reliability Gate assessment determining whether available media and model
    evidence is of sufficient quality to support media authenticity evaluation.
    """
    level: str = Field(
        ...,
        description="Reliability level: 'OK' if media quality and evidence are sufficient, 'LOW' if degraded or compromised."
    )
    reasons: List[str] = Field(
        default_factory=list,
        description="List of human-readable diagnostic reasons explaining any reliability degradation."
    )
