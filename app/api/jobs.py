"""
Job management API endpoints for the Video Caption Watermark API.

This module provides endpoints for querying job status and listing jobs.
Jobs are created by other endpoints (caption generation, video processing)
and tracked in Redis for status monitoring.

Endpoints:
- GET /api/v1/jobs/{job_id} - Get job status
- GET /api/v1/jobs - List all jobs (optionally filtered by video_id)

Validates: Requirements 6.5, 6.6
"""

from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query, status

from app.models.schemas import JobResponse, JobListResponse, ErrorResponse
from app.models.enums import JobStatus
from app.services.job_manager import RedisJobManager
from app.config import settings


router = APIRouter()

# Initialize job manager
job_manager = RedisJobManager()


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Job not found"},
    },
    summary="Get job status",
    description="Retrieve the current status and details of a background processing job.",
)
async def get_job(job_id: str) -> JobResponse:
    """
    Get job status by ID.
    
    Returns the complete job information including status, progress,
    result path (if completed), and error message (if failed).
    
    Args:
        job_id: Unique identifier of the job
        
    Returns:
        JobResponse with complete job information
        
    Raises:
        HTTPException 404: If the job is not found
        
    Validates: Requirements 6.5
    """
    job_data = job_manager.get_job(job_id)
    
    if job_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "JOB_NOT_FOUND",
                "message": f"Job with ID '{job_id}' not found",
                "details": None,
            },
        )
    
    return JobResponse(
        job_id=job_data["job_id"],
        job_type=job_data["job_type"],
        video_id=job_data["video_id"],
        status=job_data["status"],
        progress=job_data.get("progress"),
        result_path=job_data.get("result_path"),
        error_message=job_data.get("error_message"),
        created_at=job_data["created_at"],
        updated_at=job_data["updated_at"],
    )


@router.get(
    "/jobs",
    response_model=JobListResponse,
    summary="List all jobs",
    description="Retrieve a list of all background processing jobs, optionally filtered by video ID.",
)
async def list_jobs(
    video_id: Optional[str] = Query(
        default=None,
        description="Filter jobs by video ID"
    )
) -> JobListResponse:
    """
    List all jobs with optional filtering.
    
    Returns all jobs in the system, sorted by creation time (newest first).
    Can be filtered by video_id to show only jobs for a specific video.
    
    Args:
        video_id: Optional video ID to filter jobs by
        
    Returns:
        JobListResponse with list of jobs and total count
        
    Validates: Requirements 6.6
    """
    jobs_data = job_manager.list_jobs(video_id=video_id)
    
    jobs = [
        JobResponse(
            job_id=job["job_id"],
            job_type=job["job_type"],
            video_id=job["video_id"],
            status=job["status"],
            progress=job.get("progress"),
            result_path=job.get("result_path"),
            error_message=job.get("error_message"),
            created_at=job["created_at"],
            updated_at=job["updated_at"],
        )
        for job in jobs_data
    ]
    
    return JobListResponse(
        jobs=jobs,
        total=len(jobs),
    )
