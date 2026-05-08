"""
Background tasks package.

This package contains Celery configuration and background task definitions
for video processing operations.
"""

from app.tasks.celery_app import celery_app

__all__ = ["celery_app"]
