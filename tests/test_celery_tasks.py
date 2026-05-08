"""
Unit tests for Celery background tasks.

Tests the Celery task configuration and video processing tasks
for proper job status updates and error handling.

Validates: Requirements 2.7, 4.8, 5.3
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from celery.exceptions import MaxRetriesExceededError

from app.models.enums import JobStatus, CaptionFormat, WatermarkPosition
from app.tasks.celery_app import celery_app
from app.tasks.video_tasks import (
    BaseVideoTask,
    generate_captions_task,
    apply_watermark_task,
    process_video_task,
)


class TestCeleryAppConfiguration:
    """Test suite for Celery application configuration."""
    
    def test_celery_app_name(self):
        """Test that Celery app has correct name."""
        assert celery_app.main == "video_processor"
    
    def test_celery_task_serializer(self):
        """Test that task serializer is JSON."""
        assert celery_app.conf.task_serializer == "json"
    
    def test_celery_result_serializer(self):
        """Test that result serializer is JSON."""
        assert celery_app.conf.result_serializer == "json"
    
    def test_celery_accept_content(self):
        """Test that accepted content includes JSON."""
        assert "json" in celery_app.conf.accept_content
    
    def test_celery_timezone_utc(self):
        """Test that timezone is UTC."""
        assert celery_app.conf.timezone == "UTC"
        assert celery_app.conf.enable_utc is True
    
    def test_celery_task_acks_late(self):
        """Test that tasks acknowledge after completion."""
        assert celery_app.conf.task_acks_late is True
    
    def test_celery_task_reject_on_worker_lost(self):
        """Test that tasks are rejected if worker dies."""
        assert celery_app.conf.task_reject_on_worker_lost is True
    
    def test_celery_default_retry_delay(self):
        """Test default retry delay is configured."""
        assert celery_app.conf.task_default_retry_delay == 60
    
    def test_celery_max_retries(self):
        """Test max retries is configured."""
        assert celery_app.conf.task_max_retries == 3


class TestBaseVideoTask:
    """Test suite for BaseVideoTask base class."""
    
    def test_autoretry_for_connection_errors(self):
        """Test that connection errors trigger auto-retry."""
        assert ConnectionError in BaseVideoTask.autoretry_for
        assert TimeoutError in BaseVideoTask.autoretry_for
    
    def test_retry_backoff_enabled(self):
        """Test that retry backoff is enabled."""
        assert BaseVideoTask.retry_backoff is True
    
    def test_retry_backoff_max(self):
        """Test retry backoff max is 10 minutes."""
        assert BaseVideoTask.retry_backoff_max == 600
    
    def test_retry_jitter_enabled(self):
        """Test that retry jitter is enabled."""
        assert BaseVideoTask.retry_jitter is True


class TestGenerateCaptionsTask:
    """Test suite for generate_captions_task."""
    
    def test_task_is_registered(self):
        """Test that task is registered with Celery."""
        assert "app.tasks.video_tasks.generate_captions_task" in celery_app.tasks
    
    def test_task_max_retries(self):
        """Test task has correct max retries."""
        task = celery_app.tasks["app.tasks.video_tasks.generate_captions_task"]
        assert task.max_retries == 3
    
    @patch("app.tasks.video_tasks.generate_captions")
    @patch("app.tasks.video_tasks.RedisJobManager")
    def test_updates_status_to_processing(self, mock_manager_class, mock_generate):
        """
        Test that task updates job status to processing.
        
        Validates: Requirements 2.7
        """
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_generate.return_value = "/captions/test.srt"
        
        # Create a mock task instance
        task = generate_captions_task
        task._job_manager = mock_manager
        
        result = task.apply(args=(
            "job-123",
            "video-456",
            "/uploads/video.mp4",
            "/captions/video.srt",
            "id",
            "srt"
        )).get()
        
        # Verify status was updated to processing
        calls = mock_manager.update_status.call_args_list
        processing_calls = [c for c in calls if c[1].get("status") == JobStatus.PROCESSING]
        assert len(processing_calls) >= 1
    
    @patch("app.tasks.video_tasks.generate_captions")
    @patch("app.tasks.video_tasks.RedisJobManager")
    def test_updates_status_to_completed_on_success(self, mock_manager_class, mock_generate):
        """
        Test that task updates job status to completed on success.
        
        Validates: Requirements 2.7
        """
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_generate.return_value = "/captions/test.srt"
        
        task = generate_captions_task
        task._job_manager = mock_manager
        
        result = task.apply(args=(
            "job-123",
            "video-456",
            "/uploads/video.mp4",
            "/captions/video.srt",
            "id",
            "srt"
        )).get()
        
        # Verify final status is completed
        final_call = mock_manager.update_status.call_args_list[-1]
        assert final_call[1]["status"] == JobStatus.COMPLETED
        assert final_call[1]["progress"] == 100
    
    @patch("app.tasks.video_tasks.generate_captions")
    @patch("app.tasks.video_tasks.RedisJobManager")
    def test_returns_result_dict(self, mock_manager_class, mock_generate):
        """
        Test that task returns correct result dictionary.
        
        Validates: Requirements 2.7
        """
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_generate.return_value = "/captions/test.srt"
        
        task = generate_captions_task
        task._job_manager = mock_manager
        
        result = task.apply(args=(
            "job-123",
            "video-456",
            "/uploads/video.mp4",
            "/captions/video.srt",
            "id",
            "srt"
        )).get()
        
        assert result["job_id"] == "job-123"
        assert result["video_id"] == "video-456"
        assert result["result_path"] == "/captions/test.srt"


class TestApplyWatermarkTask:
    """Test suite for apply_watermark_task."""
    
    def test_task_is_registered(self):
        """Test that task is registered with Celery."""
        assert "app.tasks.video_tasks.apply_watermark_task" in celery_app.tasks
    
    def test_task_max_retries(self):
        """Test task has correct max retries."""
        task = celery_app.tasks["app.tasks.video_tasks.apply_watermark_task"]
        assert task.max_retries == 3
    
    @patch("app.tasks.video_tasks.apply_watermark")
    @patch("app.tasks.video_tasks.RedisJobManager")
    def test_updates_status_to_processing(self, mock_manager_class, mock_apply):
        """
        Test that task updates job status to processing.
        
        Validates: Requirements 4.8
        """
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_apply.return_value = "/outputs/video.mp4"
        
        task = apply_watermark_task
        task._job_manager = mock_manager
        
        result = task.apply(args=(
            "job-123",
            "video-456",
            "/uploads/video.mp4",
            "/watermarks/logo.png",
            "/outputs/video.mp4",
            "bottom-right",
            0.5
        )).get()
        
        # Verify status was updated to processing
        calls = mock_manager.update_status.call_args_list
        processing_calls = [c for c in calls if c[1].get("status") == JobStatus.PROCESSING]
        assert len(processing_calls) >= 1
    
    @patch("app.tasks.video_tasks.apply_watermark")
    @patch("app.tasks.video_tasks.RedisJobManager")
    def test_updates_status_to_completed_on_success(self, mock_manager_class, mock_apply):
        """
        Test that task updates job status to completed on success.
        
        Validates: Requirements 4.8
        """
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_apply.return_value = "/outputs/video.mp4"
        
        task = apply_watermark_task
        task._job_manager = mock_manager
        
        result = task.apply(args=(
            "job-123",
            "video-456",
            "/uploads/video.mp4",
            "/watermarks/logo.png",
            "/outputs/video.mp4",
            "bottom-right",
            0.5
        )).get()
        
        # Verify final status is completed
        final_call = mock_manager.update_status.call_args_list[-1]
        assert final_call[1]["status"] == JobStatus.COMPLETED
        assert final_call[1]["progress"] == 100
    
    @patch("app.tasks.video_tasks.apply_watermark")
    @patch("app.tasks.video_tasks.RedisJobManager")
    def test_returns_result_dict(self, mock_manager_class, mock_apply):
        """
        Test that task returns correct result dictionary.
        
        Validates: Requirements 4.8
        """
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_apply.return_value = "/outputs/video.mp4"
        
        task = apply_watermark_task
        task._job_manager = mock_manager
        
        result = task.apply(args=(
            "job-123",
            "video-456",
            "/uploads/video.mp4",
            "/watermarks/logo.png",
            "/outputs/video.mp4",
            "bottom-right",
            0.5
        )).get()
        
        assert result["job_id"] == "job-123"
        assert result["video_id"] == "video-456"
        assert result["result_path"] == "/outputs/video.mp4"


class TestProcessVideoTask:
    """Test suite for process_video_task."""
    
    def test_task_is_registered(self):
        """Test that task is registered with Celery."""
        assert "app.tasks.video_tasks.process_video_task" in celery_app.tasks
    
    def test_task_max_retries(self):
        """Test task has correct max retries."""
        task = celery_app.tasks["app.tasks.video_tasks.process_video_task"]
        assert task.max_retries == 3
    
    @patch("app.tasks.video_tasks.process_video")
    @patch("app.tasks.video_tasks.RedisJobManager")
    def test_updates_status_to_processing(self, mock_manager_class, mock_process):
        """
        Test that task updates job status to processing.
        
        Validates: Requirements 5.3
        """
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_process.return_value = "/outputs/video.mp4"
        
        task = process_video_task
        task._job_manager = mock_manager
        
        result = task.apply(args=(
            "job-123",
            "video-456",
            "/uploads/video.mp4",
            "/outputs/video.mp4",
            "/captions/video.srt",
            None,
            None,
            None
        )).get()
        
        # Verify status was updated to processing
        calls = mock_manager.update_status.call_args_list
        processing_calls = [c for c in calls if c[1].get("status") == JobStatus.PROCESSING]
        assert len(processing_calls) >= 1
    
    @patch("app.tasks.video_tasks.process_video")
    @patch("app.tasks.video_tasks.RedisJobManager")
    def test_updates_status_to_completed_on_success(self, mock_manager_class, mock_process):
        """
        Test that task updates job status to completed on success.
        
        Validates: Requirements 5.3
        """
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_process.return_value = "/outputs/video.mp4"
        
        task = process_video_task
        task._job_manager = mock_manager
        
        result = task.apply(args=(
            "job-123",
            "video-456",
            "/uploads/video.mp4",
            "/outputs/video.mp4",
            "/captions/video.srt",
            None,
            None,
            None
        )).get()
        
        # Verify final status is completed
        final_call = mock_manager.update_status.call_args_list[-1]
        assert final_call[1]["status"] == JobStatus.COMPLETED
        assert final_call[1]["progress"] == 100
    
    @patch("app.tasks.video_tasks.process_video")
    @patch("app.tasks.video_tasks.RedisJobManager")
    def test_returns_result_dict(self, mock_manager_class, mock_process):
        """
        Test that task returns correct result dictionary.
        
        Validates: Requirements 5.3
        """
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_process.return_value = "/outputs/video.mp4"
        
        task = process_video_task
        task._job_manager = mock_manager
        
        result = task.apply(args=(
            "job-123",
            "video-456",
            "/uploads/video.mp4",
            "/outputs/video.mp4",
            "/captions/video.srt",
            None,
            None,
            None
        )).get()
        
        assert result["job_id"] == "job-123"
        assert result["video_id"] == "video-456"
        assert result["result_path"] == "/outputs/video.mp4"
    
    @patch("app.tasks.video_tasks.process_video")
    @patch("app.tasks.video_tasks.RedisJobManager")
    def test_handles_watermark_with_position_and_opacity(self, mock_manager_class, mock_process):
        """
        Test that task correctly passes watermark parameters.
        
        Validates: Requirements 5.3
        """
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_process.return_value = "/outputs/video.mp4"
        
        task = process_video_task
        task._job_manager = mock_manager
        
        result = task.apply(args=(
            "job-123",
            "video-456",
            "/uploads/video.mp4",
            "/outputs/video.mp4",
            None,
            "/watermarks/logo.png",
            "top-left",
            0.8
        )).get()
        
        # Verify process_video was called with correct parameters
        mock_process.assert_called_once()
        call_kwargs = mock_process.call_args[1]
        assert call_kwargs["watermark_path"] == "/watermarks/logo.png"
        assert call_kwargs["watermark_position"] == WatermarkPosition.TOP_LEFT
        assert call_kwargs["watermark_opacity"] == 0.8


class TestTaskRouting:
    """Test suite for task routing configuration."""
    
    def test_caption_task_routed_to_captions_queue(self):
        """Test caption task is routed to captions queue."""
        routes = celery_app.conf.task_routes
        assert routes["app.tasks.video_tasks.generate_captions_task"]["queue"] == "captions"
    
    def test_watermark_task_routed_to_watermarks_queue(self):
        """Test watermark task is routed to watermarks queue."""
        routes = celery_app.conf.task_routes
        assert routes["app.tasks.video_tasks.apply_watermark_task"]["queue"] == "watermarks"
    
    def test_process_task_routed_to_processing_queue(self):
        """Test process task is routed to processing queue."""
        routes = celery_app.conf.task_routes
        assert routes["app.tasks.video_tasks.process_video_task"]["queue"] == "processing"
    
    def test_default_queue_is_default(self):
        """Test default queue is 'default'."""
        assert celery_app.conf.task_default_queue == "default"
