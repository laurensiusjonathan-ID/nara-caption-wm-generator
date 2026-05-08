"""
Background tasks for video processing operations.

This module defines Celery tasks for caption generation, watermark application,
and combined video processing. Each task updates job status throughout execution.

Validates: Requirements 2.7, 4.8, 5.3
"""

from typing import Optional
import os

from celery import Task
from celery.exceptions import MaxRetriesExceededError

from app.tasks.celery_app import celery_app
from app.models.enums import JobStatus, CaptionFormat, WatermarkPosition
from app.services.job_manager import RedisJobManager
from app.services.caption_generator import (
    generate_captions,
    AudioExtractionError,
    CaptionGenerationError,
)
from app.services.watermark_applicator import (
    apply_watermark,
    WatermarkValidationError,
    WatermarkApplicationError,
)
from app.services.video_processor import (
    process_video,
    merge_videos,
    VideoProcessingError,
)
from app.config import settings


class BaseVideoTask(Task):
    """
    Base task class with common functionality for video processing tasks.
    
    Provides automatic job status updates and error handling.
    """
    
    abstract = True
    autoretry_for = (ConnectionError, TimeoutError)
    retry_backoff = True
    retry_backoff_max = 600  # Max 10 minutes between retries
    retry_jitter = True
    
    _job_manager = None
    
    @property
    def job_manager(self) -> RedisJobManager:
        """Lazy-load job manager to avoid connection issues at import time."""
        if self._job_manager is None:
            self._job_manager = RedisJobManager()
        return self._job_manager
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure by updating job status."""
        job_id = kwargs.get("job_id") or (args[0] if args else None)
        if job_id:
            try:
                self.job_manager.update_status(
                    job_id=job_id,
                    status=JobStatus.FAILED,
                    error=str(exc)
                )
            except Exception:
                pass  # Don't raise during failure handling


@celery_app.task(
    bind=True,
    base=BaseVideoTask,
    name="app.tasks.video_tasks.generate_captions_task",
    max_retries=3
)
def generate_captions_task(
    self,
    job_id: str,
    video_id: str,
    video_path: str,
    output_path: str,
    language: str = "id",
    output_format: str = "srt"
) -> dict:
    """
    Background task for caption generation.
    
    Extracts audio from video and generates captions using faster-whisper.
    Updates job status throughout the process.
    
    Args:
        job_id: Job identifier for status tracking
        video_id: Video identifier
        video_path: Path to the source video file
        output_path: Path where caption file will be saved
        language: Language code for transcription (default: "id" for Indonesian)
        output_format: Caption format ("srt" or "vtt")
        
    Returns:
        Dict with job_id, video_id, and result_path
        
    Validates: Requirements 2.7
    """
    job_manager = self.job_manager
    
    try:
        # Update status to processing
        job_manager.update_status(
            job_id=job_id,
            status=JobStatus.PROCESSING,
            progress=0
        )
        
        # Convert format string to enum
        caption_format = CaptionFormat(output_format.lower())
        
        # Update progress - starting transcription
        job_manager.update_status(
            job_id=job_id,
            status=JobStatus.PROCESSING,
            progress=10
        )
        
        # Generate captions
        result_path = generate_captions(
            video_path=video_path,
            output_path=output_path,
            language=language,
            output_format=caption_format,
            model_size=settings.whisper_model_size
        )
        
        # Update status to completed
        job_manager.update_status(
            job_id=job_id,
            status=JobStatus.COMPLETED,
            progress=100,
            result=result_path
        )
        
        return {
            "job_id": job_id,
            "video_id": video_id,
            "result_path": result_path
        }
        
    except (AudioExtractionError, CaptionGenerationError) as e:
        # Non-retryable errors - mark as failed
        job_manager.update_status(
            job_id=job_id,
            status=JobStatus.FAILED,
            error=str(e)
        )
        raise
        
    except Exception as e:
        # Retry for transient errors
        try:
            raise self.retry(exc=e)
        except MaxRetriesExceededError:
            job_manager.update_status(
                job_id=job_id,
                status=JobStatus.FAILED,
                error=f"Max retries exceeded: {str(e)}"
            )
            raise


@celery_app.task(
    bind=True,
    base=BaseVideoTask,
    name="app.tasks.video_tasks.apply_watermark_task",
    max_retries=3
)
def apply_watermark_task(
    self,
    job_id: str,
    video_id: str,
    video_path: str,
    watermark_path: str,
    output_path: str,
    position: str = "bottom-right",
    opacity: float = 0.5
) -> dict:
    """
    Background task for watermark application.
    
    Applies a PNG watermark to a video with configurable position and opacity.
    Updates job status throughout the process.
    
    Args:
        job_id: Job identifier for status tracking
        video_id: Video identifier
        video_path: Path to the source video file
        watermark_path: Path to the PNG watermark image
        output_path: Path for the output video file
        position: Watermark position (default: "bottom-right")
        opacity: Watermark opacity 0.0-1.0 (default: 0.5)
        
    Returns:
        Dict with job_id, video_id, and result_path
        
    Validates: Requirements 4.8
    """
    job_manager = self.job_manager
    
    try:
        # Update status to processing
        job_manager.update_status(
            job_id=job_id,
            status=JobStatus.PROCESSING,
            progress=0
        )
        
        # Convert position string to enum
        watermark_position = WatermarkPosition(position)
        
        # Update progress - starting watermark application
        job_manager.update_status(
            job_id=job_id,
            status=JobStatus.PROCESSING,
            progress=10
        )
        
        # Apply watermark
        result_path = apply_watermark(
            video_path=video_path,
            watermark_path=watermark_path,
            output_path=output_path,
            position=watermark_position,
            opacity=opacity
        )
        
        # Update status to completed
        job_manager.update_status(
            job_id=job_id,
            status=JobStatus.COMPLETED,
            progress=100,
            result=result_path
        )
        
        return {
            "job_id": job_id,
            "video_id": video_id,
            "result_path": result_path
        }
        
    except (WatermarkValidationError, WatermarkApplicationError) as e:
        # Non-retryable errors - mark as failed
        job_manager.update_status(
            job_id=job_id,
            status=JobStatus.FAILED,
            error=str(e)
        )
        raise
        
    except Exception as e:
        # Retry for transient errors
        try:
            raise self.retry(exc=e)
        except MaxRetriesExceededError:
            job_manager.update_status(
                job_id=job_id,
                status=JobStatus.FAILED,
                error=f"Max retries exceeded: {str(e)}"
            )
            raise


@celery_app.task(
    bind=True,
    base=BaseVideoTask,
    name="app.tasks.video_tasks.process_video_task",
    max_retries=3
)
def process_video_task(
    self,
    job_id: str,
    video_id: str,
    video_path: str,
    output_path: str,
    caption_path: Optional[str] = None,
    watermark_path: Optional[str] = None,
    watermark_position: Optional[str] = None,
    watermark_opacity: Optional[float] = None
) -> dict:
    """
    Background task for combined video processing.
    
    Processes a video with captions and/or watermark in a single operation.
    Updates job status throughout the process.
    
    Args:
        job_id: Job identifier for status tracking
        video_id: Video identifier
        video_path: Path to the source video file
        output_path: Path for the output video file
        caption_path: Optional path to caption file (SRT or VTT)
        watermark_path: Optional path to watermark image (PNG)
        watermark_position: Optional watermark position
        watermark_opacity: Optional watermark opacity 0.0-1.0
        
    Returns:
        Dict with job_id, video_id, and result_path
        
    Validates: Requirements 5.3
    """
    job_manager = self.job_manager
    
    try:
        # Update status to processing
        job_manager.update_status(
            job_id=job_id,
            status=JobStatus.PROCESSING,
            progress=0
        )
        
        # Convert position string to enum if provided
        position = WatermarkPosition.BOTTOM_RIGHT
        if watermark_position:
            position = WatermarkPosition(watermark_position)
        
        # Use default opacity if not provided
        opacity = watermark_opacity if watermark_opacity is not None else 0.5
        
        # Update progress - starting video processing
        job_manager.update_status(
            job_id=job_id,
            status=JobStatus.PROCESSING,
            progress=10
        )
        
        # Process video
        result_path = process_video(
            video_path=video_path,
            output_path=output_path,
            caption_path=caption_path,
            watermark_path=watermark_path,
            watermark_position=position,
            watermark_opacity=opacity
        )
        
        # Update status to completed
        job_manager.update_status(
            job_id=job_id,
            status=JobStatus.COMPLETED,
            progress=100,
            result=result_path
        )
        
        return {
            "job_id": job_id,
            "video_id": video_id,
            "result_path": result_path
        }
        
    except VideoProcessingError as e:
        # Non-retryable errors - mark as failed
        job_manager.update_status(
            job_id=job_id,
            status=JobStatus.FAILED,
            error=str(e)
        )
        raise
        
    except Exception as e:
        # Retry for transient errors
        try:
            raise self.retry(exc=e)
        except MaxRetriesExceededError:
            job_manager.update_status(
                job_id=job_id,
                status=JobStatus.FAILED,
                error=f"Max retries exceeded: {str(e)}"
            )
            raise


@celery_app.task(
    bind=True,
    base=BaseVideoTask,
    name="app.tasks.video_tasks.merge_videos_task",
    max_retries=3
)
def merge_videos_task(
    self,
    job_id: str,
    video_id: str,
    cover_video_path: str,
    main_video_path: str,
    output_path: str,
    re_encode: bool = True
) -> dict:
    """
    Background task for merging videos.
    
    Merges a cover video with a main course video. The cover video is placed before the main video.
    
    Args:
        job_id: Job identifier for status tracking
        video_id: Video identifier
        cover_video_path: Path to the cover/intro video file
        main_video_path: Path to the main course video file
        output_path: Path for the merged output video file
        re_encode: If True, re-encode for compatibility (default: True)
        
    Returns:
        Dict with job_id, video_id, and result_path
        
    Validates: Requirements 5.1, 5.4
    """
    job_manager = self.job_manager
    
    try:
        # Update status to processing
        job_manager.update_status(
            job_id=job_id,
            status=JobStatus.PROCESSING,
            progress=0
        )
        
        # Update progress - starting video merge
        job_manager.update_status(
            job_id=job_id,
            status=JobStatus.PROCESSING,
            progress=10
        )
        
        # Merge videos
        result_path = merge_videos(
            cover_video_path=cover_video_path,
            main_video_path=main_video_path,
            output_path=output_path,
            re_encode=re_encode
        )
        
        # Update status to completed
        job_manager.update_status(
            job_id=job_id,
            status=JobStatus.COMPLETED,
            progress=100,
            result=result_path
        )
        
        return {
            "job_id": job_id,
            "video_id": video_id,
            "result_path": result_path
        }
        
    except VideoProcessingError as e:
        # Non-retryable errors - mark as failed
        job_manager.update_status(
            job_id=job_id,
            status=JobStatus.FAILED,
            error=str(e)
        )
        raise
        
    except Exception as e:
        # Retry for transient errors
        try:
            raise self.retry(exc=e)
        except MaxRetriesExceededError:
            job_manager.update_status(
                job_id=job_id,
                status=JobStatus.FAILED,
                error=f"Max retries exceeded: {str(e)}"
            )
            raise
