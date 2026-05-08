"""
Celery application configuration for background task processing.

This module configures Celery with Redis as the message broker and result backend.
It includes retry policies for transient failures to ensure reliable task execution.

Validates: Requirements 2.7, 4.8
"""

from celery import Celery

from app.config import settings


# Create Celery application
celery_app = Celery(
    "video_processor",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.video_tasks"]
)

# Celery configuration
celery_app.conf.update(
    # Task tracking
    task_track_started=settings.celery_task_track_started,
    task_time_limit=settings.celery_task_time_limit,
    
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_extended=True,  # Store additional task metadata
    
    # Task serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # Timezone
    timezone="UTC",
    enable_utc=True,
    
    # Task retry defaults for transient failures
    task_default_retry_delay=60,  # 60 seconds between retries
    task_max_retries=3,  # Maximum 3 retries
    
    # Task acknowledgment
    task_acks_late=True,  # Acknowledge after task completes
    task_reject_on_worker_lost=True,  # Reject task if worker dies
    
    # Worker settings
    worker_prefetch_multiplier=1,  # Process one task at a time
    worker_concurrency=2,  # Number of concurrent workers
)

# Task routing (optional, for future scaling)
celery_app.conf.task_routes = {
    "app.tasks.video_tasks.generate_captions_task": {"queue": "captions"},
    "app.tasks.video_tasks.apply_watermark_task": {"queue": "watermarks"},
    "app.tasks.video_tasks.process_video_task": {"queue": "processing"},
}

# Default queue for tasks without explicit routing
celery_app.conf.task_default_queue = "default"
