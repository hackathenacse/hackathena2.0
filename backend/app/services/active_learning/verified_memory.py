import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from app.core.logging import logger
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_REGISTRY_PATH = _BACKEND_DIR / "data" / "verified_media_registry.json"

class VerifiedMediaRegistry:
    """
    Dual-layer verified media memory system:
    1. Exact Binary Matching (SHA-256):
       Identifies exact repeat uploads of human-verified files and remembers
       the certified ground truth.
    2. Near-Duplicate Perceptual/Feature Matching (Cosine Similarity):
       Detects WhatsApp re-encodings, rescalings, or bitrate variations
       and supplies supporting evidence without automatically overriding forensic verdicts.
    """

    _instance: Optional["VerifiedMediaRegistry"] = None

    def __init__(self, registry_path: Path = DEFAULT_REGISTRY_PATH):
        self.registry_path = registry_path
        self._entries: Dict[str, Dict[str, Any]] = {}
        self.load()

    @classmethod
    def get_instance(cls) -> "VerifiedMediaRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load(self) -> None:
        if self.registry_path.exists():
            try:
                data = json.loads(self.registry_path.read_text(encoding="utf-8"))
                self._entries = data.get("entries", {})
                logger.info(f"VerifiedMediaRegistry: Loaded {len(self._entries)} verified records.")
            except Exception as e:
                logger.warning(f"Failed to read verified media registry: {e}. Starting fresh.")
                self._entries = {}
        else:
            self._entries = {}

    def save(self) -> None:
        try:
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "version": "1.0",
                "count": len(self._entries),
                "entries": self._entries
            }
            self.registry_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save verified media registry: {e}")

    def register(
        self,
        sha256: str,
        filename: str,
        ground_truth_media: str,
        ground_truth_fraud: str,
        embedding: Optional[List[float]] = None,
        notes: str = "",
        analyst_id: str = "analyst"
    ) -> Dict[str, Any]:
        """Registers a verified human-confirmed ground truth entry."""
        sha256 = sha256.lower().strip()
        entry = {
            "sha256": sha256,
            "filename": filename,
            "ground_truth_media": ground_truth_media,  # REAL or FAKE
            "ground_truth_fraud": ground_truth_fraud,  # HARMLESS or SCAM
            "embedding": embedding,
            "notes": notes,
            "analyst_id": analyst_id,
        }
        self._entries[sha256] = entry
        self.save()
        logger.info(f"VerifiedMediaRegistry: Registered SHA-256 {sha256[:12]}... as {ground_truth_media}")
        return entry

    def lookup_exact_sha256(self, sha256: str) -> Optional[Dict[str, Any]]:
        """Exact binary lookup by SHA-256."""
        sha256 = sha256.lower().strip()
        return self._entries.get(sha256)

    def lookup_near_duplicate(
        self,
        query_embedding: List[float],
        similarity_threshold: float = 0.95
    ) -> Optional[Dict[str, Any]]:
        """
        Calculates cosine similarity against registered feature representations.
        Returns near-duplicate evidence if similarity >= similarity_threshold.
        """
        if not query_embedding or not self._entries:
            return None

        q_vec = np.array(query_embedding, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm < 1e-6:
            return None
        q_vec = q_vec / q_norm

        best_sim = -1.0
        best_match = None

        for sha, record in self._entries.items():
            emb = record.get("embedding")
            if not emb:
                continue
            r_vec = np.array(emb, dtype=np.float32)
            r_norm = np.linalg.norm(r_vec)
            if r_norm < 1e-6:
                continue
            r_vec = r_vec / r_norm

            sim = float(np.dot(q_vec, r_vec))
            if sim > best_sim:
                best_sim = sim
                best_match = record

        if best_match and best_sim >= similarity_threshold:
            return {
                "matched_sha256": best_match["sha256"],
                "filename": best_match["filename"],
                "similarity": round(best_sim, 4),
                "ground_truth_media": best_match["ground_truth_media"],
                "ground_truth_fraud": best_match["ground_truth_fraud"],
                "threshold": similarity_threshold
            }

        return None

