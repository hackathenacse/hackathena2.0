from pathlib import Path
from typing import List, Optional

from app.core.logging import logger
from app.schemas.analysis import AudioResult, SpeechResult, VideoInfo, VisualResult
from .base import AudioDetector, FrameSample, SpeechToText, VisualDetector


class PlaceholderVisualDetector(VisualDetector):
    """
    Stage 1 Placeholder for Member 2's Visual AI Deepfake Detector.
    Returns status='unavailable' with available=False and zeroed/empty results.
    Never fabricates detection scores.
    """

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name

    async def analyze(
        self,
        frames: List[FrameSample],
        video_info: VideoInfo
    ) -> VisualResult:
        logger.info(
            f"VisualDetector: Member 2 detector not yet active. "
            f"Extracted {len(frames)} frames ready for visual model integration."
        )
        return VisualResult(
            available=False,
            model=self.model_name,
            status="unavailable",
            frames_analyzed=0,
            faces_found=0,
            face_detection_rate=None,
            results=[]
        )


class PlaceholderAudioDetector(AudioDetector):
    """
    Stage 1 Placeholder for Member 3's Audio / Voice Spoofing Detector.
    Returns status='unavailable' with available=False and empty results.
    Never fabricates spoofing scores.
    """

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name

    async def analyze(
        self,
        audio_path: Optional[Path],
        video_info: Optional[VideoInfo] = None
    ) -> AudioResult:
        audio_available = video_info.audio_available if video_info is not None else True
        if not audio_available or audio_path is None:
            logger.info("AudioDetector: No audio track present in media file.")
            return AudioResult(
                available=False,
                model=self.model_name,
                status="unavailable",
                results=[]
            )

        logger.info(
            f"AudioDetector: Member 3 audio detector not yet active. "
            f"Extracted audio track at {audio_path} ready for model integration."
        )
        return AudioResult(
            available=False,
            model=self.model_name,
            status="unavailable",
            results=[]
        )


class PlaceholderSpeechToText(SpeechToText):
    """
    Stage 1 Placeholder for Member 3's Speech Transcription module.
    Returns status='unavailable' with available=False and empty segments.
    Never fabricates transcriptions.
    """

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name

    async def transcribe(
        self,
        audio_path: Optional[Path],
        video_info: Optional[VideoInfo] = None
    ) -> SpeechResult:
        audio_available = video_info.audio_available if video_info is not None else True
        if not audio_available or audio_path is None:
            logger.info("SpeechToText: No audio track present in media file.")
            return SpeechResult(
                available=False,
                model=self.model_name,
                status="unavailable",
                segments=[]
            )

        logger.info(
            f"SpeechToText: Member 3 speech transcription not yet active. "
            f"Extracted audio track at {audio_path} ready for Whisper/transcription model."
        )
        return SpeechResult(
            available=False,
            model=self.model_name,
            status="unavailable",
            segments=[]
        )
