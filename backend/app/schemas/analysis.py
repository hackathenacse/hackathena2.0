from typing import List, Optional
from pydantic import BaseModel, Field

from app.schemas.evidence import (
    EvidenceMatrix,
    EvidenceMetadata,
    EvidenceModalityResult,
    MediaAssessment,
    ModelEvidenceItem,
    ProvenanceResult,
)
from app.schemas.fraud import FraudResult
from app.schemas.reliability import ReliabilityResult
from app.schemas.timeline import TimelineEvent


class VideoInfo(BaseModel):
    """Metadata extracted from the uploaded video."""
    filename: str = Field(..., description="Original filename of the uploaded video")
    sha256: str = Field(..., description="SHA-256 hash of the video file")
    duration_s: float = Field(..., description="Total duration in seconds")
    fps: float = Field(..., description="Frame rate (frames per second)")
    width: int = Field(..., description="Video width in pixels")
    height: int = Field(..., description="Video height in pixels")
    frames_sampled: int = Field(..., description="Number of sampled frames extracted for analysis")
    audio_available: bool = Field(..., description="True if an audio stream exists in the video")


class VisualFrameResult(BaseModel):
    """Result for an individual sampled video frame."""
    timestamp_s: float = Field(..., description="Timestamp of the frame in seconds")
    face_detected: Optional[bool] = Field(None, description="Whether a face was detected in this frame")
    real_score: Optional[float] = Field(None, description="Confidence score for real/authentic face (0.0 to 1.0)")
    fake_score: Optional[float] = Field(None, description="Confidence score for synthetic/deepfake face (0.0 to 1.0)")
    raw_real_score: Optional[float] = Field(None, description="Raw base model score for real class (EfficientNet)")
    raw_fake_score: Optional[float] = Field(None, description="Raw base model score for fake class (EfficientNet)")
    adapted_fake_score: Optional[float] = Field(None, description="Adapted score from Authentica adapter layer")
    face_occupancy_pct: Optional[float] = Field(None, description="Percentage of crop area occupied by face bounding box")
    context_margin_pct: Optional[float] = Field(None, description="Context margin percentage around face box")
    face_confidence: Optional[float] = Field(None, description="Detection confidence score of the face detector (0.0 to 1.0)")
    bounding_box: Optional[List[int]] = Field(None, description="[x, y, w, h] face bounding box in pixel coordinates")
    face_pixel_size: Optional[int] = Field(None, description="Face crop size in pixels (min(w, h))")
    blur_score: Optional[float] = Field(None, description="Variance of Laplacian sharpness metric")
    luma: Optional[float] = Field(None, description="Mean luminance/brightness of face crop (0-255)")
    noise_estimate: Optional[float] = Field(None, description="Estimated high-frequency noise level")


class VisualResult(BaseModel):
    """Aggregated visual / facial deepfake detection results (Member 2)."""
    available: bool = Field(False, description="Whether the visual detector is active and executed")
    model: Optional[str] = Field(None, description="Name and version of the visual detector model")
    adapter_version: Optional[str] = Field(None, description="Active Authentica adaptation layer version")
    status: str = Field("unavailable", description="Status of the visual detector (e.g., unavailable, completed, error)")
    frames_analyzed: int = Field(0, description="Total number of frames analyzed")
    faces_found: int = Field(0, description="Total number of frames where faces were detected")
    face_detection_rate: Optional[float] = Field(None, description="Proportion of sampled frames containing faces")
    average_face_occupancy_pct: Optional[float] = Field(None, description="Average percentage of crop occupied by face")
    results: List[VisualFrameResult] = Field(default_factory=list, description="Per-frame detection results")


class AudioWindowResult(BaseModel):
    """Result for a time window in the audio stream."""
    start_s: float = Field(..., description="Start timestamp in seconds")
    end_s: float = Field(..., description="End timestamp in seconds")
    spoof_score: Optional[float] = Field(None, description="Voice spoofing / synthetic voice confidence score (0.0 to 1.0)")
    raw_spoof_score: Optional[float] = Field(None, description="Raw base AASIST model spoof score")
    adapted_spoof_score: Optional[float] = Field(None, description="Adapted audio spoof score")
    status: Optional[str] = Field("analyzed", description="Window status: 'analyzed' | 'insufficient_speech' | 'error'")
    rms_db: Optional[float] = Field(None, description="RMS energy level in dBFS")


class AudioResult(BaseModel):
    """Audio deepfake / voice spoofing detection results (Member 3)."""
    available: bool = Field(False, description="Whether the audio detector is active and executed")
    model: Optional[str] = Field(None, description="Name and version of the audio detector model")
    status: str = Field("unavailable", description="Status of the audio detector (e.g., unavailable, completed, error)")
    windows_analyzed: Optional[int] = Field(None, description="Number of sliding audio windows analyzed")
    processing_time_s: Optional[float] = Field(None, description="Inference processing time in seconds")
    results: List[AudioWindowResult] = Field(default_factory=list, description="Time-windowed audio detection results")


class SpeechSegment(BaseModel):
    """Transcribed speech segment."""
    start_s: float = Field(..., description="Start timestamp in seconds")
    end_s: float = Field(..., description="End timestamp in seconds")
    text: str = Field(..., description="Transcribed text content")


class SpeechResult(BaseModel):
    """Speech-to-text transcription results (Member 3)."""
    available: bool = Field(False, description="Whether speech-to-text is active and executed")
    model: Optional[str] = Field(None, description="Name and version of the speech-to-text model")
    status: str = Field("unavailable", description="Status of the speech transcriber")
    language: Optional[str] = Field(None, description="Detected or configured spoken language code (e.g., 'en')")
    processing_time_s: Optional[float] = Field(None, description="Transcription processing time in seconds")
    segments: List[SpeechSegment] = Field(default_factory=list, description="Transcribed speech segments")
    transcript: Optional[str] = Field(None, description="Full stitched transcript text")


class InputInfo(BaseModel):
    """Uploaded input media classification."""
    media_type: str = Field(..., description="Media category: 'VIDEO' | 'AUDIO'")


class AudioMetadata(BaseModel):
    """Metadata extracted from standalone uploaded audio file."""
    filename: str = Field(..., description="Original filename of the uploaded audio")
    sha256: str = Field(..., description="SHA-256 cryptographic hash of the audio file")
    duration_s: float = Field(..., description="Total duration in seconds")
    sample_rate_hz: Optional[int] = Field(None, description="Audio sample rate in Hz")
    channels: Optional[int] = Field(None, description="Number of audio channels")
    codec: Optional[str] = Field(None, description="Audio codec format")
    bitrate_kbps: Optional[float] = Field(None, description="Audio bitrate in kbps")
    mime_type: Optional[str] = Field(None, description="Detected or declared MIME type")


class AnalysisResponse(BaseModel):
    """
    Unified Stage 1 + Stage 2 + Stage 3 Analysis Response contract.
    Contains raw sensor observations, synthesized evidence matrix, reliability gate,
    temporal timeline events, fraud intent findings, and final media assessment.
    Supports both VIDEO and AUDIO media inputs.
    """
    id: str = Field(..., description="Unique UUID for this analysis request")
    status: str = Field(..., description="Overall analysis status: completed | partial | error")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    
    # Input media classification
    input: InputInfo = Field(default_factory=lambda: InputInfo(media_type="VIDEO"), description="Input media classification")
    
    # Stage 1: Raw media metadata and sensory observations
    video: Optional[VideoInfo] = Field(None, description="Extracted video metadata (for VIDEO)")
    audio_metadata: Optional[AudioMetadata] = Field(None, description="Extracted audio metadata (for standalone AUDIO)")
    visual: VisualResult = Field(default_factory=VisualResult, description="Visual deepfake detector output")
    audio: AudioResult = Field(default_factory=AudioResult, description="Audio deepfake detector output")
    speech: SpeechResult = Field(default_factory=SpeechResult, description="Speech-to-text output")
    
    # Stage 2: Evidence & Trust Engine outputs
    reliability: Optional[ReliabilityResult] = Field(None, description="Reliability Gate assessment")
    evidence: Optional[EvidenceMatrix] = Field(None, description="Synthesized multi-modal Evidence Matrix")
    timeline: List[TimelineEvent] = Field(default_factory=list, description="Aggregated chronological timeline events")
    assessment: Optional[MediaAssessment] = Field(None, description="Media assessment verdict")
    explanation: List[str] = Field(default_factory=list, description="Evidence-grounded human explanations")
    limitations: List[str] = Field(default_factory=list, description="Systemic and model-specific limitations")
    
    # Stage 3: Fraud Intent Engine outputs
    fraud: Optional[FraudResult] = Field(None, description="Fraud intent & social-engineering risk findings")
    
    # Fast Re-Analysis & Cache Telemetry
    cached: Optional[bool] = Field(False, description="Whether this response was served from fast re-analysis cache")
    reanalysis_speedup_ms: Optional[float] = Field(None, description="Latency in milliseconds if served from fast cache")


class HealthResponse(BaseModel):
    """Health check endpoint response model."""
    status: str = Field("ok", description="Server status")
    ffmpeg_available: bool = Field(..., description="Whether ffmpeg CLI is accessible")
    ffprobe_available: bool = Field(..., description="Whether ffprobe CLI is accessible")
    version: str = Field(..., description="Application version")


class ErrorResponse(BaseModel):
    """Standard sanitized API error response."""
    detail: str = Field(..., description="Human-readable error description")
    error_code: Optional[str] = Field(None, description="Machine-readable error code")
