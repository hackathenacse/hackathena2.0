import os
from pathlib import Path
from typing import List, Optional, Set
from pydantic_settings import BaseSettings, SettingsConfigDict

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")


class Settings(BaseSettings):
    PROJECT_NAME: str = "Authentica Backend"
    VERSION: str = "2.0.0"
    API_V1_STR: str = "/api"
    
    # Stage 1: Validation settings (configurable via environment variables)
    MAX_FILE_SIZE_MB: int = 100
    MAX_DURATION_SECONDS: float = 90.0
    
    ALLOWED_EXTENSIONS: Set[str] = {
        ".mp4", ".avi", ".mov", ".mkv", ".webm",
        ".wav", ".mp3", ".m4a", ".flac", ".ogg", ".aac", ".wma"
    }
    ALLOWED_MIME_TYPES: Set[str] = {
        "video/mp4",
        "video/x-msvideo",
        "video/quicktime",
        "video/x-matroska",
        "video/webm",
        "audio/wav",
        "audio/x-wav",
        "audio/wave",
        "audio/mpeg",
        "audio/mp3",
        "audio/mp4",
        "audio/x-m4a",
        "audio/m4a",
        "audio/flac",
        "audio/x-flac",
        "audio/ogg",
        "audio/vorbis",
        "audio/aac",
        "audio/x-aac",
        "audio/webm",
        "application/octet-stream",
    }
    
    # Video sampling settings (Adaptive sampling strategy for robust temporal forensics)
    FRAME_SAMPLE_FPS: float = 1.0  # Base sampling rate
    ADAPTIVE_SAMPLING_ENABLED: bool = True
    SHORT_VIDEO_FPS: float = 3.0   # Higher density for clips < 5.0s (ensures >= 8-15 frame samples)
    MEDIUM_VIDEO_FPS: float = 1.5  # Moderate density for clips 5.0s - 12.0s
    STANDARD_VIDEO_FPS: float = 1.0 # Standard density for longer clips >= 12.0s
    MAX_SAMPLED_FRAMES: int = 60   # Computational guardrail cap for max frames evaluated per clip
    
    # Stage 2: Reliability Gate Thresholds
    RELIABILITY_MIN_WIDTH: int = 360
    RELIABILITY_MIN_HEIGHT: int = 360
    MIN_FACE_DETECTION_RATE: float = 0.30
    MIN_AUDIO_DURATION: float = 3.0
    MIN_VISUAL_OBSERVATIONS: int = 5
    MIN_VIDEO_DURATION: float = 4.0
    
    # Stage 2: Evidence Level Prototype Thresholds
    # Prototype thresholds subject to calibration on team evaluation benchmarks
    VISUAL_LOW_THRESHOLD: float = 0.30
    VISUAL_HIGH_THRESHOLD: float = 0.70
    AUDIO_LOW_THRESHOLD: float = 0.30
    AUDIO_HIGH_THRESHOLD: float = 0.70
    
    # Stage 2: Timeline Aggregation Settings
    TIMELINE_WINDOW_DURATION_S: float = 3.0
    
    # Stage 2: Trusted C2PA Signers List
    TRUSTED_C2PA_SIGNERS: List[str] = [
        "Adobe", "Truepic", "BBC", "Sony", "Nikon", "Leica", "Microsoft", "C2PA Test Signer"
    ]
    
    # MongoDB Atlas Database
    MONGODB_URI: Optional[str] = None
    MONGODB_DB_NAME: str = "authentica"

    # Temporary workspace root directory
    TEMP_DIR: Path = Path(__file__).resolve().parent.parent.parent / "temp"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024


settings = Settings()

# Ensure base temp directory exists
settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)
