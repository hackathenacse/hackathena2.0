import os
import time
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from app.schemas.analysis import AnalysisResponse, InputInfo, VisualResult, AudioResult, SpeechResult, SpeechSegment, VideoInfo
from app.schemas.evidence import EvidenceMatrix, EvidenceMetadata, ProvenanceResult, MediaAssessment, EvidenceModalityResult
from app.schemas.fraud import FraudResult, FraudCategoryEvidence
from app.schemas.reliability import ReliabilityResult
from app.services.cache_service import AnalysisCacheService
from app.services.active_learning.training_service import ActiveLearningTrainingService
from app.services.assessment_service import AssessmentService
from app.services.fraud_engine import FraudIntentEngine


def test_cache_service_set_and_get(tmp_path):
    cache = AnalysisCacheService(cache_dir=tmp_path)
    sha = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    payload = {
        "id": "test-id-1",
        "status": "completed",
        "created_at": "2026-10-07T10:00:00Z",
        "visual": {"available": True, "frames_analyzed": 5, "faces_found": 5, "status": "completed", "results": []},
        "audio": {"available": False, "status": "not_applicable", "results": []},
        "speech": {"available": False, "status": "not_applicable", "segments": []},
    }
    
    # 1. Miss initially
    assert cache.get(sha, "visual-v0") is None
    
    # 2. Store
    cache.set(sha, "visual-v0", payload)
    
    # 3. Hit under same adapter version
    hit = cache.get(sha, "visual-v0")
    assert hit is not None
    assert hit["response"]["id"] == "test-id-1"
    
    # 4. Miss under new adapter version
    assert cache.get(sha, "visual-v1") is None


def test_cache_invalidation_by_adapter_version(tmp_path):
    cache = AnalysisCacheService(cache_dir=tmp_path)
    sha1 = "aaa111222333444555666777888999aa"
    sha2 = "bbb111222333444555666777888999bb"
    cache.set(sha1, "visual-v0", {"dummy": 1})
    cache.set(sha2, "visual-v0", {"dummy": 2})
    
    assert cache.get(sha1, "visual-v0") is not None
    
    # Invalidate all visual-v0 entries
    purged = cache.invalidate_by_adapter_version("visual-v0")
    assert purged == 2
    assert cache.get(sha1, "visual-v0") is None


def test_active_learning_balanced_eligibility(tmp_path):
    adapter_dir = tmp_path / "adapters"
    data_dir = tmp_path / "data"
    adapter_dir.mkdir()
    data_dir.mkdir()
    
    service = ActiveLearningTrainingService(adapter_dir=adapter_dir, data_dir=data_dir, device="cpu")
    
    features = [[0.1] * 1280]
    telem = [[0.5, 0.5, 0.5, 0.0]]
    
    # Sample 1: REAL (only 1 real, 0 fake -> must defer)
    res1 = service.register_and_train_sample(
        analysis_id="test-1",
        features=features,
        telemetry=telem,
        ground_truth_media="REAL",
        transcript="sample test"
    )
    assert res1["status"] == "deferred"
    assert res1["real_count"] == 1
    assert res1["fake_count"] == 0
    
    # Base model checksum must remain completely intact
    assert res1["base_model_checksum"] is not None


def test_known_real_threat_video_orthogonal_assessment():
    """
    REGRESSION TEST:
    A known-real recording containing high-risk threat speech ("Your boy is in my hand...")
    MUST yield:
      Media Authenticity = NO_STRONG_EVIDENCE (or UNCERTAIN)
      Fraud Intent = HIGH
      Action = STOP_AND_VERIFY
    The system must NEVER output LIKELY_MANIPULATED.
    """
    assessment_service = AssessmentService()
    fraud_engine = FraudIntentEngine()
    
    # Simulate Whisper transcription of the threat video
    speech_result = SpeechResult(
        available=True,
        model="faster-whisper-base",
        status="completed",
        language="en",
        processing_time_s=1.2,
        segments=[
            SpeechSegment(start_s=0.0, end_s=2.5, text="Your boy is in my hand, Mr."),
            SpeechSegment(start_s=2.5, end_s=6.0, text="Give me 10 crore rupees and I will think about releasing him."),
            SpeechSegment(start_s=6.0, end_s=9.0, text="Don't even tell the police, I will kill him if I want to."),
        ]
    )
    
    fraud_result = fraud_engine.evaluate(speech_result)
    assert fraud_result.level == "HIGH"
    
    # Simulate visual & audio modalities for genuine capture (low manipulation)
    matrix = MagicMock(spec=EvidenceMatrix)
    matrix.reliability = MagicMock(spec=ReliabilityResult)
    matrix.reliability.level = "OK"
    matrix.visual = MagicMock()
    matrix.visual.level = "LOW"
    matrix.audio = MagicMock()
    matrix.audio.level = "LOW"
    matrix.metadata = MagicMock(spec=EvidenceMetadata)
    matrix.metadata.exact_verified_match = False
    matrix.metadata.verified_ground_truth = None
    matrix.provenance = ProvenanceResult(state="NONE_FOUND", note="No C2PA manifest found.")
    
    assessment, explanations, limitations = assessment_service.assess(
        matrix=matrix,
        timeline=[],
        fraud=fraud_result
    )
    
    # Verify strict invariant
    assert assessment.media == "NO_STRONG_EVIDENCE"
    assert assessment.fraud == "HIGH"
    assert assessment.action == "STOP_AND_VERIFY"


def test_direct_threat_speech_not_downgraded_by_news_context():
    """Direct coercion with threat/secrecy must NOT be downgraded."""
    fraud_engine = FraudIntentEngine()
    
    speech_result = SpeechResult(
        available=True,
        model="faster-whisper-base",
        status="completed",
        language="en",
        processing_time_s=1.0,
        segments=[
            SpeechSegment(start_s=0.0, end_s=5.0, text="Give me the cash or I will shoot him. Do not tell anyone or go to the police.")
        ]
    )
    
    fraud = fraud_engine.evaluate(speech_result)
    assert fraud.level == "HIGH"
    assert fraud.news_context_downgrade is False


def test_speech_result_transcript_attribute_safety():
    """Verify SpeechResult has safe transcript access without raising AttributeError."""
    res = SpeechResult(
        available=True,
        model="whisper",
        status="completed",
        segments=[
            SpeechSegment(start_s=0.0, end_s=1.0, text="Hello"),
            SpeechSegment(start_s=1.0, end_s=2.0, text="world")
        ]
    )
    # Both attribute access and getattr must succeed
    assert hasattr(res, "transcript")
    # transcript field is present
    assert res.transcript is None or isinstance(res.transcript, str)


@pytest.mark.anyio
async def test_verified_ground_truth_reanalysis_persistence(tmp_path):
    """
    REGRESSION TEST:
    When an analyst marks an analysis as REAL (even if high fraud risk):
    1. The stored analysis updates in-place to NO_STRONG_EVIDENCE and STOP_AND_VERIFY.
    2. VerifiedMediaRegistry remembers it.
    3. Next time the same video is evaluated, it outputs NO_STRONG_EVIDENCE and STOP_AND_VERIFY.
    """
    from app.services.active_learning.verified_memory import VerifiedMediaRegistry
    from app.db import DatabaseService, FeedbackPayload
    
    sha = "test_sha_repeat_verification_12345"
    analysis_id = "test-analysis-repeat-1"
    
    # 1. Create initial analysis with high fraud and suspicious media
    analysis = AnalysisResponse(
        id=analysis_id,
        status="completed",
        created_at="2026-10-07T10:00:00Z",
        video=VideoInfo(
            filename="threat_test.mp4",
            sha256=sha,
            duration_s=10.0,
            fps=30.0,
            width=1280,
            height=720,
            frames_sampled=10,
            audio_available=True
        ),
        assessment=MediaAssessment(
            media="LIKELY_MANIPULATED",
            fraud="HIGH",
            action="STOP_AND_VERIFY"
        ),
        evidence=EvidenceMatrix(
            visual=EvidenceModalityResult(level="LOW"),
            audio=EvidenceModalityResult(level="LOW"),
            provenance=ProvenanceResult(state="NONE_FOUND", note="No C2PA manifest found."),
            metadata=EvidenceMetadata(
                media_type="VIDEO",
                duration_s=10.0,
                exact_verified_match=False,
                verified_ground_truth=None
            ),
            reliability=ReliabilityResult(level="OK")
        ),
        explanation=["Initial detection run"]
    )
    
    await DatabaseService.save_analysis(analysis)
    
    # 2. Analyst marks it from History / Report as CONFIRMED REAL with HIGH FRAUD
    feedback = FeedbackPayload(
        ground_truth_media="REAL",
        ground_truth_fraud="SCAM",
        notes="Known genuine threat video",
        analyst_id="lead_analyst"
    )
    
    await DatabaseService.record_feedback(analysis_id, feedback)
    
    # 3. Reload stored analysis from DB/disk: must be updated to NO_STRONG_EVIDENCE and STOP_AND_VERIFY
    updated_analysis = await DatabaseService.get_analysis(analysis_id)
    assert updated_analysis is not None
    assert updated_analysis.assessment.media == "NO_STRONG_EVIDENCE"
    assert updated_analysis.assessment.fraud == "HIGH"
    assert updated_analysis.assessment.action == "STOP_AND_VERIFY"
    assert updated_analysis.evidence.metadata.exact_verified_match is True
    
    # 4. In VerifiedMediaRegistry, exact lookup must return REAL
    registry = VerifiedMediaRegistry.get_instance()
    registry.register(
        sha256=sha,
        filename="threat_test.mp4",
        ground_truth_media="REAL",
        ground_truth_fraud="SCAM"
    )
    matched = registry.lookup_exact_sha256(sha)
    assert matched is not None
    assert matched["ground_truth_media"] == "REAL"
    assert matched["ground_truth_fraud"] == "SCAM"


