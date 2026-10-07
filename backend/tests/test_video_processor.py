from pathlib import Path
import pytest

from app.services.video_processor import (
    CorruptedVideoError,
    VideoDurationExceededError,
    VideoProcessor,
)


def test_video_processor_metadata_and_sampling(synthetic_video_path: Path, temp_test_dir: Path):
    """Verifies that VideoProcessor accurately extracts metadata and samples frames at 1 FPS."""
    frames_dir = temp_test_dir / "frames"
    audio_dir = temp_test_dir / "audio"
    frames_dir.mkdir()
    audio_dir.mkdir()

    processor = VideoProcessor(max_duration_s=90.0, sample_fps=1.0)
    result = processor.process(
        video_path=synthetic_video_path,
        frames_dir=frames_dir,
        audio_dir=audio_dir
    )

    # 3 second video @ 1 FPS should yield ~3 sampled frames
    assert result.duration_s == pytest.approx(3.0, rel=0.2)
    assert result.fps == pytest.approx(10.0, rel=0.1)
    assert result.width == 320
    assert result.height == 240
    assert result.frames_sampled >= 3
    assert len(result.frame_samples) == result.frames_sampled

    # Check that frame files were actually written to disk
    for sample in result.frame_samples:
        assert sample.frame_path.exists()
        assert sample.frame_path.stat().st_size > 0
        assert sample.timestamp_s >= 0.0


def test_video_processor_corrupted_file(temp_test_dir: Path):
    """Verifies that non-video or corrupt binary garbage is cleanly rejected."""
    corrupt_path = temp_test_dir / "corrupted.mp4"
    corrupt_path.write_bytes(b"NON_VIDEO_RANDOM_CORRUPT_BYTES_XYZ_1234567890" * 50)

    frames_dir = temp_test_dir / "frames"
    audio_dir = temp_test_dir / "audio"
    frames_dir.mkdir()
    audio_dir.mkdir()

    processor = VideoProcessor()
    with pytest.raises(CorruptedVideoError):
        processor.process(
            video_path=corrupt_path,
            frames_dir=frames_dir,
            audio_dir=audio_dir
        )


def test_video_processor_duration_limit(synthetic_video_path: Path, temp_test_dir: Path):
    """Verifies that videos exceeding max_duration_s raise VideoDurationExceededError."""
    frames_dir = temp_test_dir / "frames"
    audio_dir = temp_test_dir / "audio"
    frames_dir.mkdir()
    audio_dir.mkdir()

    # Configure max duration lower than test video (1.0s vs 3.0s)
    processor = VideoProcessor(max_duration_s=1.0)
    with pytest.raises(VideoDurationExceededError) as exc_info:
        processor.process(
            video_path=synthetic_video_path,
            frames_dir=frames_dir,
            audio_dir=audio_dir
        )
    assert "exceeds maximum allowed limit" in str(exc_info.value)
