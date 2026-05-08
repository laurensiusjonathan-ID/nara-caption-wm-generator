"""
Tests for the watermark applicator module.

Tests PNG validation, opacity validation, and position validation.
"""

import pytest
from app.services.watermark_applicator import (
    validate_png_format,
    validate_opacity,
    validate_watermark_position,
    WatermarkValidationError,
    WatermarkApplicationError,
    WatermarkMetadata,
    MIN_OPACITY,
    MAX_OPACITY,
    DEFAULT_OPACITY,
    DEFAULT_POSITION,
    _get_overlay_position,
)
from app.models.enums import WatermarkPosition


class TestValidatePngFormat:
    """Tests for validate_png_format function."""
    
    def test_valid_png_lowercase(self):
        """PNG extension should be accepted (lowercase)."""
        assert validate_png_format("image.png") is True
    
    def test_valid_png_uppercase(self):
        """PNG extension should be accepted (uppercase)."""
        assert validate_png_format("image.PNG") is True
    
    def test_valid_png_mixed_case(self):
        """PNG extension should be accepted (mixed case)."""
        assert validate_png_format("image.Png") is True
    
    def test_invalid_jpg(self):
        """JPG format should be rejected."""
        assert validate_png_format("image.jpg") is False
    
    def test_invalid_jpeg(self):
        """JPEG format should be rejected."""
        assert validate_png_format("image.jpeg") is False
    
    def test_invalid_gif(self):
        """GIF format should be rejected."""
        assert validate_png_format("image.gif") is False
    
    def test_invalid_webp(self):
        """WebP format should be rejected."""
        assert validate_png_format("image.webp") is False
    
    def test_empty_filename(self):
        """Empty filename should be rejected."""
        assert validate_png_format("") is False
    
    def test_no_extension(self):
        """Filename without extension should be rejected."""
        assert validate_png_format("image") is False
    
    def test_path_with_directories(self):
        """Full path with directories should work."""
        assert validate_png_format("/path/to/image.png") is True
        assert validate_png_format("C:\\images\\logo.png") is True


class TestValidateOpacity:
    """Tests for validate_opacity function."""
    
    def test_valid_zero(self):
        """Opacity 0.0 should be valid."""
        assert validate_opacity(0.0) is True
    
    def test_valid_one(self):
        """Opacity 1.0 should be valid."""
        assert validate_opacity(1.0) is True
    
    def test_valid_half(self):
        """Opacity 0.5 should be valid."""
        assert validate_opacity(0.5) is True
    
    def test_valid_quarter(self):
        """Opacity 0.25 should be valid."""
        assert validate_opacity(0.25) is True
    
    def test_invalid_negative(self):
        """Negative opacity should be invalid."""
        assert validate_opacity(-0.1) is False
    
    def test_invalid_greater_than_one(self):
        """Opacity > 1.0 should be invalid."""
        assert validate_opacity(1.1) is False
    
    def test_invalid_large_value(self):
        """Large opacity value should be invalid."""
        assert validate_opacity(100.0) is False


class TestValidateWatermarkPosition:
    """Tests for validate_watermark_position function."""
    
    def test_valid_top_left(self):
        """top-left should be valid."""
        assert validate_watermark_position("top-left") is True
    
    def test_valid_top_right(self):
        """top-right should be valid."""
        assert validate_watermark_position("top-right") is True
    
    def test_valid_bottom_left(self):
        """bottom-left should be valid."""
        assert validate_watermark_position("bottom-left") is True
    
    def test_valid_bottom_right(self):
        """bottom-right should be valid."""
        assert validate_watermark_position("bottom-right") is True
    
    def test_valid_center(self):
        """center should be valid."""
        assert validate_watermark_position("center") is True
    
    def test_invalid_position(self):
        """Invalid position should be rejected."""
        assert validate_watermark_position("middle") is False
        assert validate_watermark_position("left") is False
        assert validate_watermark_position("right") is False
    
    def test_case_sensitive(self):
        """Position validation should be case-sensitive."""
        assert validate_watermark_position("TOP-LEFT") is False
        assert validate_watermark_position("Center") is False


class TestGetOverlayPosition:
    """Tests for _get_overlay_position function."""
    
    def test_top_left(self):
        """Top-left should return correct expression."""
        result = _get_overlay_position(WatermarkPosition.TOP_LEFT)
        assert "10:10" in result
    
    def test_top_right(self):
        """Top-right should return correct expression."""
        result = _get_overlay_position(WatermarkPosition.TOP_RIGHT)
        assert "W-w-10" in result
    
    def test_bottom_left(self):
        """Bottom-left should return correct expression."""
        result = _get_overlay_position(WatermarkPosition.BOTTOM_LEFT)
        assert "H-h-10" in result
    
    def test_bottom_right(self):
        """Bottom-right should return correct expression."""
        result = _get_overlay_position(WatermarkPosition.BOTTOM_RIGHT)
        assert "W-w-10" in result
        assert "H-h-10" in result
    
    def test_center(self):
        """Center should return correct expression."""
        result = _get_overlay_position(WatermarkPosition.CENTER)
        assert "(W-w)/2" in result
        assert "(H-h)/2" in result


class TestWatermarkMetadata:
    """Tests for WatermarkMetadata dataclass."""
    
    def test_create_metadata(self):
        """Should create metadata with all fields."""
        metadata = WatermarkMetadata(width=100, height=50, has_alpha=True)
        assert metadata.width == 100
        assert metadata.height == 50
        assert metadata.has_alpha is True
    
    def test_default_has_alpha(self):
        """has_alpha should default to True."""
        metadata = WatermarkMetadata(width=100, height=50)
        assert metadata.has_alpha is True


class TestConstants:
    """Tests for module constants."""
    
    def test_min_opacity(self):
        """MIN_OPACITY should be 0.0."""
        assert MIN_OPACITY == 0.0
    
    def test_max_opacity(self):
        """MAX_OPACITY should be 1.0."""
        assert MAX_OPACITY == 1.0
    
    def test_default_opacity(self):
        """DEFAULT_OPACITY should be 0.5."""
        assert DEFAULT_OPACITY == 0.5
    
    def test_default_position(self):
        """DEFAULT_POSITION should be BOTTOM_RIGHT."""
        assert DEFAULT_POSITION == WatermarkPosition.BOTTOM_RIGHT
