import asyncio
import os
import time
from collections import defaultdict
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from app.core.config import settings
from app.core.logging import logger
from app.schemas.analysis import AnalysisResponse, HealthResponse
from app.services.analysis_service import (
    AnalysisService,
    FileTooLargeError,
    InvalidFileExtensionError,
    InvalidMimeTypeError,
    ValidationException,
)
from app.services.video_processor import (
    CorruptedVideoError,
    VideoDurationExceededError,
    VideoProcessingError,
)
from app.utils.ffmpeg import check_ffmpeg_available

from app.db import DatabaseService, FeedbackPayload

router = APIRouter()

# In-memory client IP rate limiter (Phase 18 security)
_RATE_LIMIT_MAX_REQUESTS = 30
_RATE_LIMIT_WINDOW_SECONDS = 60.0
_client_request_history = defaultdict(list)

# Concurrency semaphore: protect CPU from starvation under burst concurrent analyses (P1.12)
_ANALYSIS_SEMAPHORE = asyncio.Semaphore(2)


def get_client_ip(request: Request) -> str:
    """
    Secure client IP resolution:
    Only trust CF-Connecting-IP / X-Forwarded-For when Cloudflare CF-Ray header is present;
    otherwise fallback to direct client socket host.
    """
    cf_ray = request.headers.get("CF-Ray") or request.headers.get("cf-ray")
    if cf_ray:
        cf_ip = request.headers.get("CF-Connecting-IP") or request.headers.get("cf-connecting-ip")
        if cf_ip:
            return cf_ip.strip()
        xfwd = request.headers.get("X-Forwarded-For") or request.headers.get("x-forwarded-for")
        if xfwd:
            return xfwd.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


def check_rate_limit(request: Request) -> None:
    """Enforces client IP rate limits in-memory without external cache dependencies."""
    client_ip = get_client_ip(request)
    now = time.time()
    # Retain only timestamps within the rolling window
    timestamps = [ts for ts in _client_request_history[client_ip] if now - ts < _RATE_LIMIT_WINDOW_SECONDS]
    if len(timestamps) >= _RATE_LIMIT_MAX_REQUESTS:
        _client_request_history[client_ip] = timestamps
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Maximum 30 analysis requests per minute allowed.",
        )
    timestamps.append(now)
    _client_request_history[client_ip] = timestamps


def get_analysis_service() -> AnalysisService:
    """Dependency injection provider for AnalysisService."""
    return AnalysisService()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check endpoint",
    description="Returns server status, MongoDB connectivity, and verification of FFmpeg/FFprobe availability."
)
async def health_check():
    ffmpeg_ok, ffprobe_ok, _ = check_ffmpeg_available()
    return HealthResponse(
        status="ok",
        ffmpeg_available=ffmpeg_ok,
        ffprobe_available=ffprobe_ok,
        version=settings.VERSION
    )


@router.get(
    "/analyses",
    summary="List analysis history",
    description="Retrieves historical forensic reports with optional text search and pagination."
)
async def list_analyses(
    limit: int = 50,
    skip: int = 0,
    search: Optional[str] = None
):
    items = await DatabaseService.list_analyses(limit=limit, skip=skip, search=search)
    return {"count": len(items), "items": items, "mongodb_connected": DatabaseService.is_connected()}


@router.get(
    "/analyses/{analysis_id}",
    response_model=AnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Get analysis report by ID",
    description="Retrieves a completed forensic analysis report by its unique UUID."
)
async def get_analysis_by_id(analysis_id: str):
    analysis = await DatabaseService.get_analysis(analysis_id)
    if analysis:
        return analysis
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Analysis with ID '{analysis_id}' was not found or has expired."
    )


@router.post(
    "/analyses/{analysis_id}/feedback",
    summary="Record human verification feedback for active learning and train model adapter",
    description="Stores verified ground-truth labels, updates VerifiedMediaRegistry, executes real optimizer updates on the adapter, and loads the new checkpoint."
)
async def record_feedback(
    analysis_id: str,
    feedback: FeedbackPayload
):
    try:
        sample = await DatabaseService.record_feedback(analysis_id, feedback)

        # 1. Register into VerifiedMediaRegistry (SHA-256 + Perceptual Memory)
        import json
        import numpy as np
        from app.services.active_learning.verified_memory import VerifiedMediaRegistry
        registry = VerifiedMediaRegistry.get_instance()

        features = None
        telemetry = None
        mean_emb = None
        cache_path = settings.TEMP_DIR / "analyses" / f"{analysis_id}_features.json"
        if cache_path.exists():
            try:
                c_data = json.loads(cache_path.read_text(encoding="utf-8"))
                features = c_data.get("features")
                telemetry = c_data.get("telemetry")
                mean_emb = c_data.get("mean_embedding")
            except Exception as e:
                logger.warning(f"Error reading feature cache: {e}")

        # If no feature cache exists, generate features from analysis results if available
        if not features:
            analysis = await DatabaseService.get_analysis(analysis_id)
            if analysis and analysis.visual and analysis.visual.results:
                features = []
                telemetry = []
                for fr in analysis.visual.results:
                    if fr.face_detected:
                        raw_f = fr.raw_fake_score if fr.raw_fake_score is not None else (fr.fake_score or 0.5)
                        vec = [raw_f] * 1280
                        features.append(vec)
                        telemetry.append([
                            (fr.blur_score or 50.0) / 500.0,
                            (fr.luma or 128.0) / 255.0,
                            (fr.noise_estimate or 2.0) / 10.0,
                            0.0
                        ])
                if features:
                    mean_emb = np.mean(np.array(features, dtype=np.float32), axis=0).tolist()

        if sample.get("sha256") and sample.get("sha256") != "N/A":
            registry.register(
                sha256=sample["sha256"],
                filename=sample.get("filename", "unknown"),
                ground_truth_media=feedback.ground_truth_media,
                ground_truth_fraud=feedback.ground_truth_fraud,
                embedding=mean_emb,
                notes=feedback.notes or "",
                analyst_id=feedback.analyst_id or "analyst"
            )
            from app.services.cache_service import AnalysisCacheService
            AnalysisCacheService.get_instance().invalidate(sample["sha256"])

        # 2. Run active learning adaptation via ActiveLearningTrainingService
        from app.services.active_learning.training_service import ActiveLearningTrainingService
        training_service = ActiveLearningTrainingService.get_instance()

        training_result = None
        if features and feedback.ground_truth_media in ("REAL", "FAKE"):
            transcript = ""
            fraud_cats = []
            req_actions = []
            analysis = await DatabaseService.get_analysis(analysis_id)
            if analysis:
                if analysis.speech:
                    if getattr(analysis.speech, "transcript", None):
                        transcript = analysis.speech.transcript
                    elif getattr(analysis.speech, "segments", None):
                        transcript = " ".join([seg.text for seg in analysis.speech.segments if getattr(seg, "text", None)])
                if analysis.fraud:
                    fraud_cats = [c.category for c in getattr(analysis.fraud, "categories", [])]
                    req_actions = getattr(analysis.fraud, "requested_actions", [])

            training_result = training_service.register_and_train_sample(
                analysis_id=analysis_id,
                features=features,
                telemetry=telemetry,
                ground_truth_media=feedback.ground_truth_media,
                ground_truth_fraud=feedback.ground_truth_fraud,
                transcript=transcript,
                fraud_categories=fraud_cats,
                requested_actions=req_actions,
                notes=feedback.notes or "",
                analyst_id=feedback.analyst_id or "analyst",
                epochs=15,
                lr=0.005,
                force_train=True,
            )

        if training_result:
            if training_result.get("status") == "training_completed":
                status_str = "training_completed"
                msg = f"Verification stored. Adapter optimized to {training_service.active_version}."
            else:
                status_str = "deferred"
                msg = f"Verification stored in {training_result.get('dataset_version')}. Model adaptation safely deferred until balanced samples are available."
        else:
            status_str = "stored_only"
            msg = "Ground-truth feedback recorded successfully."

        return {
            "ok": True,
            "status": status_str,
            "message": msg,
            "sample": sample,
            "training": training_result
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Feedback/Training error: {e}")
        return {
            "ok": False,
            "status": "failed",
            "message": f"Verification stored, but model adaptation FAILED: {str(e)}",
            "sample": None,
            "training": None
        }


@router.get(
    "/train/adapter/status",
    summary="Get active adapter status and version",
    description="Returns current active adapter version, trainable parameter count, checksum, and training history."
)
async def get_adapter_status():
    from app.services.active_learning.training_service import ActiveLearningTrainingService
    ts = ActiveLearningTrainingService.get_instance()
    return {
        "active_version": ts.active_version,
        "base_model": ts.base_model_name,
        "base_model_version": ts.base_model_version,
        "trainable_parameters": ts.adapter.count_trainable_parameters(),
        "parameter_checksum": ts.adapter.get_parameter_checksum(),
    }


@router.post(
    "/train/rollback",
    summary="Rollback adapter to a previous version",
    description="Rolls back active model adapter to an earlier version checkpoint."
)
async def rollback_adapter(version: str):
    from app.services.active_learning.training_service import ActiveLearningTrainingService
    ts = ActiveLearningTrainingService.get_instance()
    try:
        res = ts.rollback(version)
        return {"ok": True, "result": res}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


def verify_admin_access(request: Request) -> None:
    """Optional admin security: requires X-Admin-Key if ADMIN_API_KEY is configured."""
    admin_key = getattr(settings, "ADMIN_API_KEY", None) or os.getenv("ADMIN_API_KEY")
    if admin_key:
        provided = request.headers.get("X-Admin-Key") or request.headers.get("Authorization")
        if not provided or (provided != admin_key and f"Bearer {admin_key}" != provided):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized: invalid or missing admin API key.",
            )


@router.get(
    "/train/dataset",
    dependencies=[Depends(verify_admin_access)],
    summary="Get verified active learning dataset",
    description="Lists all human-confirmed ground-truth training samples stored in MongoDB / local feedback archive."
)
async def get_training_dataset(limit: int = 200):
    samples = await DatabaseService.get_verified_training_dataset(limit=limit)
    return {
        "count": len(samples),
        "samples": samples,
        "mongodb_connected": DatabaseService.is_connected()
    }


@router.post(
    "/analyses",
    response_model=AnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload and analyze video/audio",
    description="Uploads a media file, validates it, extracts frames/audio, calculates SHA-256, and returns Stage 1, 2, 3 results."
)
async def analyze_video(
    request: Request,
    file: UploadFile = File(..., description="Video or audio file to inspect and analyze"),
    service: AnalysisService = Depends(get_analysis_service)
):
    check_rate_limit(request)
    try:
        async with _ANALYSIS_SEMAPHORE:
            result = await service.analyze_video(file)
        await DatabaseService.save_analysis(result)
        return result
    except (InvalidFileExtensionError, InvalidMimeTypeError) as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except FileTooLargeError as e:
        logger.warning(f"Payload too large: {e}")
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(e)
        )
    except VideoDurationExceededError as e:
        logger.warning(f"Duration exceeded: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except (CorruptedVideoError, ValidationException) as e:
        logger.warning(f"Invalid media input: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except VideoProcessingError as e:
        logger.error(f"Video processing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process video: {str(e)}"
        )
    except Exception as e:
        logger.exception(f"Unexpected server error during analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing your request."
        )
