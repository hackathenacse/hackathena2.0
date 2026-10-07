import subprocess
from pathlib import Path
import numpy as np
import pytest
import soundfile as sf

from app.schemas.analysis import SpeechResult, VideoInfo
from app.services.detectors.speech_transcriber import (
    MODEL_NAME,
    FasterWhisperTranscriber,
)


@pytest.fixture(scope="module")
def transcriber():
    """Initializes and loads the FasterWhisperTranscriber once for tests."""
    t = FasterWhisperTranscriber(model_size="base", device="cpu", compute_type="int8")
    t.load()
    return t


@pytest.fixture
def dummy_video_info():
    return VideoInfo(
        filename="test_sample.mp4",
        sha256="1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        duration_s=4.0,
        fps=30.0,
        width=1280,
        height=720,
        frames_sampled=4,
        audio_available=True,
    )


def create_speech_audio_ffmpeg(file_path: Path) -> Path:
    """
    Creates a small 16kHz test WAV file containing synthetic tone pulses.
    """
    try:
        import static_ffmpeg
        static_ffmpeg.add_paths()
    except Exception:
        pass

    # Generate a 2.5s audio with beep patterns
    cmd = [
        "ffmpeg", "-v", "error", "-y",
        "-f", "lavfi", "-i", "sine=frequency=1000:duration=2.5",
        "-ar", "16000",
        "-ac", "1",
        str(file_path.resolve())
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    return file_path


def test_transcriber_loading(transcriber):
    """Verifies that the faster-whisper model initializes correctly."""
    assert transcriber._is_loaded is True
    assert transcriber.model is not None


@pytest.mark.asyncio
async def test_transcribe_synthetic_audio(transcriber, dummy_video_info, tmp_path):
    """Verifies that faster-whisper runs inference and produces a structured SpeechResult."""
    audio_path = tmp_path / "test_audio.wav"
    create_speech_audio_ffmpeg(audio_path)

    result = await transcriber.transcribe(audio_path=audio_path, video_info=dummy_video_info)

    assert isinstance(result, SpeechResult)
    assert result.available is True
    assert result.model == MODEL_NAME
    assert result.status == "completed"
    assert result.language is not None
    assert result.processing_time_s is not None and result.processing_time_s >= 0.0
    assert isinstance(result.segments, list)


@pytest.mark.asyncio
async def test_transcribe_no_audio(transcriber):
    """Verifies graceful handling when video has no audio stream."""
    video_info = VideoInfo(
        filename="no_audio.mp4",
        sha256="abc1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcd",
        duration_s=3.0,
        fps=30.0,
        width=640,
        height=480,
        frames_sampled=3,
        audio_available=False,
    )

    result = await transcriber.transcribe(audio_path=None, video_info=video_info)

    assert result.available is False
    assert result.status == "unavailable"
    assert len(result.segments) == 0


@pytest.mark.asyncio
async def test_transcribe_corrupted_audio(transcriber, dummy_video_info, tmp_path):
    """Verifies that a corrupted audio file returns status='error' without raising an unhandled exception."""
    corrupt_file = tmp_path / "corrupt.wav"
    corrupt_file.write_bytes(b"INVALID DATA")

    result = await transcriber.transcribe(audio_path=corrupt_file, video_info=dummy_video_info)

    assert result.available is False
    assert result.status == "error"
    assert len(result.segments) == 0
