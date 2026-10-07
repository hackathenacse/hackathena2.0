from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.schemas.analysis import AudioResult, SpeechResult, VideoInfo, VisualResult


class FrameSample:
    """Represents an extracted frame sample with its timestamp and local filesystem path."""
    def __init__(self, timestamp_s: float, frame_path: Path):
        self.timestamp_s = timestamp_s
        self.frame_path = frame_path

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp_s": self.timestamp_s,
            "frame_path": str(self.frame_path)
        }


class VisualDetector(ABC):
    """
    Interface for Member 2's Visual AI Deepfake Detector.
    Responsible for analyzing extracted video frames for face manipulation, blending artifacts, etc.
    """

    @abstractmethod
    async def analyze(
        self,
        frames: List[FrameSample],
        video_info: VideoInfo
    ) -> VisualResult:
        """
        Runs visual / face manipulation detection across sampled frames.
        
        Args:
            frames: List of FrameSample objects containing timestamp_s and frame_path.
            video_info: Video metadata (dimensions, fps, duration).
            
        Returns:
            VisualResult matching the Stage 1 data contract.
        """
        pass


class AudioDetector(ABC):
    """
    Interface for Member 3's Audio / Voice Spoofing Detector.
    Responsible for analyzing audio streams for synthetic speech, cloning, or spoofing artifacts.
    """

    @abstractmethod
    async def analyze(
        self,
        audio_path: Optional[Path],
        video_info: Optional[VideoInfo] = None
    ) -> AudioResult:
        """
        Runs voice spoofing and deepfake audio detection.
        
        Args:
            audio_path: Path to extracted 16kHz mono WAV file (or None if no audio stream).
            video_info: Video metadata (or None for audio-only media).
            
        Returns:
            AudioResult matching the Stage 1 data contract.
        """
        pass


class SpeechToText(ABC):
    """
    Interface for Member 3's Speech Transcription module.
    Responsible for generating timestamped text transcripts from audio.
    """

    @abstractmethod
    async def transcribe(
        self,
        audio_path: Optional[Path],
        video_info: Optional[VideoInfo] = None
    ) -> SpeechResult:
        """
        Transcribes speech audio into timestamped text segments.
        
        Args:
            audio_path: Path to extracted 16kHz mono WAV file (or None if no audio stream).
            video_info: Video metadata (or None for audio-only media).
            
        Returns:
            SpeechResult matching the Stage 1 data contract.
        """
        pass
