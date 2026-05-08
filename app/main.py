"""Main FastAPI application entry point."""

from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging
import sys

from app.config import settings
from app.api import videos, captions, watermarks, processing, jobs
from app.api.exceptions import register_exception_handlers

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    
    # Validate dependencies
    validate_dependencies()
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Application shutdown")


def validate_dependencies():
    """Validate required dependencies are available."""
    import shutil
    import redis as redis_client
    
    # Check FFmpeg
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        logger.error("FFmpeg not found in PATH. Please install FFmpeg.")
        raise RuntimeError("FFmpeg is required but not found")
    logger.info(f"FFmpeg found at: {ffmpeg_path}")
    
    # Check Redis connection
    try:
        r = redis_client.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            socket_connect_timeout=5
        )
        r.ping()
        logger.info(f"Redis connection successful: {settings.redis_host}:{settings.redis_port}")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        raise RuntimeError(f"Redis is required but connection failed: {e}")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="API for adding captions and watermarks to e-course videos",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Register exception handlers for consistent error responses
# Validates: Requirements 7.3, 7.4, 7.5
register_exception_handlers(app)


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    
    Returns the application status and version.
    """
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.app_version
    }


@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint.
    
    Returns basic API information.
    """
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "docs": "/docs",
        "redoc": "/redoc"
    }


# API routers - wired with /api/v1 prefix and appropriate tags
# Validates: Requirements 7.1, 7.2
app.include_router(videos.router, prefix=settings.api_v1_prefix, tags=["Videos"])
app.include_router(captions.router, prefix=settings.api_v1_prefix, tags=["Captions"])
app.include_router(watermarks.router, prefix=settings.api_v1_prefix, tags=["Watermarks"])
app.include_router(processing.router, prefix=settings.api_v1_prefix, tags=["Processing"])
app.include_router(jobs.router, prefix=settings.api_v1_prefix, tags=["Jobs"])
