import shutil
import uuid
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.core.logging import logger


class TempWorkspace:
    """
    Manages an isolated temporary workspace for an individual analysis session.
    Ensures that uploaded media, sampled frames, and extracted audio files
    are strictly ephemeral and cleaned up immediately after processing.
    """

    def __init__(self, analysis_id: Optional[str] = None):
        self.analysis_id = analysis_id or str(uuid.uuid4())
        self.workspace_dir: Path = settings.TEMP_DIR / self.analysis_id
        self.frames_dir: Path = self.workspace_dir / "frames"
        self.audio_dir: Path = self.workspace_dir / "audio"
        self.video_dir: Path = self.workspace_dir / "video"

    def setup(self) -> "TempWorkspace":
        """Creates isolated workspace directories."""
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.frames_dir.mkdir(parents=True, exist_ok=True)
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.video_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created temporary workspace for analysis {self.analysis_id} at {self.workspace_dir}")
        return self

    def cleanup(self) -> None:
        """
        Safely removes all temporary files and directories associated with this analysis.
        Adheres to local-only privacy standards: zero retention of user media.
        """
        if self.workspace_dir.exists():
            try:
                shutil.rmtree(self.workspace_dir, ignore_errors=True)
                logger.info(f"Cleaned up temporary workspace for analysis {self.analysis_id}")
            except Exception as e:
                logger.warning(f"Failed to cleanly remove workspace {self.workspace_dir}: {e}")

    def __enter__(self) -> "TempWorkspace":
        return self.setup()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
