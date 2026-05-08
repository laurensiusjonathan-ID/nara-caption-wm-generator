"""
Tests for the caption generator module.

Tests audio extraction and caption generation functionality.
"""

import pytest
from app.services.caption_generator import (
    TranscriptionSegment,
    TranscriptionWord,
    _build_segments_from_words,
    segments_to_caption_content,
    AudioExtractionError,
    CaptionGenerationError,
)
from app.models.enums import CaptionFormat


class TestTranscriptionSegment:
    """Tests for TranscriptionSegment dataclass."""
    
    def test_create_segment(self):
        """Should create a segment with all fields."""
        segment = TranscriptionSegment(start=0.0, end=2.5, text="Hello world")
        assert segment.start == 0.0
        assert segment.end == 2.5
        assert segment.text == "Hello world"


class TestSegmentsToCaptionContent:
    """Tests for segments_to_caption_content function."""
    
    def test_empty_segments_returns_empty_string(self):
        """Empty segment list should return empty string."""
        result = segments_to_caption_content([])
        assert result == ""
    
    def test_single_segment_srt(self):
        """Single segment should format correctly to SRT."""
        segments = [TranscriptionSegment(start=0.0, end=2.5, text="Hello")]
        result = segments_to_caption_content(segments, CaptionFormat.SRT)
        
        assert "1" in result
        assert "00:00:00,000 --> 00:00:02,500" in result
        assert "Hello" in result
    
    def test_single_segment_vtt(self):
        """Single segment should format correctly to VTT."""
        segments = [TranscriptionSegment(start=0.0, end=2.5, text="Hello")]
        result = segments_to_caption_content(segments, CaptionFormat.VTT)
        
        assert result.startswith("WEBVTT")
        assert "00:00:00.000 --> 00:00:02.500" in result
        assert "Hello" in result
    
    def test_multiple_segments_srt(self):
        """Multiple segments should format correctly to SRT."""
        segments = [
            TranscriptionSegment(start=0.0, end=2.5, text="First"),
            TranscriptionSegment(start=2.5, end=5.0, text="Second"),
        ]
        result = segments_to_caption_content(segments, CaptionFormat.SRT)
        
        assert "1" in result
        assert "2" in result
        assert "First" in result
        assert "Second" in result
    
    def test_multiple_segments_vtt(self):
        """Multiple segments should format correctly to VTT."""
        segments = [
            TranscriptionSegment(start=0.0, end=2.5, text="First"),
            TranscriptionSegment(start=2.5, end=5.0, text="Second"),
        ]
        result = segments_to_caption_content(segments, CaptionFormat.VTT)
        
        assert result.startswith("WEBVTT")
        assert "First" in result
        assert "Second" in result
    
    def test_default_format_is_srt(self):
        """Default format should be SRT."""
        segments = [TranscriptionSegment(start=0.0, end=2.5, text="Test")]
        result = segments_to_caption_content(segments)
        
        # SRT uses comma for milliseconds, VTT uses period
        assert "," in result
        assert not result.startswith("WEBVTT")


class TestBuildSegmentsFromWords:
    """Tests word-timestamp chunking helper for better sync precision."""

    def test_build_segments_from_words_splits_on_gap(self):
        words = [
            TranscriptionWord(start=0.00, end=0.20, text="halo"),
            TranscriptionWord(start=0.22, end=0.40, text="saya"),
            TranscriptionWord(start=1.10, end=1.35, text="iril"),
        ]

        result = _build_segments_from_words(words, max_gap=0.4)

        assert len(result) == 2
        assert result[0].text == "halo saya"
        assert result[1].text == "iril"

    def test_build_segments_from_words_splits_on_char_limit(self):
        words = [
            TranscriptionWord(start=0.0, end=0.1, text="ini"),
            TranscriptionWord(start=0.1, end=0.2, text="adalah"),
            TranscriptionWord(start=0.2, end=0.3, text="kalimat"),
            TranscriptionWord(start=0.3, end=0.4, text="sangat"),
            TranscriptionWord(start=0.4, end=0.5, text="panjang"),
        ]

        result = _build_segments_from_words(words, max_chars=15)

        assert len(result) >= 2
        assert all(seg.text for seg in result)


class TestAudioExtractionError:
    """Tests for AudioExtractionError exception."""
    
    def test_exception_message(self):
        """Should preserve error message."""
        error = AudioExtractionError("Test error message")
        assert str(error) == "Test error message"


class TestCaptionGenerationError:
    """Tests for CaptionGenerationError exception."""
    
    def test_exception_message(self):
        """Should preserve error message."""
        error = CaptionGenerationError("Test error message")
        assert str(error) == "Test error message"
