"""
Job management service for tracking async processing jobs.

This module provides the job management functionality for tracking
background processing tasks like caption generation and video processing.
Jobs are stored in Redis for persistence and fast access.

Validates: Requirements 6.1, 6.2, 6.3, 6.5, 6.6
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid
import json

import redis

from app.models.enums import JobStatus
from app.config import settings


class IJobManager(ABC):
    """
    Interface for job management operations.
    
    Defines the contract for creating, updating, and querying
    background processing jobs.
    """
    
    @abstractmethod
    def create_job(self, job_type: str, video_id: str) -> str:
        """
        Create a new job with pending status.
        
        Args:
            job_type: Type of job (e.g., 'caption_generation', 'video_processing')
            video_id: ID of the video being processed
            
        Returns:
            Unique job identifier
            
        Validates: Requirements 6.1
        """
        pass
    
    @abstractmethod
    def update_status(
        self,
        job_id: str,
        status: JobStatus,
        progress: Optional[int] = None,
        result: Optional[str] = None,
        error: Optional[str] = None
    ) -> None:
        """
        Update job status and optional fields.
        
        Args:
            job_id: Job identifier
            status: New status value
            progress: Progress percentage (0-100)
            result: Result path for completed jobs
            error: Error message for failed jobs
            
        Validates: Requirements 6.2, 6.3
        """
        pass
    
    @abstractmethod
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job details by ID.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job details dict or None if not found
            
        Validates: Requirements 6.5
        """
        pass
    
    @abstractmethod
    def list_jobs(self, video_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all jobs, optionally filtered by video ID.
        
        Args:
            video_id: Optional video ID to filter by
            
        Returns:
            List of job details dicts
            
        Validates: Requirements 6.6
        """
        pass


class RedisJobManager(IJobManager):
    """
    Redis-backed implementation of job management.
    
    Stores job data in Redis using hash structures for efficient
    access and updates. Job IDs are tracked in a set for listing.
    
    Redis key structure:
    - job:{job_id} - Hash containing job data
    - jobs:all - Set of all job IDs
    - jobs:video:{video_id} - Set of job IDs for a specific video
    """
    
    # Key prefixes
    JOB_KEY_PREFIX = "job:"
    ALL_JOBS_KEY = "jobs:all"
    VIDEO_JOBS_KEY_PREFIX = "jobs:video:"
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        Initialize the Redis job manager.
        
        Args:
            redis_client: Optional Redis client instance. If not provided,
                         creates one using settings.
        """
        if redis_client is not None:
            self._redis = redis_client
        else:
            self._redis = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                decode_responses=True
            )

    def _job_key(self, job_id: str) -> str:
        """Get Redis key for a job."""
        return f"{self.JOB_KEY_PREFIX}{job_id}"
    
    def _video_jobs_key(self, video_id: str) -> str:
        """Get Redis key for a video's job set."""
        return f"{self.VIDEO_JOBS_KEY_PREFIX}{video_id}"
    
    def _serialize_job(self, job_data: Dict[str, Any]) -> Dict[str, str]:
        """Serialize job data for Redis storage."""
        serialized = {}
        for key, value in job_data.items():
            if isinstance(value, datetime):
                serialized[key] = value.isoformat()
            elif isinstance(value, JobStatus):
                serialized[key] = value.value
            elif value is None:
                serialized[key] = ""
            else:
                serialized[key] = str(value)
        return serialized
    
    def _deserialize_job(self, job_data: Dict[str, str]) -> Dict[str, Any]:
        """Deserialize job data from Redis storage."""
        if not job_data:
            return {}
        
        deserialized = {}
        for key, value in job_data.items():
            if key in ("created_at", "updated_at"):
                deserialized[key] = datetime.fromisoformat(value) if value else None
            elif key == "status":
                deserialized[key] = JobStatus(value) if value else None
            elif key == "progress":
                deserialized[key] = int(value) if value else None
            elif key in ("result_path", "error_message"):
                deserialized[key] = value if value else None
            else:
                deserialized[key] = value
        return deserialized
    
    def create_job(self, job_type: str, video_id: str) -> str:
        """
        Create a new job with pending status.
        
        Generates a unique job ID, initializes job data with pending status,
        and stores it in Redis. Also tracks the job ID in the all-jobs set
        and the video-specific jobs set.
        
        Args:
            job_type: Type of job (e.g., 'caption_generation', 'video_processing')
            video_id: ID of the video being processed
            
        Returns:
            Unique job identifier (UUID)
            
        Validates: Requirements 6.1
        """
        job_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        job_data = {
            "job_id": job_id,
            "job_type": job_type,
            "video_id": video_id,
            "status": JobStatus.PENDING,
            "progress": None,
            "result_path": None,
            "error_message": None,
            "created_at": now,
            "updated_at": now
        }
        
        # Store job data
        job_key = self._job_key(job_id)
        self._redis.hset(job_key, mapping=self._serialize_job(job_data))
        
        # Track job ID in sets
        self._redis.sadd(self.ALL_JOBS_KEY, job_id)
        self._redis.sadd(self._video_jobs_key(video_id), job_id)
        
        return job_id
    
    def update_status(
        self,
        job_id: str,
        status: JobStatus,
        progress: Optional[int] = None,
        result: Optional[str] = None,
        error: Optional[str] = None
    ) -> None:
        """
        Update job status and optional fields.
        
        Updates the job's status and any provided optional fields.
        Enforces valid status transitions:
        - pending -> processing
        - processing -> completed | failed
        - completed/failed are terminal states
        
        Args:
            job_id: Job identifier
            status: New status value
            progress: Progress percentage (0-100)
            result: Result path for completed jobs
            error: Error message for failed jobs
            
        Raises:
            ValueError: If job not found or invalid status transition
            
        Validates: Requirements 6.2, 6.3
        """
        job_key = self._job_key(job_id)
        
        # Check job exists
        if not self._redis.exists(job_key):
            raise ValueError(f"Job not found: {job_id}")
        
        # Get current status for transition validation
        current_status_str = self._redis.hget(job_key, "status")
        if current_status_str:
            current_status = JobStatus(current_status_str)
            
            # Validate status transition
            if not self._is_valid_transition(current_status, status):
                raise ValueError(
                    f"Invalid status transition: {current_status.value} -> {status.value}"
                )
        
        # Build update data
        now = datetime.now(timezone.utc)
        update_data = {
            "status": status,
            "updated_at": now
        }
        
        if progress is not None:
            update_data["progress"] = progress
        
        if result is not None:
            update_data["result_path"] = result
        
        if error is not None:
            update_data["error_message"] = error
        
        # Update in Redis
        self._redis.hset(job_key, mapping=self._serialize_job(update_data))
    
    def _is_valid_transition(self, current: JobStatus, new: JobStatus) -> bool:
        """
        Check if a status transition is valid.
        
        Valid transitions:
        - pending -> processing
        - processing -> completed
        - processing -> failed
        - Same status (idempotent updates)
        
        Terminal states (completed, failed) cannot transition to other states.
        """
        if current == new:
            return True
        
        valid_transitions = {
            JobStatus.PENDING: {JobStatus.PROCESSING},
            JobStatus.PROCESSING: {JobStatus.COMPLETED, JobStatus.FAILED},
            JobStatus.COMPLETED: set(),  # Terminal state
            JobStatus.FAILED: set()  # Terminal state
        }
        
        return new in valid_transitions.get(current, set())
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job details by ID.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job details dict with all fields, or None if not found
            
        Validates: Requirements 6.5
        """
        job_key = self._job_key(job_id)
        job_data = self._redis.hgetall(job_key)
        
        if not job_data:
            return None
        
        return self._deserialize_job(job_data)
    
    def list_jobs(self, video_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all jobs, optionally filtered by video ID.
        
        Args:
            video_id: Optional video ID to filter by
            
        Returns:
            List of job details dicts, sorted by created_at descending
            
        Validates: Requirements 6.6
        """
        # Get job IDs from appropriate set
        if video_id:
            job_ids = self._redis.smembers(self._video_jobs_key(video_id))
        else:
            job_ids = self._redis.smembers(self.ALL_JOBS_KEY)
        
        # Fetch all job data
        jobs = []
        for job_id in job_ids:
            job_data = self.get_job(job_id)
            if job_data:
                jobs.append(job_data)
        
        # Sort by created_at descending (newest first)
        jobs.sort(key=lambda j: j.get("created_at") or datetime.min, reverse=True)
        
        return jobs
    
    def delete_job(self, job_id: str) -> bool:
        """
        Delete a job from Redis.
        
        Removes the job data and its references from tracking sets.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if job was deleted, False if not found
        """
        job_key = self._job_key(job_id)
        
        # Get video_id before deletion for set cleanup
        video_id = self._redis.hget(job_key, "video_id")
        
        # Delete job data
        deleted = self._redis.delete(job_key)
        
        if deleted:
            # Remove from tracking sets
            self._redis.srem(self.ALL_JOBS_KEY, job_id)
            if video_id:
                self._redis.srem(self._video_jobs_key(video_id), job_id)
            return True
        
        return False
    
    def delete_video_jobs(self, video_id: str) -> int:
        """
        Delete all jobs associated with a video.
        
        Args:
            video_id: Video identifier
            
        Returns:
            Number of jobs deleted
        """
        # Copy to list to avoid modifying set during iteration
        job_ids = list(self._redis.smembers(self._video_jobs_key(video_id)))
        deleted_count = 0
        
        for job_id in job_ids:
            if self.delete_job(job_id):
                deleted_count += 1
        
        return deleted_count
