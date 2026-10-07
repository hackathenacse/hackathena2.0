import hashlib
from pathlib import Path
import pytest

from app.utils.ffmpeg import (
    FFmpegUnavailableError,
    check_ffmpeg_available,
    ensure_ffmpeg_installed,
)
from app.utils.hashing import compute_sha256


def test_ffmpeg_availability_live():
    """Verifies that FFmpeg and FFprobe checks succeed on system."""
    ffmpeg_ok, ffprobe_ok, err_msg = check_ffmpeg_available()
    assert ffmpeg_ok is True
    assert ffprobe_ok is True
    assert err_msg is None


def test_ffmpeg_missing_simulation(monkeypatch):
    """Verifies clear error messaging when FFmpeg or FFprobe are missing."""
    import shutil
    
    # Mock shutil.which to return None for ffmpeg
    monkeypatch.setattr(shutil, "which", lambda cmd: None)
    
    ffmpeg_ok, ffprobe_ok, err_msg = check_ffmpeg_available()
    assert ffmpeg_ok is False
    assert ffprobe_ok is False
    assert "missing" in err_msg.lower()

    with pytest.raises(FFmpegUnavailableError):
        ensure_ffmpeg_installed()


def test_sha256_computation(temp_test_dir: Path):
    """Verifies SHA-256 computation against known string hash."""
    test_file = temp_test_dir / "sample.txt"
    sample_content = b"Authentica Hackathena 2026 Stage 1 Foundation"
    test_file.write_bytes(sample_content)

    expected_hash = hashlib.sha256(sample_content).hexdigest()
    computed_hash = compute_sha256(test_file)

    assert computed_hash == expected_hash
