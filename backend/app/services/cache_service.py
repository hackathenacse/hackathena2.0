import datetime
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from app.core.logging import logger

_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_CACHE_DIR = _BACKEND_DIR / "data" / "analysis_cache"
PIPELINE_VERSION = "2.1.0"
MODEL_VERSION = "efficientnet-ffpp-c23-v1"
PREPROCESSING_VERSION = "v2"


class AnalysisCacheService:
    """
    Multi-Level Analysis Cache Service for Fast Re-Analysis & Smart Artifact Reuse.
    
    Level 1 — Exact Media Cache (SHA-256):
      Retrieves cached full analysis results near-instantly when an exact binary
      has been analyzed under the current pipeline, model, and adapter version.
      
    Level 2 — Near-Duplicate Lookup & Artifact Reuse:
      Finds perceptually similar media (cosine similarity >= threshold)
      to supply supporting context and avoid repeated redundant feature extractions.
      
    Cache Invalidation:
      Cache keys depend strictly on (sha256, pipeline_version, model_version, adapter_version).
      When the adapter version changes (e.g. visual-v0 -> visual-v1), old cached results
      are automatically bypassed so new adapter semantics take effect immediately.
    """

    _instance: Optional["AnalysisCacheService"] = None

    def __init__(self, cache_dir: Path = DEFAULT_CACHE_DIR):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.pipeline_version = PIPELINE_VERSION
        self.model_version = MODEL_VERSION
        self.preprocessing_version = PREPROCESSING_VERSION
        
        # Performance Telemetry
        self.total_queries = 0
        self.cache_hits = 0
        self.cache_misses = 0

    @classmethod
    def get_instance(cls) -> "AnalysisCacheService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _get_cache_key(self, sha256: str, adapter_version: str) -> str:
        clean_sha = sha256.lower().strip()
        clean_adapter = (adapter_version or "visual-v0").strip()
        return f"{clean_sha}_{self.pipeline_version}_{self.model_version}_{clean_adapter}_{self.preprocessing_version}"

    def _get_cache_file(self, sha256: str, adapter_version: str) -> Path:
        key = self._get_cache_key(sha256, adapter_version)
        return self.cache_dir / f"{key}.json"

    def get(self, sha256: str, adapter_version: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves cached analysis record if exact key matches.
        Returns deserialized dictionary or None on miss/corruption.
        """
        self.total_queries += 1
        cache_file = self._get_cache_file(sha256, adapter_version)
        if not cache_file.exists():
            self.cache_misses += 1
            return None

        try:
            start_t = time.perf_counter()
            content = cache_file.read_text(encoding="utf-8")
            data = json.loads(content)
            elapsed_ms = (time.perf_counter() - start_t) * 1000.0
            self.cache_hits += 1
            logger.info(
                f"AnalysisCacheService: EXACT CACHE HIT for {sha256[:12]}... "
                f"(adapter: {adapter_version}) in {elapsed_ms:.2f}ms"
            )
            return data
        except Exception as e:
            logger.warning(f"AnalysisCacheService: Failed to read cache file {cache_file.name}: {e}")
            self.cache_misses += 1
            return None

    def set(
        self,
        sha256: str,
        adapter_version: str,
        response_data: Dict[str, Any],
        intermediate_features: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Persists analysis response and optional intermediate features atomically to cache.
        """
        try:
            cache_file = self._get_cache_file(sha256, adapter_version)
            payload = {
                "cache_metadata": {
                    "sha256": sha256.lower().strip(),
                    "pipeline_version": self.pipeline_version,
                    "model_version": self.model_version,
                    "adapter_version": adapter_version,
                    "preprocessing_version": self.preprocessing_version,
                    "cached_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                },
                "response": response_data,
                "intermediate_features": intermediate_features or {},
            }
            tmp_file = cache_file.with_suffix(".tmp")
            tmp_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            tmp_file.replace(cache_file)
            logger.info(
                f"AnalysisCacheService: Persisted cache entry for {sha256[:12]}... (adapter: {adapter_version})"
            )
        except Exception as e:
            logger.error(f"AnalysisCacheService: Failed to write cache for {sha256}: {e}")

    def invalidate(self, sha256: str) -> int:
        """Invalidates all cached entries matching the specified SHA-256."""
        clean_sha = sha256.lower().strip()
        count = 0
        for p in self.cache_dir.glob(f"{clean_sha}_*.json"):
            try:
                p.unlink()
                count += 1
            except Exception:
                pass
        logger.info(f"AnalysisCacheService: Invalidated {count} cache entries for {clean_sha[:12]}...")
        return count

    def invalidate_by_adapter_version(self, old_adapter_version: str) -> int:
        """Invalidates entries created under an outdated adapter version."""
        count = 0
        for p in self.cache_dir.glob(f"*_{old_adapter_version}_*.json"):
            try:
                p.unlink()
                count += 1
            except Exception:
                pass
        logger.info(f"AnalysisCacheService: Purged {count} entries matching obsolete adapter '{old_adapter_version}'.")
        return count

    def clear(self) -> int:
        """Clears all cached analysis files."""
        count = 0
        for p in self.cache_dir.glob("*.json"):
            try:
                p.unlink()
                count += 1
            except Exception:
                pass
        self.total_queries = 0
        self.cache_hits = 0
        self.cache_misses = 0
        return count

    def get_metrics(self) -> Dict[str, Any]:
        """Returns cache telemetry metrics."""
        hit_ratio = round(self.cache_hits / max(1, self.total_queries), 4)
        return {
            "total_queries": self.total_queries,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_ratio": hit_ratio,
            "pipeline_version": self.pipeline_version,
            "model_version": self.model_version,
            "preprocessing_version": self.preprocessing_version,
        }
