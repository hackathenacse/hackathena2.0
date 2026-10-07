import pytest
from app.schemas.analysis import AudioResult, VideoInfo, VisualFrameResult, VisualResult
from app.services.reliability_service import ReliabilityService


def test_reliability_gate_ok():
    service = ReliabilityService()
    video_info = VideoInfo(
        filename="test.mp4",
        sha256="abc123",
        duration_s=10.0,
        fps=30.0,
        width=1280,
        height=720,
        frames_sampled=10,
        audio_available=True,
    )
    visual = VisualResult(
        available=True,
        model="EfficientNet-B0-FFPP-C23",
        status="completed",
        frames_analyzed=10,
        faces_found=8,
        face_detection_rate=0.8,
        results=[VisualFrameResult(timestamp_s=i, face_detected=True, fake_score=0.1) for i in range(8)],
    )
    audio = AudioResult(
        available=True,
        model="AASIST-ASVspoof2019-LA",
        status="completed",
        windows_analyzed=3,
        results=[],
    )

    result = service.evaluate(video_info, visual, audio)
    assert result.level == "OK"
    assert len(result.reasons) == 0


def test_reliability_gate_low_resolution():
    service = ReliabilityService(min_width=360, min_height=360)
    video_info = VideoInfo(
        filename="low_res.mp4",
        sha256="abc123",
        duration_s=10.0,
        fps=30.0,
        width=240,
        height=240,
        frames_sampled=10,
        audio_available=True,
    )
    visual = VisualResult(available=True, status="completed", frames_analyzed=10, faces_found=10, face_detection_rate=1.0)
    audio = AudioResult(available=True, status="completed")

    result = service.evaluate(video_info, visual, audio)
    assert result.level == "LOW"
    assert any("resolution (240x240) is below recommended threshold" in r for r in result.reasons)


def test_reliability_gate_low_face_coverage():
    service = ReliabilityService(min_face_rate=0.30)
    video_info = VideoInfo(
        filename="test.mp4",
        sha256="abc123",
        duration_s=10.0,
        fps=30.0,
        width=1280,
        height=720,
        frames_sampled=10,
        audio_available=True,
    )
    visual = VisualResult(
        available=True,
        status="completed",
        frames_analyzed=10,
        faces_found=2,
        face_detection_rate=0.20,
    )
    audio = AudioResult(available=True, status="completed")

    result = service.evaluate(video_info, visual, audio)
    assert result.level == "LOW"
    assert any("Face detection coverage is low (20.0%" in r for r in result.reasons)


def test_reliability_gate_no_faces_found():
    service = ReliabilityService()
    video_info = VideoInfo(
        filename="test.mp4",
        sha256="abc123",
        duration_s=10.0,
        fps=30.0,
        width=1280,
        height=720,
        frames_sampled=10,
        audio_available=True,
    )
    visual = VisualResult(
        available=True,
        status="completed",
        frames_analyzed=10,
        faces_found=0,
        face_detection_rate=0.0,
    )
    audio = AudioResult(available=True, status="completed")

    result = service.evaluate(video_info, visual, audio)
    assert result.level == "LOW"
    assert any("No detectable faces found" in r for r in result.reasons)


def test_reliability_gate_short_audio():
    service = ReliabilityService(min_audio_dur=3.0)
    video_info = VideoInfo(
        filename="short_audio.mp4",
        sha256="abc123",
        duration_s=1.5,
        fps=30.0,
        width=1280,
        height=720,
        frames_sampled=2,
        audio_available=True,
    )
    visual = VisualResult(available=True, status="completed", frames_analyzed=2, faces_found=2, face_detection_rate=1.0)
    audio = AudioResult(available=True, status="completed")

    result = service.evaluate(video_info, visual, audio)
    assert result.level == "LOW"
    assert any("Audio track duration (1.5s) is shorter than recommended minimum" in r for r in result.reasons)


def test_reliability_gate_model_error():
    service = ReliabilityService()
    video_info = VideoInfo(
        filename="test.mp4",
        sha256="abc123",
        duration_s=10.0,
        fps=30.0,
        width=1280,
        height=720,
        frames_sampled=10,
        audio_available=True,
    )
    visual = VisualResult(available=False, status="error")
    audio = AudioResult(available=True, status="completed")

    result = service.evaluate(video_info, visual, audio)
    assert result.level == "LOW"
    assert any("Visual deepfake detector encountered an execution error" in r for r in result.reasons)


def test_reliability_gate_small_face_pixel_size():
    from app.schemas.analysis import VisualFrameResult
    service = ReliabilityService()
    video_info = VideoInfo(
        filename="small_face.mp4",
        sha256="abc123",
        duration_s=10.0,
        fps=30.0,
        width=1280,
        height=720,
        frames_sampled=5,
        audio_available=True,
    )
    # Face detections with pixel size < 48px
    frames = [
        VisualFrameResult(timestamp_s=i, face_detected=True, fake_score=0.75, face_pixel_size=32)
        for i in range(5)
    ]
    visual = VisualResult(available=True, status="completed", frames_analyzed=5, faces_found=5, face_detection_rate=1.0, results=frames)
    audio = AudioResult(available=True, status="completed")

    result = service.evaluate(video_info, visual, audio)
    assert result.level == "LOW"
    assert any("below minimum forensic resolution (48px)" in r for r in result.reasons)


def test_reliability_gate_blurry_faces():
    from app.schemas.analysis import VisualFrameResult
    service = ReliabilityService()
    video_info = VideoInfo(
        filename="blurry.mp4",
        sha256="abc123",
        duration_s=10.0,
        fps=30.0,
        width=1280,
        height=720,
        frames_sampled=5,
        audio_available=True,
    )
    # Face detections with severe blur (blur_score < 40)
    frames = [
        VisualFrameResult(timestamp_s=i, face_detected=True, fake_score=0.8, face_pixel_size=100, blur_score=22.0)
        for i in range(5)
    ]
    visual = VisualResult(available=True, status="completed", frames_analyzed=5, faces_found=5, face_detection_rate=1.0, results=frames)
    audio = AudioResult(available=True, status="completed")

    result = service.evaluate(video_info, visual, audio)
    assert result.level == "LOW"
    assert any("optical defocus or motion blur detected" in r for r in result.reasons)

