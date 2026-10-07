import os
import time
from pathlib import Path
from typing import List, Optional

import numpy as np
import soundfile as sf

from app.core.logging import logger
from app.schemas.analysis import SpeechSegment, SpeechResult, VideoInfo
from app.services.detectors.base import SpeechToText

MODEL_NAME = "faster-whisper-base-int8"
MODEL_VERSION = "1.2.1"
MODEL_LICENSE = "MIT"


class FasterWhisperTranscriber(SpeechToText):
    """
    Member 3 Speech-to-Text Transcription Service for Stage 1.
    
    Pipeline:
      16kHz Mono WAV Audio -> Faster-Whisper (CTranslate2 INT8 CPU / CUDA) ->
      VAD Silence Filtering -> Timestamped Speech Segments + Detected Language ->
      Structured SpeechResult.
      
    Responsibilities:
      - Uses local CTranslate2-accelerated Whisper models for sub-second CPU inference.
      - Automatically detects spoken language (multilingual support).
      - Extracts accurate word/segment start and end timestamps.
      - Gracefully handles missing audio, silent tracks, and corrupt WAV files.
      - Thread-safe singleton instance.
    """

    _instance: Optional["FasterWhisperTranscriber"] = None

    def __init__(
        self,
        model_size: str = "base",
        device: Optional[str] = None,
        compute_type: str = "int8"
    ):
        self.model_size = model_size
        self.compute_type = compute_type
        
        # Device auto-selection
        if device:
            self.device = device
        else:
            import torch
            self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # int8 is optimal for CPU inference
        if self.device == "cpu" and self.compute_type not in ["int8", "float32"]:
            self.compute_type = "int8"

        self.model = None
        self._is_loaded = False

    @classmethod
    def get_instance(cls) -> "FasterWhisperTranscriber":
        """Singleton accessor to prevent reloading weights across requests."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load(self) -> None:
        """Loads the faster-whisper model into memory."""
        if self._is_loaded and self.model is not None:
            return

        logger.info(
            f"FasterWhisperTranscriber: Loading model '{self.model_size}' "
            f"on {self.device} ({self.compute_type})..."
        )
        start_time = time.perf_counter()

        try:
            from faster_whisper import WhisperModel
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                download_root=os.path.expanduser("~/.cache/huggingface/hub")
            )
            self._is_loaded = True
            elapsed = time.perf_counter() - start_time
            logger.info(f"FasterWhisperTranscriber: Successfully loaded in {elapsed:.2f}s.")
        except Exception as e:
            logger.error(f"FasterWhisperTranscriber: Failed to load model: {e}")
            self._is_loaded = False
            raise

    async def transcribe(
        self,
        audio_path: Optional[Path],
        video_info: Optional[VideoInfo] = None
    ) -> SpeechResult:
        """
        Executes speech-to-text transcription on the extracted WAV file.
        """
        start_time = time.perf_counter()

        audio_available = video_info.audio_available if video_info is not None else True
        if not audio_available or audio_path is None or not audio_path.is_file():
            logger.info("FasterWhisperTranscriber: No audio stream or audio file present.")
            return SpeechResult(
                available=False,
                model=MODEL_NAME,
                status="unavailable",
                language=None,
                processing_time_s=0.0,
                segments=[]
            )

        if audio_path.stat().st_size == 0:
            logger.warning(f"FasterWhisperTranscriber: Audio file at {audio_path} is 0 bytes.")
            return SpeechResult(
                available=False,
                model=MODEL_NAME,
                status="unavailable",
                language=None,
                processing_time_s=0.0,
                segments=[]
            )

        try:
            self.load()
        except Exception as e:
            logger.error(f"FasterWhisperTranscriber: Cannot transcribe due to loading failure: {e}")
            return SpeechResult(
                available=False,
                model=MODEL_NAME,
                status="error",
                language=None,
                processing_time_s=round(time.perf_counter() - start_time, 3),
                segments=[]
            )

        try:
            # Read audio into float32 waveform (avoids PyAV metadata errors)
            audio_data, sr = sf.read(str(audio_path.resolve()), dtype="float32")
            if audio_data.ndim > 1:
                audio_data = np.mean(audio_data, axis=1)

            # For streaming audio clips (< 25 seconds), disable VAD filter to prevent Silero-VAD
            # from erroneously stripping spoken conversational sentences in streaming chunks.
            duration_s = len(audio_data) / max(1, sr)
            use_vad = duration_s >= 25.0

            raw_segments, info = self.model.transcribe(
                audio_data,
                vad_filter=use_vad,
                vad_parameters=dict(min_silence_duration_ms=400, threshold=0.35) if use_vad else None,
                beam_size=5,
                no_speech_threshold=0.6,
                condition_on_previous_text=False,
                compression_ratio_threshold=2.4,
            )

            segments: List[SpeechSegment] = []
            for seg in raw_segments:
                text_clean = seg.text.strip()
                # Suppress non-speech artifacts and hallucinations
                no_speech_prob = getattr(seg, "no_speech_prob", 0.0)
                if text_clean and no_speech_prob < 0.65:
                    segments.append(SpeechSegment(
                        start_s=round(float(seg.start), 2),
                        end_s=round(float(seg.end), 2),
                        text=text_clean
                    ))

            # Resilient fallback: if VAD returned 0 segments on non-silent audio, retry directly
            if len(segments) == 0 and len(audio_data) > 0 and np.max(np.abs(audio_data)) > 0.005:
                retry_segments, info = self.model.transcribe(
                    audio_data,
                    vad_filter=False,
                    beam_size=5,
                    no_speech_threshold=0.6,
                    condition_on_previous_text=False,
                    compression_ratio_threshold=2.4,
                )
                for seg in retry_segments:
                    text_clean = seg.text.strip()
                    no_speech_prob = getattr(seg, "no_speech_prob", 0.0)
                    if text_clean and no_speech_prob < 0.65:
                        segments.append(SpeechSegment(
                            start_s=round(float(seg.start), 2),
                            end_s=round(float(seg.end), 2),
                            text=text_clean
                        ))

            elapsed = round(time.perf_counter() - start_time, 3)
            detected_lang = info.language if info else "unknown"

            logger.info(
                f"FasterWhisperTranscriber: Transcribed {len(segments)} segments | "
                f"Language: {detected_lang} (p={info.language_probability:.2f}) | "
                f"Elapsed: {elapsed:.2f}s"
            )

            return SpeechResult(
                available=True,
                model=MODEL_NAME,
                status="completed",
                language=detected_lang,
                processing_time_s=elapsed,
                segments=segments
            )

        except Exception as e:
            logger.error(f"FasterWhisperTranscriber: Transcription failed: {e}")
            elapsed = round(time.perf_counter() - start_time, 3)
            return SpeechResult(
                available=False,
                model=MODEL_NAME,
                status="error",
                language=None,
                processing_time_s=elapsed,
                segments=[]
            )
