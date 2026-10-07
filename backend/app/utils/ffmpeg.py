import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from app.core.logging import logger


class FFmpegUnavailableError(RuntimeError):
    """Raised when ffmpeg or ffprobe executable is not found on the system path."""
    pass


class MediaExtractionError(RuntimeError):
    """Raised when ffmpeg / ffprobe command fails on a media file."""
    pass


def check_ffmpeg_available() -> Tuple[bool, bool, Optional[str]]:
    """
    Checks whether ffmpeg and ffprobe CLI tools are available.
    
    Returns:
        (ffmpeg_installed, ffprobe_installed, error_message_if_any)
    """
    try:
        import static_ffmpeg
        static_ffmpeg.add_paths()
    except Exception:
        pass

    ffmpeg_path = shutil.which("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")

    ffmpeg_ok = ffmpeg_path is not None
    ffprobe_ok = ffprobe_path is not None

    if not ffmpeg_ok or not ffprobe_ok:
        missing = []
        if not ffmpeg_ok:
            missing.append("ffmpeg")
        if not ffprobe_ok:
            missing.append("ffprobe")
        msg = f"Required media tools missing from system PATH: {', '.join(missing)}. Please install FFmpeg."
        return ffmpeg_ok, ffprobe_ok, msg

    return True, True, None


def ensure_ffmpeg_installed() -> None:
    """Raises FFmpegUnavailableError if ffmpeg or ffprobe are not available."""
    ffmpeg_ok, ffprobe_ok, err_msg = check_ffmpeg_available()
    if not (ffmpeg_ok and ffprobe_ok):
        logger.error(f"FFmpeg check failed: {err_msg}")
        raise FFmpegUnavailableError(err_msg or "FFmpeg/FFprobe binaries not found")


def get_media_metadata_ffprobe(video_path: Path) -> Dict[str, Any]:
    """
    Safely executes ffprobe using argument lists to retrieve media stream and format metadata.
    
    Args:
        video_path: Path to the target video file.
        
    Returns:
        Dictionary parsed from ffprobe's JSON output.
    """
    ensure_ffmpeg_installed()

    if not video_path.is_file():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    # Explicit argument list — never shell=True
    cmd = [
        "ffprobe",
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(video_path.resolve())
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
            check=False
        )
    except subprocess.TimeoutExpired as e:
        logger.error(f"ffprobe timed out analyzing {video_path}")
        raise MediaExtractionError("ffprobe execution timed out") from e
    except Exception as e:
        logger.error(f"Failed to execute ffprobe: {str(e)}")
        raise MediaExtractionError(f"ffprobe execution failed: {str(e)}") from e

    if result.returncode != 0:
        err_detail = result.stderr.strip() or "Unknown ffprobe error"
        logger.warning(f"ffprobe failed on {video_path.name}: {err_detail}")
        raise MediaExtractionError(f"Corrupt or invalid media file: {err_detail}")

    try:
        data = json.loads(result.stdout)
        return data
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse ffprobe JSON output: {result.stdout}")
        raise MediaExtractionError("Failed to parse media metadata from ffprobe") from e


def extract_audio_ffmpeg(video_path: Path, output_audio_path: Path, sample_rate_hz: int = 16000) -> bool:
    """
    Safely extracts audio track from video to a mono 16kHz WAV format (optimal for audio/speech models).
    
    Args:
        video_path: Path to the video file.
        output_audio_path: Path to save the extracted WAV audio.
        sample_rate_hz: Target sampling rate (default: 16000 Hz for Whisper / speech models).
        
    Returns:
        True if audio was successfully extracted, False otherwise.
    """
    ensure_ffmpeg_installed()

    output_audio_path.parent.mkdir(parents=True, exist_ok=True)

    # Arguments: -vn (disable video), -acodec pcm_s16le (standard uncompressed PCM),
    # -ar 16000 (16kHz), -ac 1 (mono), -y (overwrite)
    cmd = [
        "ffmpeg",
        "-v", "error",
        "-y",
        "-i", str(video_path.resolve()),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", str(sample_rate_hz),
        "-ac", "1",
        str(output_audio_path.resolve())
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
            check=False
        )
        if result.returncode != 0:
            logger.warning(f"ffmpeg audio extraction warning/error: {result.stderr.strip()}")
            return False
        return output_audio_path.is_file() and output_audio_path.stat().st_size > 0
    except Exception as e:
        logger.error(f"Error during ffmpeg audio extraction: {str(e)}")
        return False
