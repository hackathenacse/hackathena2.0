import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.logging import logger
from app.schemas.analysis import AnalysisResponse

try:
    from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
    MOTOR_AVAILABLE = True
except ImportError:
    MOTOR_AVAILABLE = False


class FeedbackPayload(BaseModel):
    ground_truth_media: str = Field(..., description="'REAL' | 'FAKE' | 'UNVERIFIED'")
    ground_truth_fraud: str = Field(..., description="'HARMLESS' | 'SCAM' | 'UNVERIFIED'")
    is_false_positive: bool = Field(default=False)
    is_false_negative: bool = Field(default=False)
    notes: Optional[str] = None
    analyst_id: Optional[str] = "analyst"


class DatabaseService:
    """
    Dual-layer storage engine:
      1. Primary: Asynchronous MongoDB Atlas (when MONGODB_URI is provided)
      2. Fallback: Local disk cache & JSON persistence (when offline or MONGODB_URI is None)
    """

    _client: Optional[Any] = None
    _db: Optional[Any] = None
    _is_connected: bool = False

    @classmethod
    async def connect(cls) -> bool:
        if not MOTOR_AVAILABLE or not settings.MONGODB_URI:
            logger.info("MongoDB: No MONGODB_URI configured. Running with local disk cache.")
            cls._is_connected = False
            return False

        try:
            motor_kwargs = {
                "serverSelectionTimeoutMS": 4000,
                "connectTimeoutMS": 4000,
            }
            try:
                import certifi
                motor_kwargs["tlsCAFile"] = certifi.where()
            except Exception:
                pass

            cls._client = AsyncIOMotorClient(
                settings.MONGODB_URI,
                **motor_kwargs,
            )
            # Verify connectivity
            await cls._client.admin.command("ping")
            cls._db = cls._client[settings.MONGODB_DB_NAME]
            cls._is_connected = True

            # Create search and index constraints
            analyses_col = cls._db["analyses"]
            await analyses_col.create_index("id", unique=True)
            await analyses_col.create_index("created_at")
            await analyses_col.create_index("input.sha256")

            feedback_col = cls._db["feedback_dataset"]
            await feedback_col.create_index("analysis_id", unique=True)
            await feedback_col.create_index("ground_truth_media")
            await feedback_col.create_index("ground_truth_fraud")

            logger.info("MongoDB Atlas: Successfully connected and initialized indexes.")
            return True
        except Exception as e:
            logger.warning(f"MongoDB Atlas: Could not connect ({e}). Falling back to local disk storage.")
            cls._is_connected = False
            return False

    @classmethod
    async def disconnect(cls):
        if cls._client:
            cls._client.close()
            cls._client = None
            cls._db = None
            cls._is_connected = False
            logger.info("MongoDB: Connection closed.")

    @classmethod
    def is_connected(cls) -> bool:
        return cls._is_connected

    # ==========================================
    # Local Disk Cache Helpers
    # ==========================================
    @classmethod
    def _get_disk_cache_dir(cls) -> Path:
        cache_dir = settings.TEMP_DIR / "analyses"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    @classmethod
    def _get_feedback_dir(cls) -> Path:
        fb_dir = settings.TEMP_DIR / "feedback"
        fb_dir.mkdir(parents=True, exist_ok=True)
        return fb_dir

    # ==========================================
    # Analysis Operations
    # ==========================================
    @classmethod
    async def save_analysis(cls, analysis: AnalysisResponse) -> None:
        """Saves analysis record to MongoDB and local disk backup."""
        doc = analysis.model_dump()

        # 1. Save to local disk backup
        try:
            cache_file = cls._get_disk_cache_dir() / f"{analysis.id}.json"
            cache_file.write_text(analysis.model_dump_json(indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Disk storage error for {analysis.id}: {e}")

        # 2. Save to MongoDB Atlas
        if cls._is_connected and cls._db is not None:
            try:
                await cls._db["analyses"].replace_one(
                    {"id": analysis.id},
                    doc,
                    upsert=True
                )
                logger.debug(f"MongoDB: Saved analysis '{analysis.id}'.")
            except Exception as e:
                logger.warning(f"MongoDB insert error for {analysis.id}: {e}")

    @classmethod
    async def get_analysis(cls, analysis_id: str) -> Optional[AnalysisResponse]:
        """Retrieves analysis report by ID from MongoDB or disk cache."""
        # Try MongoDB
        if cls._is_connected and cls._db is not None:
            try:
                doc = await cls._db["analyses"].find_one({"id": analysis_id}, {"_id": 0})
                if doc:
                    return AnalysisResponse.model_validate(doc)
            except Exception as e:
                logger.warning(f"MongoDB query error for {analysis_id}: {e}")

        # Fallback to local disk
        try:
            cache_file = cls._get_disk_cache_dir() / f"{analysis_id}.json"
            if cache_file.exists():
                return AnalysisResponse.model_validate_json(cache_file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"Disk read error for {analysis_id}: {e}")

        return None

    @classmethod
    async def list_analyses(cls, limit: int = 50, skip: int = 0, search: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves history list with search filtering."""
        results: List[Dict[str, Any]] = []

        if cls._is_connected and cls._db is not None:
            try:
                query = {}
                if search:
                    regex = {"$regex": search, "$options": "i"}
                    query = {
                        "$or": [
                            {"input.filename": regex},
                            {"input.sha256": regex},
                            {"assessment.action": regex},
                            {"assessment.media": regex},
                        ]
                    }

                cursor = cls._db["analyses"].find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit)
                async for item in cursor:
                    results.append(item)
                return results
            except Exception as e:
                logger.warning(f"MongoDB list query error: {e}")

        # Fallback: scan local disk
        try:
            cache_files = sorted(
                cls._get_disk_cache_dir().glob("*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            for f in cache_files[skip : skip + limit]:
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    if search:
                        fn = data.get("input", {}).get("filename", "")
                        sha = data.get("input", {}).get("sha256", "")
                        if search.lower() not in fn.lower() and search.lower() not in sha.lower():
                            continue
                    results.append(data)
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f"Disk history scan error: {e}")

        return results

    # ==========================================
    # Active Learning & Feedback Operations
    # ==========================================
    @classmethod
    async def record_feedback(cls, analysis_id: str, feedback: FeedbackPayload) -> Dict[str, Any]:
        """
        Stores verified human ground-truth feedback for an analysis.
        Adds sample into the curated active-learning training dataset buffer.
        """
        analysis = await cls.get_analysis(analysis_id)
        if not analysis:
            raise ValueError(f"Analysis with ID '{analysis_id}' does not exist.")

        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

        filename = analysis.video.filename if analysis.video else (analysis.audio_metadata.filename if analysis.audio_metadata else "media")
        sha256 = analysis.video.sha256 if analysis.video else (analysis.audio_metadata.sha256 if analysis.audio_metadata else "N/A")

        # Build training record
        training_sample = {
            "analysis_id": analysis_id,
            "filename": filename,
            "media_type": analysis.evidence.metadata.media_type,
            "sha256": sha256,
            "duration_s": analysis.evidence.metadata.duration_s,
            "predicted_media_verdict": analysis.assessment.media,
            "predicted_fraud_level": analysis.assessment.fraud,
            "predicted_action": analysis.assessment.action,
            "ground_truth_media": feedback.ground_truth_media,
            "ground_truth_fraud": feedback.ground_truth_fraud,
            "is_false_positive": feedback.is_false_positive,
            "is_false_negative": feedback.is_false_negative,
            "notes": feedback.notes or "",
            "analyst_id": feedback.analyst_id or "analyst",
            "verified_at": timestamp,
            "evidence_snapshot": {
                "visual_mean": analysis.evidence.visual.statistics.mean_score if analysis.evidence.visual.statistics else None,
                "audio_mean": analysis.evidence.audio.statistics.mean_score if analysis.evidence.audio.statistics else None,
                "transcript": " ".join(seg.text for seg in analysis.speech.segments) if (analysis.speech and analysis.speech.segments) else "",
            }
        }

        # Update the stored analysis record in-place with the verified ground truth
        if analysis.assessment:
            if feedback.ground_truth_media == "REAL":
                analysis.assessment.media = "NO_STRONG_EVIDENCE"
            elif feedback.ground_truth_media == "FAKE":
                analysis.assessment.media = "LIKELY_MANIPULATED"

            fraud_risk = analysis.assessment.fraud or "LOW"
            if feedback.ground_truth_fraud == "SCAM":
                analysis.assessment.fraud = "HIGH"
                fraud_risk = "HIGH"
            elif feedback.ground_truth_fraud == "HARMLESS" and fraud_risk != "HIGH":
                analysis.assessment.fraud = "LOW"
                fraud_risk = "LOW"

            if fraud_risk == "HIGH":
                analysis.assessment.action = "STOP_AND_VERIFY"
            elif analysis.assessment.media == "NO_STRONG_EVIDENCE" and fraud_risk in ("LOW", "NOT_ASSESSABLE"):
                analysis.assessment.action = "NO_ACTION_FLAGGED"
            else:
                analysis.assessment.action = "VERIFY"

        if analysis.evidence and analysis.evidence.metadata:
            analysis.evidence.metadata.exact_verified_match = True
            analysis.evidence.metadata.verified_ground_truth = {
                "ground_truth_media": feedback.ground_truth_media,
                "ground_truth_fraud": feedback.ground_truth_fraud,
                "verified_at": timestamp,
                "notes": feedback.notes or "",
            }

        if analysis.explanation is not None:
            v_note = f"Verified Ground Truth: Human analyst certified media as {feedback.ground_truth_media}."
            if v_note not in analysis.explanation:
                analysis.explanation.insert(0, v_note)

        # Persist updated analysis back to MongoDB Atlas and local disk
        try:
            await cls.save_analysis(analysis)
            logger.info(
                f"DatabaseService: Updated analysis '{analysis_id}' with verified verdict: "
                f"media={analysis.assessment.media if analysis.assessment else 'N/A'}, "
                f"fraud={analysis.assessment.fraud if analysis.assessment else 'N/A'}, "
                f"action={analysis.assessment.action if analysis.assessment else 'N/A'}"
            )
        except Exception as e:
            logger.warning(f"DatabaseService: Failed to update analysis record: {e}")

        # 1. Save to local feedback archive
        try:
            fb_file = cls._get_feedback_dir() / f"feedback_{analysis_id}.json"
            fb_file.write_text(json.dumps(training_sample, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to write local feedback file: {e}")

        # 2. Save to MongoDB Atlas feedback collection
        if cls._is_connected and cls._db is not None:
            try:
                await cls._db["feedback_dataset"].replace_one(
                    {"analysis_id": analysis_id},
                    training_sample,
                    upsert=True
                )
                logger.info(f"MongoDB Atlas: Stored verified ground-truth training sample for '{analysis_id}'.")
            except Exception as e:
                logger.warning(f"MongoDB feedback insert error: {e}")

        return training_sample

    @classmethod
    async def get_verified_training_dataset(cls, limit: int = 500) -> List[Dict[str, Any]]:
        """Retrieves curated feedback samples for model retraining."""
        if cls._is_connected and cls._db is not None:
            try:
                cursor = cls._db["feedback_dataset"].find({}, {"_id": 0}).sort("verified_at", -1).limit(limit)
                return [doc async for doc in cursor]
            except Exception as e:
                logger.warning(f"MongoDB training query error: {e}")

        # Fallback local feedback files
        samples = []
        for f in cls._get_feedback_dir().glob("*.json"):
            try:
                samples.append(json.loads(f.read_text(encoding="utf-8")))
            except Exception:
                continue
        return samples

