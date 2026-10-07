import pytest
from app.schemas.analysis import (
    AudioResult,
    AudioWindowResult,
    VideoInfo,
    VisualFrameResult,
    VisualResult,
)
from app.schemas.evidence import ProvenanceResult
from app.schemas.reliability import ReliabilityResult
from app.services.evidence_service import EvidenceService


def test_evidence_service_levels():
    service = EvidenceService(
        visual_low=0.30, visual_high=0.70, audio_low=0.30, audio_high=0.70
    )

    video_info = VideoInfo(
        filename="test.mp4",
        sha256="abc",
        duration_s=10.0,
        fps=30.0,
        width=1280,
        height=720,
        frames_sampled=5,
        audio_available=True,
    )

    # 1. High Visual, Low Audio
    visual_high = VisualResult(
        available=True,
        model="EfficientNet-B0-FFPP-C23",
        status="completed",
        frames_analyzed=3,
        faces_found=3,
        face_detection_rate=1.0,
        results=[
            VisualFrameResult(timestamp_s=0.0, face_detected=True, fake_score=0.85),
            VisualFrameResult(timestamp_s=1.0, face_detected=True, fake_score=0.78),
        ],
    )
    audio_low = AudioResult(
        available=True,
        model="AASIST-ASVspoof2019-LA",
        status="completed",
        results=[
            AudioWindowResult(start_s=0.0, end_s=3.0, spoof_score=0.12),
        ],
    )
    prov = ProvenanceResult(state="NONE_FOUND", valid=None, trusted=None, signer=None, note="No C2PA")
    rel = ReliabilityResult(level="OK", reasons=[])

    matrix = service.build_matrix(video_info, visual_high, audio_low, prov, rel)

    assert matrix.visual.level == "HIGH"
    assert matrix.visual.models[0].score == 0.815
    assert matrix.visual.statistics is not None
    assert matrix.visual.statistics.max_score == 0.85
    assert matrix.visual.models[0].label == "model score (not a probability)"

    assert matrix.audio.level == "LOW"
    assert matrix.audio.models[0].score == 0.12
    assert matrix.audio.models[0].label == "model score (not a probability)"


def test_evidence_service_medium_and_na():
    service = EvidenceService(visual_low=0.30, visual_high=0.70, audio_low=0.30, audio_high=0.70)

    video_info = VideoInfo(
        filename="test.mp4",
        sha256="abc",
        duration_s=10.0,
        fps=30.0,
        width=1280,
        height=720,
        frames_sampled=5,
        audio_available=False,
    )

    visual_med = VisualResult(
        available=True,
        model="EfficientNet-B0-FFPP-C23",
        status="completed",
        frames_analyzed=2,
        faces_found=2,
        face_detection_rate=1.0,
        results=[
            VisualFrameResult(timestamp_s=0.0, face_detected=True, fake_score=0.45),
        ],
    )
    audio_na = AudioResult(available=False, status="unavailable", results=[])
    prov = ProvenanceResult(state="NONE_FOUND", valid=None, trusted=None, signer=None, note="No C2PA")
    rel = ReliabilityResult(level="OK", reasons=[])

    matrix = service.build_matrix(video_info, visual_med, audio_na, prov, rel)
    assert matrix.visual.level == "MEDIUM"
    assert matrix.audio.level == "N/A"
