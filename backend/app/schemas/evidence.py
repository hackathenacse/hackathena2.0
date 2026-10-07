from typing import List, Optional
from pydantic import BaseModel, Field

from app.schemas.reliability import ReliabilityResult


class ModelEvidenceItem(BaseModel):
    """
    Representation of an individual model score.
    Explicitly annotated to prevent misinterpreting raw outputs as calibrated probabilities.
    """
    name: str = Field(..., description="Unique model name and version")
    score: Optional[float] = Field(None, description="Raw model score (not a probability)")
    label: str = Field(
        "model score (not a probability)",
        description="Explicit provenance annotation for consumer interfaces"
    )


class LocalizedRegion(BaseModel):
    """Contiguous temporal region of persistent high forensic manipulation evidence."""
    start_s: float = Field(..., description="Start timestamp of high-evidence region in seconds")
    end_s: float = Field(..., description="End timestamp of high-evidence region in seconds")
    level: str = Field("HIGH", description="Regional evidence level ('HIGH')")
    mean_score: Optional[float] = Field(None, description="Average manipulation score across region")


class ModalityStatistics(BaseModel):
    """Robust statistical metrics across frames/windows for calibrated decisions."""
    valid_frame_count: int = Field(0, description="Count of valid face/audio observations evaluated")
    mean_score: Optional[float] = Field(None, description="Arithmetic mean score across evaluated items")
    median_score: Optional[float] = Field(None, description="Median score across evaluated items")
    max_score: Optional[float] = Field(None, description="Maximum observed score (diagnostic only)")
    high_ratio: Optional[float] = Field(None, description="Ratio of frames exceeding high threshold")
    consecutive_high_count: int = Field(0, description="Maximum count of consecutive high windows")
    high_window_ratio: Optional[float] = Field(None, description="Ratio of temporal windows classified as HIGH")
    persistent_high_window_ratio: Optional[float] = Field(None, description="Ratio of persistent consecutive high windows")
    localized_high_regions: List[LocalizedRegion] = Field(default_factory=list, description="Persistent high-evidence temporal regions")


class EvidenceModalityResult(BaseModel):
    """Normalized evidence for an individual sensory modality (visual or audio)."""
    level: str = Field(
        "N/A",
        description="Derived modality level: 'LOW' | 'MEDIUM' | 'HIGH' | 'N/A'"
    )
    models: List[ModelEvidenceItem] = Field(
        default_factory=list,
        description="List of model outputs contributing to this modality"
    )
    statistics: Optional[ModalityStatistics] = Field(
        None,
        description="Robust statistical metrics preventing single-observation false positives"
    )


class ProvenanceResult(BaseModel):
    """
    C2PA / Content Credentials inspection findings.
    Distinguishes presence, signature validity, and signer trustworthiness.
    """
    state: str = Field(
        ...,
        description="Provenance state: 'NONE_FOUND' | 'FOUND' | 'UNAVAILABLE' | 'ERROR'"
    )
    valid: Optional[bool] = Field(
        None,
        description="True if cryptographic manifest signature is verified and intact, False if invalid/tampered"
    )
    trusted: Optional[bool] = Field(
        None,
        description="True if signing certificate is on the configured trusted root list"
    )
    signer: Optional[str] = Field(
        None,
        description="Common Name or Organization of the signing identity"
    )
    ai_generated: Optional[bool] = Field(
        None,
        description="True if credentials explicitly declare AI or algorithmic generation"
    )
    note: str = Field(
        ...,
        description="Human-readable explanation of provenance state and implications"
    )


class EvidenceMetadata(BaseModel):
    """Normalized media quality and container metrics."""
    media_type: str = Field("VIDEO", description="Input media category: 'VIDEO' | 'AUDIO'")
    width: Optional[int] = Field(None, description="Video width in pixels (for VIDEO)")
    height: Optional[int] = Field(None, description="Video height in pixels (for VIDEO)")
    duration_s: float = Field(..., description="Total duration in seconds")
    fps: Optional[float] = Field(None, description="Frame rate (for VIDEO)")
    frames_sampled: Optional[int] = Field(None, description="Number of sampled frames (for VIDEO)")
    audio_available: bool = Field(True, description="True if audio stream exists")
    exact_verified_match: Optional[bool] = Field(None, description="True if identical SHA-256 binary was previously human-verified")
    verified_ground_truth: Optional[dict] = Field(None, description="Stored human ground-truth verdict if previously verified")
    near_duplicate_match: Optional[dict] = Field(None, description="Perceptual / feature similarity matching data for near-duplicates")
    cached_reanalysis: Optional[bool] = Field(None, description="True if result was returned from fast re-analysis cache")


class EvidenceMatrix(BaseModel):
    """
    Unified evidence synthesis matrix combining sensory evidence, provenance,
    media quality, and reliability status.
    """
    visual: EvidenceModalityResult = Field(default_factory=EvidenceModalityResult)
    audio: EvidenceModalityResult = Field(default_factory=EvidenceModalityResult)
    provenance: ProvenanceResult
    metadata: EvidenceMetadata
    reliability: ReliabilityResult


class MediaAssessment(BaseModel):
    """
    Stage 2 & Stage 3 Media Assessment verdict and recommended action.
    Explicitly avoids unsupported 'AUTHENTIC' claims.
    """
    media: str = Field(
        ...,
        description="Media verdict: 'LIKELY_MANIPULATED' | 'SUSPICIOUS' | 'NO_STRONG_EVIDENCE' | 'UNCERTAIN'"
    )
    fraud: Optional[str] = Field(
        None,
        description="Fraud intent risk: 'LOW' | 'MEDIUM' | 'HIGH' | 'NOT_ASSESSABLE'"
    )
    action: Optional[str] = Field(
        None,
        description="Recommended action: 'STOP_AND_VERIFY' | 'VERIFY' | 'CAUTION' | 'NO_ACTION_FLAGGED'"
    )
