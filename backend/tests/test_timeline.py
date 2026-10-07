import pytest
from app.schemas.analysis import (
    AudioResult,
    AudioWindowResult,
    SpeechResult,
    SpeechSegment,
    VisualFrameResult,
    VisualResult,
)
from app.services.timeline_service import TimelineService


def test_timeline_aggregation_visual_consecutive_vs_isolated():
    service = TimelineService(
        window_duration_s=3.0,
        visual_low=0.30,
        visual_high=0.70,
        audio_low=0.30,
        audio_high=0.70,
    )

    # 1. Test isolated spike: Window 0 is HIGH (0.85), Window 1 is LOW (0.10), Window 2 is LOW (0.10)
    # The isolated HIGH in window 0 has no adjacent qualifying window (score >= 0.30)
    visual_isolated = VisualResult(
        available=True,
        status="completed",
        results=[
            VisualFrameResult(timestamp_s=0.5, face_detected=True, fake_score=0.85),
            VisualFrameResult(timestamp_s=3.5, face_detected=True, fake_score=0.10),
            VisualFrameResult(timestamp_s=6.5, face_detected=True, fake_score=0.05),
        ],
    )
    audio = AudioResult(available=False, results=[])
    speech = SpeechResult(available=False, segments=[])

    events = service.aggregate(visual_isolated, audio, speech, video_duration_s=9.0)
    visual_events = [ev for ev in events if ev.kind == "visual"]
    assert len(visual_events) == 3
    # Isolated spike should be attenuated to MEDIUM
    assert visual_events[0].level == "MEDIUM"
    assert visual_events[0].score == 0.85


def test_timeline_aggregation_consecutive_high_windows():
    service = TimelineService(
        window_duration_s=3.0,
        visual_low=0.30,
        visual_high=0.70,
    )

    # Window 0 is HIGH (0.85), Window 1 is HIGH (0.75) -> Consecutive high signals
    visual_consecutive = VisualResult(
        available=True,
        status="completed",
        results=[
            VisualFrameResult(timestamp_s=0.5, face_detected=True, fake_score=0.85),
            VisualFrameResult(timestamp_s=3.5, face_detected=True, fake_score=0.75),
        ],
    )
    audio = AudioResult(available=False, results=[])
    speech = SpeechResult(available=False, segments=[])

    events = service.aggregate(visual_consecutive, audio, speech, video_duration_s=6.0)
    visual_events = [ev for ev in events if ev.kind == "visual"]
    assert visual_events[0].level == "HIGH"
    assert visual_events[1].level == "HIGH"


def test_timeline_aggregation_multimodal_chronology():
    service = TimelineService()

    visual = VisualResult(
        available=True,
        status="completed",
        results=[
            VisualFrameResult(timestamp_s=1.0, face_detected=True, fake_score=0.2),
        ],
    )
    audio = AudioResult(
        available=True,
        status="completed",
        results=[
            AudioWindowResult(start_s=0.0, end_s=3.0, spoof_score=0.8),
        ],
    )
    speech = SpeechResult(
        available=True,
        status="completed",
        segments=[
            SpeechSegment(start_s=0.5, end_s=2.5, text="Hello Authentica"),
        ],
    )

    events = service.aggregate(visual, audio, speech, video_duration_s=3.0)

    # Check chronological ordering: sorted by start_s
    for i in range(len(events) - 1):
        assert events[i].start_s <= events[i + 1].start_s

    kinds = {ev.kind for ev in events}
    assert kinds == {"visual", "audio", "transcript"}
