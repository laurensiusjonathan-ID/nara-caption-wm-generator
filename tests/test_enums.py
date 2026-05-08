"""
Unit tests for enum definitions.

Tests verify that enums are properly defined with correct values
and can be used in type checking and validation scenarios.
"""

import pytest
from app.models.enums import CaptionFormat, WatermarkPosition, JobStatus


class TestCaptionFormat:
    """Test CaptionFormat enum."""
    
    def test_caption_format_values(self):
        """Verify CaptionFormat has correct values."""
        assert CaptionFormat.SRT.value == "srt"
        assert CaptionFormat.VTT.value == "vtt"
    
    def test_caption_format_count(self):
        """Verify CaptionFormat has exactly 2 formats."""
        assert len(CaptionFormat) == 2
    
    def test_caption_format_string_comparison(self):
        """Verify CaptionFormat can be compared with strings."""
        assert CaptionFormat.SRT == "srt"
        assert CaptionFormat.VTT == "vtt"


class TestWatermarkPosition:
    """Test WatermarkPosition enum."""
    
    def test_watermark_position_values(self):
        """Verify WatermarkPosition has correct values."""
        assert WatermarkPosition.TOP_LEFT.value == "top-left"
        assert WatermarkPosition.TOP_RIGHT.value == "top-right"
        assert WatermarkPosition.BOTTOM_LEFT.value == "bottom-left"
        assert WatermarkPosition.BOTTOM_RIGHT.value == "bottom-right"
        assert WatermarkPosition.CENTER.value == "center"
    
    def test_watermark_position_count(self):
        """Verify WatermarkPosition has exactly 5 positions."""
        assert len(WatermarkPosition) == 5
    
    def test_watermark_position_string_comparison(self):
        """Verify WatermarkPosition can be compared with strings."""
        assert WatermarkPosition.TOP_LEFT == "top-left"
        assert WatermarkPosition.BOTTOM_RIGHT == "bottom-right"


class TestJobStatus:
    """Test JobStatus enum."""
    
    def test_job_status_values(self):
        """Verify JobStatus has correct values."""
        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.PROCESSING.value == "processing"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"
    
    def test_job_status_count(self):
        """Verify JobStatus has exactly 4 statuses."""
        assert len(JobStatus) == 4
    
    def test_job_status_string_comparison(self):
        """Verify JobStatus can be compared with strings."""
        assert JobStatus.PENDING == "pending"
        assert JobStatus.COMPLETED == "completed"
    
    def test_job_status_lifecycle_values_exist(self):
        """Verify all lifecycle states are defined."""
        # Ensure all expected lifecycle states exist
        lifecycle_states = {JobStatus.PENDING, JobStatus.PROCESSING, 
                          JobStatus.COMPLETED, JobStatus.FAILED}
        assert len(lifecycle_states) == 4
