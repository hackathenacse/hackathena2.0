from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple
import subprocess
import cv2

from app.core.config import settings
from app.core.logging import logger
from app.services.detectors.base import FrameSample
from app.utils.ffmpeg import (
    MediaExtractionError,
    extract_audio_ffmpeg,
    get_media_metadata_ffprobe,
)


class VideoProcessingError(Exception):
    """Base exception for video processing failures."""
    pass


class CorruptedVideoError(VideoProcessingError):
    """Raised when the uploaded media cannot be opened or decoded."""
    pass


class VideoDurationExceededError(VideoProcessingError):
    """Raised when the video duration exceeds the configured maximum limit."""
    pass


@dataclass
class VideoProcessingResult:
    """Raw processing and extraction results produced by VideoProcessor."""
    duration_s: float
    fps: float
    width: int
    height: int
    frame_count: int
    frames_sampled: int
    audio_available: bool
    frame_samples: List[FrameSample]
    audio_path: Optional[Path] = None

    def to_metadata_dict(self) -> dict:
        return {
            "duration_s": self.duration_s,
            "fps": self.fps,
            "width": self.width,
            "height": self.height,
            "frames_sampled": self.frames_sampled,
            "audio_available": self.audio_available,
        }


@dataclass
class AudioProcessingResult:
    """Raw processing and extraction results produced for standalone audio."""
    duration_s: float
    sample_rate_hz: Optional[int]
    channels: Optional[int]
    codec: Optional[str]
    bitrate_kbps: Optional[float]
    mime_type: Optional[str]
    audio_path: Path


class VideoProcessor:
    """
    Core media inspection, video frame sampling, audio extraction, and audio-only processing service.
    Implements real media processing using OpenCV and FFmpeg/FFprobe.
    """

    def __init__(
        self,
        max_duration_s: float = settings.MAX_DURATION_SECONDS,
        sample_fps: float = settings.FRAME_SAMPLE_FPS
    ):
        self.max_duration_s = max_duration_s
        self.sample_fps = sample_fps

    def process(
        self,
        video_path: Path,
        frames_dir: Path,
        audio_dir: Path
    ) -> VideoProcessingResult:
        """
        Validates, extracts metadata, samples frames (~1 FPS), and prepares audio.
        
        Args:
            video_path: Path to the local video file.
            frames_dir: Directory where sampled frame images will be written.
            audio_dir: Directory where extracted WAV audio will be written.
            
        Returns:
            VideoProcessingResult with full metadata and artifact paths.
        """
        logger.info(f"Starting video processing for: {video_path.name}")

        # 1. Inspect container & streams with ffprobe
        has_video_stream, has_audio_stream, ffprobe_duration, ffprobe_fps, ffprobe_dims = (
            self._probe_media_streams(video_path)
        )

        if not has_video_stream:
            raise CorruptedVideoError("No valid video stream detected in uploaded file.")

        # 2. Open video stream using OpenCV
        cap = cv2.VideoCapture(str(video_path.resolve()))
        if not cap.isOpened():
            raise CorruptedVideoError("Failed to open video file with OpenCV decoder.")

        try:
            cv_frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cv_fps = float(cap.get(cv2.CAP_PROP_FPS))
            cv_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            cv_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            # Combine ffprobe and OpenCV metadata for maximum accuracy
            width = cv_width if cv_width > 0 else (ffprobe_dims[0] if ffprobe_dims else 0)
            height = cv_height if cv_height > 0 else (ffprobe_dims[1] if ffprobe_dims else 0)
            fps = cv_fps if cv_fps > 0 else (ffprobe_fps or 30.0)

            if cv_frame_count > 0 and fps > 0:
                duration_s = cv_frame_count / fps
            elif ffprobe_duration is not None and ffprobe_duration > 0:
                duration_s = ffprobe_duration
            else:
                duration_s = 0.0

            if ffprobe_duration is not None and ffprobe_duration > 0:
                duration_s = ffprobe_duration

            # Stream-recorded containers (e.g. Chrome MediaRecorder WebM) omit duration from EBML header.
            # Perform fast stream-copy remux with FFmpeg to populate container duration and seek index.
            if duration_s <= 0.0 or cv_frame_count <= 0:
                remuxed_path = video_path.parent / f"remux_{video_path.name}"
                cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(video_path.resolve()), "-c", "copy", str(remuxed_path.resolve())]
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if res.returncode == 0 and remuxed_path.exists() and remuxed_path.stat().st_size > 0:
                    logger.info(f"Stream-recorded media successfully finalized with FFmpeg: {remuxed_path.name}")
                    video_path = remuxed_path
                    has_video_stream, has_audio_stream, ffprobe_duration, ffprobe_fps, ffprobe_dims = (
                        self._probe_media_streams(video_path)
                    )
                    cap.release()
                    cap = cv2.VideoCapture(str(video_path.resolve()))
                    cv_frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    cv_fps = float(cap.get(cv2.CAP_PROP_FPS))
                    cv_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    cv_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    width = cv_width if cv_width > 0 else (ffprobe_dims[0] if ffprobe_dims else width)
                    height = cv_height if cv_height > 0 else (ffprobe_dims[1] if ffprobe_dims else height)
                    fps = cv_fps if cv_fps > 0 else (ffprobe_fps or fps or 30.0)
                    if ffprobe_duration is not None and ffprobe_duration > 0:
                        duration_s = ffprobe_duration
                    elif cv_frame_count > 0 and fps > 0:
                        duration_s = cv_frame_count / fps

            # If duration or frame count is still unavailable, decode frames to establish true count and duration
            if duration_s <= 0.0 or cv_frame_count <= 0:
                logger.info(f"Duration unavailable from headers; performing decoder frame count fallback on {video_path.name}")
                counted_frames = 0
                while True:
                    ret, _ = cap.read()
                    if not ret:
                        break
                    counted_frames += 1

                if counted_frames > 0:
                    cv_frame_count = counted_frames
                    duration_s = cv_frame_count / fps if fps > 0 else 0.0
                    logger.info(f"Decoder fallback recovered {cv_frame_count} frames, duration: {duration_s:.2f}s")
                    # Reopen VideoCapture for subsequent sampling
                    cap.release()
                    cap = cv2.VideoCapture(str(video_path.resolve()))

            if width <= 0 or height <= 0:
                raise CorruptedVideoError("Invalid video dimensions (0x0). Video may be corrupted.")

            # 3. Determine adaptive sampling rate based on video duration
            if settings.ADAPTIVE_SAMPLING_ENABLED:
                if duration_s > 0 and duration_s < 5.0:
                    effective_sample_fps = settings.SHORT_VIDEO_FPS
                elif duration_s >= 5.0 and duration_s < 12.0:
                    effective_sample_fps = settings.MEDIUM_VIDEO_FPS
                else:
                    effective_sample_fps = settings.STANDARD_VIDEO_FPS
            else:
                effective_sample_fps = self.sample_fps

            # Sample frames adaptively
            frame_samples = self._sample_frames(
                cap=cap,
                fps=fps,
                total_frames=cv_frame_count,
                frames_dir=frames_dir,
                target_sample_fps=effective_sample_fps
            )

            if not frame_samples:
                raise CorruptedVideoError("Failed to extract any readable frames from video stream.")

            # If duration could not be extracted from header, calculate from sampled frames
            if duration_s <= 0.0 and frame_samples:
                duration_s = frame_samples[-1].timestamp_s + (1.0 / fps if fps > 0 else 1.0)

            # Validate maximum duration
            if duration_s > self.max_duration_s:
                raise VideoDurationExceededError(
                    f"Video duration ({duration_s:.1f}s) exceeds maximum allowed limit of {self.max_duration_s:.1f}s."
                )

            logger.info(
                f"Video inspection: {width}x{height} @ {fps:.2f} FPS | "
                f"Duration: {duration_s:.2f}s | Audio stream: {has_audio_stream}"
            )
            logger.info(f"Extracted {len(frame_samples)} frame samples at ~{effective_sample_fps:.1f} FPS (adaptive).")

        finally:
            cap.release()

        # 4. Extract audio if audio stream is present
        extracted_audio_path: Optional[Path] = None
        if has_audio_stream:
            target_wav = audio_dir / "audio.wav"
            success = extract_audio_ffmpeg(video_path, target_wav, sample_rate_hz=16000)
            if success:
                extracted_audio_path = target_wav
                logger.info(f"Audio extracted successfully to {target_wav}")
            else:
                logger.warning("Audio stream was detected by ffprobe, but ffmpeg extraction failed.")
                has_audio_stream = False

        return VideoProcessingResult(
            duration_s=round(duration_s, 2),
            fps=round(fps, 2),
            width=width,
            height=height,
            frame_count=cv_frame_count if cv_frame_count > 0 else len(frame_samples),
            frames_sampled=len(frame_samples),
            audio_available=has_audio_stream,
            frame_samples=frame_samples,
            audio_path=extracted_audio_path
        )

    def _probe_media_streams(
        self,
        video_path: Path
    ) -> Tuple[bool, bool, Optional[float], Optional[float], Optional[Tuple[int, int]]]:
        """Runs ffprobe to inspect container streams and formats."""
        try:
            probe_data = get_media_metadata_ffprobe(video_path)
        except MediaExtractionError as e:
            logger.warning(f"ffprobe metadata extraction failed: {e}")
            raise CorruptedVideoError(f"Media inspection failed: {str(e)}") from e

        streams = probe_data.get("streams", [])
        has_video = False
        has_audio = False
        duration_s: Optional[float] = None
        fps: Optional[float] = None
        dims: Optional[Tuple[int, int]] = None

        # Check format level duration
        fmt = probe_data.get("format", {})
        if "duration" in fmt:
            try:
                duration_s = float(fmt["duration"])
            except (ValueError, TypeError):
                pass

        for st in streams:
            codec_type = st.get("codec_type")
            if codec_type == "video" and not has_video:
                has_video = True
                w = st.get("width")
                h = st.get("height")
                if w and h:
                    dims = (int(w), int(h))
                
                # Parse r_frame_rate or avg_frame_rate e.g. "30/1" or "29.97"
                rate_str = st.get("avg_frame_rate") or st.get("r_frame_rate")
                if rate_str and "/" in rate_str:
                    num, den = rate_str.split("/", 1)
                    try:
                        num_f, den_f = float(num), float(den)
                        if den_f > 0:
                            fps = num_f / den_f
                    except (ValueError, ZeroDivisionError):
                        pass

            elif codec_type == "audio":
                has_audio = True

        return has_video, has_audio, duration_s, fps, dims

    def _sample_frames(
        self,
        cap: cv2.VideoCapture,
        fps: float,
        total_frames: int,
        frames_dir: Path,
        target_sample_fps: Optional[float] = None
    ) -> List[FrameSample]:
        """
        Samples frames at target_sample_fps (or self.sample_fps) and writes them to frames_dir.
        Preserves timestamps accurately with MAX_SAMPLED_FRAMES computational safety limit.
        """
        samples: List[FrameSample] = []
        eff_fps = target_sample_fps or self.sample_fps
        frame_interval = max(1, round(fps / eff_fps))
        max_samples = getattr(settings, "MAX_SAMPLED_FRAMES", 60)

        frame_idx = 0
        sample_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % frame_interval == 0:
                # Timestamp in seconds
                pos_msec = cap.get(cv2.CAP_PROP_POS_MSEC)
                if pos_msec > 0:
                    timestamp_s = pos_msec / 1000.0
                else:
                    timestamp_s = frame_idx / fps if fps > 0 else float(sample_count)

                frame_filename = f"frame_{sample_count:04d}_{int(timestamp_s * 1000):06d}ms.jpg"
                frame_path = frames_dir / frame_filename

                # Save frame image locally
                write_ok = cv2.imwrite(str(frame_path.resolve()), frame)
                if write_ok:
                    samples.append(FrameSample(
                        timestamp_s=round(timestamp_s, 3),
                        frame_path=frame_path
                    ))
                    sample_count += 1
                else:
                    logger.warning(f"Failed to write frame to {frame_path}")

                if sample_count >= max_samples:
                    logger.info(f"Reached maximum frame sample limit ({max_samples}). Halting sampling.")
                    break

            frame_idx += 1

        return samples

    def probe_media_type(
        self,
        media_path: Path
    ) -> Tuple[str, dict]:
        """
        Inspects container streams using ffprobe to classify media as 'VIDEO' or 'AUDIO'.
        
        Returns:
            Tuple of (media_type, ffprobe_metadata) where media_type is 'VIDEO' or 'AUDIO'.
        """
        try:
            probe_data = get_media_metadata_ffprobe(media_path)
        except MediaExtractionError as e:
            logger.warning(f"ffprobe metadata extraction failed: {e}")
            raise CorruptedVideoError(f"Media inspection failed: {str(e)}") from e

        streams = probe_data.get("streams", [])
        has_video_stream = False
        has_audio_stream = False

        for st in streams:
            codec_type = st.get("codec_type")
            if codec_type == "video":
                # Exclude attached pictures (album art, poster images in MP3/FLAC/M4A)
                is_attached_pic = st.get("disposition", {}).get("attached_pic", 0) == 1
                w = st.get("width") or 0
                h = st.get("height") or 0
                if not is_attached_pic and (w > 0 or h > 0):
                    has_video_stream = True
            elif codec_type == "audio":
                has_audio_stream = True

        if has_video_stream:
            return "VIDEO", probe_data
        elif has_audio_stream:
            return "AUDIO", probe_data
        else:
            raise CorruptedVideoError("No valid video or audio stream detected in uploaded file.")

    def process_audio(
        self,
        audio_path: Path,
        audio_dir: Path
    ) -> AudioProcessingResult:
        """
        Extracts 16kHz mono WAV audio and metadata for standalone audio uploads.
        
        Args:
            audio_path: Path to the local uploaded audio file.
            audio_dir: Directory where extracted WAV audio will be written.
            
        Returns:
            AudioProcessingResult with metadata and local artifact path.
        """
        logger.info(f"Starting standalone audio processing for: {audio_path.name}")
        
        try:
            probe_data = get_media_metadata_ffprobe(audio_path)
        except MediaExtractionError as e:
            raise CorruptedVideoError(f"Audio inspection failed: {str(e)}") from e

        streams = probe_data.get("streams", [])
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
        if not audio_stream:
            raise CorruptedVideoError("No readable audio stream found in uploaded file.")

        # Extract format level or stream duration
        duration_s: Optional[float] = None
        fmt = probe_data.get("format", {})
        if "duration" in fmt:
            try:
                duration_s = float(fmt["duration"])
            except (ValueError, TypeError):
                pass

        if duration_s is None and "duration" in audio_stream:
            try:
                duration_s = float(audio_stream["duration"])
            except (ValueError, TypeError):
                pass

        sample_rate_hz: Optional[int] = None
        if "sample_rate" in audio_stream:
            try:
                sample_rate_hz = int(audio_stream["sample_rate"])
            except (ValueError, TypeError):
                pass

        channels: Optional[int] = audio_stream.get("channels")
        codec: Optional[str] = audio_stream.get("codec_name")
        
        bitrate_kbps: Optional[float] = None
        bit_rate_raw = fmt.get("bit_rate") or audio_stream.get("bit_rate")
        if bit_rate_raw:
            try:
                bitrate_kbps = round(float(bit_rate_raw) / 1000.0, 1)
            except (ValueError, TypeError):
                pass

        mime_type = fmt.get("format_name")

        target_wav = audio_dir / "audio.wav"
        success = extract_audio_ffmpeg(audio_path, target_wav, sample_rate_hz=16000)
        if not success or not target_wav.is_file() or target_wav.stat().st_size == 0:
            raise CorruptedVideoError("Failed to decode uploaded audio file into standard PCM WAV.")

        if duration_s is None or duration_s <= 0:
            # Fallback to soundfile header read on extracted wav
            try:
                import soundfile as sf
                info = sf.info(str(target_wav.resolve()))
                duration_s = info.duration
            except Exception:
                duration_s = 0.0

        if duration_s <= 0:
            raise CorruptedVideoError("Unable to determine audio length or track is empty.")

        if duration_s > self.max_duration_s:
            raise VideoDurationExceededError(
                f"Audio duration ({duration_s:.1f}s) exceeds maximum allowed limit of {self.max_duration_s:.1f}s."
            )

        logger.info(
            f"Audio inspection: codec={codec} | {sample_rate_hz}Hz | {channels}ch | "
            f"bitrate={bitrate_kbps}kbps | duration={duration_s:.2f}s"
        )

        return AudioProcessingResult(
            duration_s=round(duration_s, 2),
            sample_rate_hz=sample_rate_hz,
            channels=channels,
            codec=codec,
            bitrate_kbps=bitrate_kbps,
            mime_type=mime_type,
            audio_path=target_wav,
        )
