import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")

from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router as api_router
from app.core.config import settings
from app.core.logging import logger
from app.utils.ffmpeg import check_ffmpeg_available


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Verifies system prerequisites on startup and manages cleanup on shutdown.
    """
    logger.info("=" * 60)
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    logger.info("=" * 60)

    # Validate FFmpeg and FFprobe system availability
    ffmpeg_ok, ffprobe_ok, err_msg = check_ffmpeg_available()
    if not (ffmpeg_ok and ffprobe_ok):
        logger.critical(f"STARTUP WARNING: {err_msg}")
        logger.critical("Media processing operations will fail without FFmpeg.")
    else:
        logger.info("Prerequisites check: FFmpeg and FFprobe detected on system PATH.")

    logger.info(f"Ephemeral media directory configured at: {settings.TEMP_DIR.resolve()}")
    
    # Initialize MongoDB Atlas / Database Service
    from app.db import DatabaseService
    await DatabaseService.connect()

    yield

    await DatabaseService.disconnect()
    logger.info(f"Shutting down {settings.PROJECT_NAME}")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Authentica AI Fraud & Deepfake Detection - Stage 1 Backend Foundation",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes under /api
app.include_router(api_router, prefix=settings.API_V1_STR)

# Mount controlled demo lab under /demo for browser extension testing
demo_dir = Path(__file__).resolve().parent.parent.parent / "demo"
if demo_dir.is_dir():
    from fastapi.staticfiles import StaticFiles
    app.mount("/demo", StaticFiles(directory=str(demo_dir), html=True), name="demo")


# Global unhandled exception handler to prevent leaking stack traces to clients
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled server error on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred while processing the request.",
            "error_code": "INTERNAL_SERVER_ERROR"
        }
    )
