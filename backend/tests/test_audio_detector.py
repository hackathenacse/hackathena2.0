import tempfile
from pathlib import Path
import numpy as np
import pytest
import soundfile as sf
import torch

from app.schemas.analysis import AudioResult, VideoInfo
from app.services.detectors.audio_detector import (
    MODEL_NAME,
    LocalAudioAntiSpoofDetector,
    TARGET_SAMPLE_RATE,
)


@pytest.fixture(scope="module")
def audio_detector():
    """Initializes and loads the local audio anti-spoofing detector once for tests."""
    detector = LocalAudioAntiSpoofDetector(device="cpu")
    detector.load()
    return detector


@pytest.fixture
def dummy_video_info():
    return VideoInfo(
        filename="test_sample.mp4",
        sha256="1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        duration_s=6.0,
        fps=30.0,
        width=1280,
        height=720,
        frames_sampled=6,
        audio_available=True,
    )


def create_synthetic_wav(file_path: Path, duration_s: float = 6.0, freq_hz: float = 440.0) -> Path:
    """Generates a synthetic 16kHz mono WAV file for testing."""
    total_samples = int(TARGET_SAMPLE_RATE * duration_s)
    t = np.linspace(0, duration_s, total_samples, endpoint=False, dtype=np.float32)
    # Sine wave with gentle amplitude modulation
    waveform = 0.5 * np.sin(2 * np.pi * freq_hz * t) * (0.8 + 0.2 * np.sin(2 * np.pi * 2 * t))
    sf.write(str(file_path.resolve()), waveform, TARGET_SAMPLE_RATE, subtype="PCM_16")
    return file_path


def test_audio_detector_model_loading(audio_detector):
    """Verifies that the AASIST model architecture and weights initialize correctly."""
    assert audio_detector._is_loaded is True
    assert audio_detector.model is not None
    assert isinstance(audio_detector.model, torch.nn.Module)


@pytest.mark.asyncio
async def test_audio_detector_sliding_windows(audio_detector, dummy_video_info, tmp_path):
    """
    Verifies that a 6-second audio produces multiple sliding windows (~4s window, 2s stride).
    """
    wav_path = tmp_path / "test_6s.wav"
    create_synthetic_wav(wav_path, duration_s=6.0)

    result = await audio_detector.analyze(audio_path=wav_path, video_info=dummy_video_info)

    assert isinstance(result, AudioResult)
    assert result.available is True
    assert result.model == MODEL_NAME
    assert result.status == "completed"
    assert result.windows_analyzed >= 2
    assert len(result.results) == result.windows_analyzed

    # Validate window timestamps and scores
    prev_start = -1.0
    for window in result.results:
        assert window.start_s >= 0.0
        assert window.end_s > window.start_s
        assert window.start_s > prev_start
        assert window.spoof_score is not None
        assert 0.0 <= window.spoof_score <= 1.0
        prev_start = window.start_s


@pytest.mark.asyncio
async def test_audio_detector_short_clip(audio_detector, tmp_path):
    """Verifies that audio shorter than 4s is analyzed gracefully with 1 window."""
    wav_path = tmp_path / "test_short.wav"
    create_synthetic_wav(wav_path, duration_s=1.5)

    video_info = VideoInfo(
        filename="short.mp4",
        sha256="abc1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcd",
        duration_s=1.5,
        fps=30.0,
        width=640,
        height=480,
        frames_sampled=2,
        audio_available=True,
    )

    result = await audio_detector.analyze(audio_path=wav_path, video_info=video_info)

    assert result.available is True
    assert result.status == "completed"
    assert result.windows_analyzed == 1
    assert len(result.results) == 1
    assert result.results[0].start_s == 0.0
    assert result.results[0].end_s == 1.5
    assert result.results[0].spoof_score is not None
    assert 0.0 <= result.results[0].spoof_score <= 1.0


@pytest.mark.asyncio
async def test_audio_detector_no_audio_stream(audio_detector):
    """Verifies graceful handling when media has no audio track."""
    video_info = VideoInfo(
        filename="silent.mp4",
        sha256="abc1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcd",
        duration_s=3.0,
        fps=30.0,
        width=640,
        height=480,
        frames_sampled=3,
        audio_available=False,
    )

    result = await audio_detector.analyze(audio_path=None, video_info=video_info)

    assert result.available is False
    assert result.status == "unavailable"
    assert result.windows_analyzed == 0
    assert len(result.results) == 0


@pytest.mark.asyncio
async def test_audio_detector_corrupted_file(audio_detector, dummy_video_info, tmp_path):
    """Verifies that a corrupt audio file returns status='error' without raising an exception."""
    bad_wav = tmp_path / "corrupt.wav"
    bad_wav.write_bytes(b"NOT A WAV FILE GARBAGE DATA")

    result = await audio_detector.analyze(audio_path=bad_wav, video_info=dummy_video_info)

    assert result.available is False
    assert result.status == "error"
    assert len(result.results) == 0


def test_aasist_polarity_and_synthetic_detection(audio_detector):
    """
    Empirically verifies AASIST class ordering:
    - Index 0 = Spoof (synthetic/unnatural waveforms get high spoof score)
    - Index 1 = Bonafide
    """
    sr = 16000
    t = np.linspace(0, 4.0, int(sr * 4.0), endpoint=False, dtype=np.float32)
    # 440 Hz synthetic sine tone
    sine = (0.5 * np.sin(2 * np.pi * 440.0 * t)).astype(np.float32)
    score = audio_detector.predict_window(sine)
    assert score is not None
    assert score > 0.80, f"Expected synthetic tone to yield high spoof_score (>0.80), got {score}"


@pytest.mark.asyncio
async def test_audio_detector_silence_returns_none(audio_detector, tmp_path):
    """
    Verifies that silence (< -45 dBFS) is excluded with status='insufficient_speech'
    and spoof_score=None (never fabricated 0.02 authenticity score).
    """
    sr = 16000
    silent_audio = np.zeros(sr * 4, dtype=np.float32)
    score = audio_detector.predict_window(silent_audio)
    assert score is None, f"Expected None on silence, got {score}"

    wav_path = tmp_path / "silence.wav"
    sf.write(str(wav_path), silent_audio, sr, subtype="PCM_16")

    video_info = VideoInfo(
        filename="silence.mp4",
        sha256="abc1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcd",
        duration_s=4.0,
        fps=30.0,
        width=640,
        height=480,
        frames_sampled=4,
        audio_available=True,
    )
    result = await audio_detector.analyze(audio_path=wav_path, video_info=video_info)
    assert result.available is True
    assert len(result.results) > 0
    for w in result.results:
        assert w.spoof_score is None
        assert w.status == "insufficient_speech"

