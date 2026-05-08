"""
Tests for the video service module.

Tests video format validation and metadata extraction functionality.
"""

import pytest
from app.services.video_service import (
    validate_video_format,
    get_supported_formats,
    VideoValidationError,
    SUPPORTED_VIDEO_FORMATS,
)


class TestValidateVideoFormat:
    """Tests for validate_video_format function."""
    
    def test_valid_mp4_lowercase(self):
        """MP4 format should be accepted (lowercase)."""
        assert validate_video_format("video.mp4") is True
    
    def test_valid_mp4_uppercase(self):
        """MP4 format should be accepted (uppercase)."""
        assert validate_video_format("video.MP4") is True
    
    def test_valid_mov_lowercase(self):
        """MOV format should be accepted (lowercase)."""
        assert validate_video_format("video.mov") is True
    
    def test_valid_mov_uppercase(self):
        """MOV format should be accepted (uppercase)."""
        assert validate_video_format("video.MOV") is True
    
    def test_valid_avi_lowercase(self):
        """AVI format should be accepted (lowercase)."""
        assert validate_video_format("video.avi") is True
    
    def test_valid_avi_uppercase(self):
        """AVI format should be accepted (uppercase)."""
        assert validate_video_format("video.AVI") is True
    
    def test_valid_mixed_case(self):
        """Mixed case extensions should be accepted."""
        assert validate_video_format("video.Mp4") is True
        assert validate_video_format("video.MoV") is True
        assert validate_video_format("video.AVI") is True
    
    def test_invalid_format_wmv(self):
        """WMV format should be rejected."""
        assert validate_video_format("video.wmv") is False
    
    def test_invalid_format_mkv(self):
        """MKV format should be rejected."""
        assert validate_video_format("video.mkv") is False
    
    def test_invalid_format_webm(self):
        """WebM format should be rejected."""
        assert validate_video_format("video.webm") is False
    
    def test_empty_filename(self):
        """Empty filename should be rejected."""
        assert validate_video_format("") is False
    
    def test_no_extension(self):
        """Filename without extension should be rejected."""
        assert validate_video_format("video") is False
    
    def test_path_with_directories(self):
        """Full path with directories should work."""
        assert validate_video_format("/path/to/video.mp4") is True
        assert validate_video_format("C:\\videos\\test.avi") is True


class TestGetSupportedFormats:
    """Tests for get_supported_formats function."""
    
    def test_returns_list(self):
        """Should return a list."""
        result = get_supported_formats()
        assert isinstance(result, list)
    
    def test_contains_expected_formats(self):
        """Should contain mp4, mov, and avi."""
        result = get_supported_formats()
        assert "mp4" in result
        assert "mov" in result
        assert "avi" in result
    
    def test_matches_constant(self):
        """Should match SUPPORTED_VIDEO_FORMATS constant."""
        result = set(get_supported_formats())
        assert result == SUPPORTED_VIDEO_FORMATS
