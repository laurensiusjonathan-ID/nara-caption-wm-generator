"""
Unit tests for caption formatting service.

Tests the caption formatter functions for SRT and VTT format generation,
parsing, timestamp validation, and round-trip conversions.

Validates: Requirements 2.3, 2.4, 2.5, 3.2, 3.3
"""

import pytest
from app.services.caption_formatter import (
    format_to_srt,
    format_to_vtt,
    parse_srt,
    parse_vtt,
    validate_timestamps,
    CaptionSegment,
    CaptionFormatError,
    TimestampValidationError,
    _format_srt_timestamp,
    _format_vtt_timestamp,
    _parse_srt_timestamp,
    _parse_vtt_timestamp,
)


class TestTimestampFormatting:
    """Tests for timestamp formatting functions."""
    
    def test_format_srt_timestamp_zero(self):
        """Test SRT timestamp formatting for zero seconds."""
        assert _format_srt_timestamp(0.0) == "00:00:00,000"
    
    def test_format_srt_timestamp_with_milliseconds(self):
        """Test SRT timestamp formatting with milliseconds."""
        assert _format_srt_timestamp(1.5) == "00:00:01,500"
    
    def test_format_srt_timestamp_with_minutes(self):
        """Test SRT timestamp formatting with minutes."""
        assert _format_srt_timestamp(65.123) == "00:01:05,123"
    
    def test_format_srt_timestamp_with_hours(self):
        """Test SRT timestamp formatting with hours."""
        assert _format_srt_timestamp(3661.456) == "01:01:01,456"
    
    def test_format_vtt_timestamp_zero(self):
        """Test VTT timestamp formatting for zero seconds."""
        assert _format_vtt_timestamp(0.0) == "00:00:00.000"
    
    def test_format_vtt_timestamp_with_milliseconds(self):
        """Test VTT timestamp formatting with milliseconds."""
        assert _format_vtt_timestamp(1.5) == "00:00:01.500"
    
    def test_format_vtt_timestamp_with_minutes(self):
        """Test VTT timestamp formatting with minutes."""
        assert _format_vtt_timestamp(65.123) == "00:01:05.123"
    
    def test_format_vtt_timestamp_with_hours(self):
        """Test VTT timestamp formatting with hours."""
        assert _format_vtt_timestamp(3661.456) == "01:01:01.456"


class TestTimestampParsing:
    """Tests for timestamp parsing functions."""
    
    def test_parse_srt_timestamp_zero(self):
        """Test parsing SRT timestamp for zero."""
        assert _parse_srt_timestamp("00:00:00,000") == 0.0
    
    def test_parse_srt_timestamp_with_milliseconds(self):
        """Test parsing SRT timestamp with milliseconds."""
        assert _parse_srt_timestamp("00:00:01,500") == 1.5
    
    def test_parse_srt_timestamp_with_minutes(self):
        """Test parsing SRT timestamp with minutes."""
        assert _parse_srt_timestamp("00:01:05,123") == 65.123
    
    def test_parse_srt_timestamp_with_hours(self):
        """Test parsing SRT timestamp with hours."""
        assert _parse_srt_timestamp("01:01:01,456") == 3661.456
    
    def test_parse_srt_timestamp_invalid_format(self):
        """Test parsing invalid SRT timestamp raises error."""
        with pytest.raises(CaptionFormatError):
            _parse_srt_timestamp("invalid")
    
    def test_parse_vtt_timestamp_zero(self):
        """Test parsing VTT timestamp for zero."""
        assert _parse_vtt_timestamp("00:00:00.000") == 0.0
    
    def test_parse_vtt_timestamp_with_milliseconds(self):
        """Test parsing VTT timestamp with milliseconds."""
        assert _parse_vtt_timestamp("00:00:01.500") == 1.5
    
    def test_parse_vtt_timestamp_with_minutes(self):
        """Test parsing VTT timestamp with minutes."""
        assert _parse_vtt_timestamp("00:01:05.123") == 65.123
    
    def test_parse_vtt_timestamp_with_hours(self):
        """Test parsing VTT timestamp with hours."""
        assert _parse_vtt_timestamp("01:01:01.456") == 3661.456
    
    def test_parse_vtt_timestamp_invalid_format(self):
        """Test parsing invalid VTT timestamp raises error."""
        with pytest.raises(CaptionFormatError):
            _parse_vtt_timestamp("invalid")


class TestTimestampValidation:
    """Tests for timestamp validation function."""
    
    def test_validate_empty_segments(self):
        """Test validation passes for empty segment list."""
        validate_timestamps([])
    
    def test_validate_single_valid_segment(self):
        """Test validation passes for single valid segment."""
        segments = [CaptionSegment(start=0.0, end=2.5, text="Hello")]
        validate_timestamps(segments)
    
    def test_validate_multiple_valid_segments(self):
        """Test validation passes for multiple valid segments."""
        segments = [
            CaptionSegment(start=0.0, end=2.5, text="Hello"),
            CaptionSegment(start=2.5, end=5.0, text="World"),
            CaptionSegment(start=5.0, end=7.5, text="Test"),
        ]
        validate_timestamps(segments)
    
    def test_validate_start_equals_end_raises_error(self):
        """Test validation fails when start equals end."""
        segments = [CaptionSegment(start=2.5, end=2.5, text="Hello")]
        with pytest.raises(TimestampValidationError) as exc_info:
            validate_timestamps(segments)
        assert "start time" in str(exc_info.value)
        assert "must be less than" in str(exc_info.value)
    
    def test_validate_start_greater_than_end_raises_error(self):
        """Test validation fails when start is greater than end."""
        segments = [CaptionSegment(start=5.0, end=2.5, text="Hello")]
        with pytest.raises(TimestampValidationError) as exc_info:
            validate_timestamps(segments)
        assert "start time" in str(exc_info.value)
    
    def test_validate_overlapping_segments_raises_error(self):
        """Test validation fails for overlapping segments."""
        segments = [
            CaptionSegment(start=0.0, end=3.0, text="Hello"),
            CaptionSegment(start=2.0, end=5.0, text="World"),
        ]
        with pytest.raises(TimestampValidationError) as exc_info:
            validate_timestamps(segments)
        assert "overlaps" in str(exc_info.value)
    
    def test_validate_non_chronological_raises_error(self):
        """Test validation fails for non-chronological segments."""
        segments = [
            CaptionSegment(start=5.0, end=7.0, text="Second"),
            CaptionSegment(start=0.0, end=2.0, text="First"),
        ]
        with pytest.raises(TimestampValidationError) as exc_info:
            validate_timestamps(segments)
        assert "overlaps" in str(exc_info.value)


class TestFormatToSrt:
    """Tests for format_to_srt function."""
    
    def test_format_single_segment(self):
        """Test formatting a single segment to SRT."""
        segments = [{'start': 0.0, 'end': 2.5, 'text': 'Hello'}]
        result = format_to_srt(segments)
        
        assert "1\n" in result
        assert "00:00:00,000 --> 00:00:02,500" in result
        assert "Hello" in result
    
    def test_format_multiple_segments(self):
        """Test formatting multiple segments to SRT."""
        segments = [
            {'start': 0.0, 'end': 2.5, 'text': 'Hello'},
            {'start': 2.5, 'end': 5.0, 'text': 'World'},
        ]
        result = format_to_srt(segments)
        
        assert "1\n" in result
        assert "2\n" in result
        assert "00:00:00,000 --> 00:00:02,500" in result
        assert "00:00:02,500 --> 00:00:05,000" in result
        assert "Hello" in result
        assert "World" in result
    
    def test_format_srt_uses_comma_for_milliseconds(self):
        """Test that SRT format uses comma for milliseconds separator."""
        segments = [{'start': 1.5, 'end': 5.75, 'text': 'Test'}]
        result = format_to_srt(segments)
        
        assert ",500" in result
        assert ",750" in result
        assert ".500" not in result
        assert ".750" not in result
    
    def test_format_srt_sequential_indices(self):
        """Test that SRT indices are sequential starting at 1."""
        segments = [
            {'start': 0.0, 'end': 1.0, 'text': 'One'},
            {'start': 1.0, 'end': 2.0, 'text': 'Two'},
            {'start': 2.0, 'end': 3.0, 'text': 'Three'},
        ]
        result = format_to_srt(segments)
        lines = result.split('\n')
        
        indices = [line for line in lines if line.strip().isdigit()]
        assert indices == ['1', '2', '3']
    
    def test_format_srt_invalid_timestamps_raises_error(self):
        """Test that invalid timestamps raise TimestampValidationError."""
        segments = [{'start': 5.0, 'end': 2.0, 'text': 'Invalid'}]
        with pytest.raises(TimestampValidationError):
            format_to_srt(segments)


class TestFormatToVtt:
    """Tests for format_to_vtt function."""
    
    def test_format_vtt_has_webvtt_header(self):
        """Test that VTT format starts with WEBVTT header."""
        segments = [{'start': 0.0, 'end': 2.5, 'text': 'Hello'}]
        result = format_to_vtt(segments)
        
        assert result.startswith("WEBVTT")
    
    def test_format_single_segment(self):
        """Test formatting a single segment to VTT."""
        segments = [{'start': 0.0, 'end': 2.5, 'text': 'Hello'}]
        result = format_to_vtt(segments)
        
        assert "WEBVTT" in result
        assert "00:00:00.000 --> 00:00:02.500" in result
        assert "Hello" in result
    
    def test_format_multiple_segments(self):
        """Test formatting multiple segments to VTT."""
        segments = [
            {'start': 0.0, 'end': 2.5, 'text': 'Hello'},
            {'start': 2.5, 'end': 5.0, 'text': 'World'},
        ]
        result = format_to_vtt(segments)
        
        assert "00:00:00.000 --> 00:00:02.500" in result
        assert "00:00:02.500 --> 00:00:05.000" in result
        assert "Hello" in result
        assert "World" in result
    
    def test_format_vtt_uses_period_for_milliseconds(self):
        """Test that VTT format uses period for milliseconds separator."""
        segments = [{'start': 1.5, 'end': 5.75, 'text': 'Test'}]
        result = format_to_vtt(segments)
        
        assert ".500" in result
        assert ".750" in result
        assert ",500" not in result
        assert ",750" not in result
    
    def test_format_vtt_invalid_timestamps_raises_error(self):
        """Test that invalid timestamps raise TimestampValidationError."""
        segments = [{'start': 5.0, 'end': 2.0, 'text': 'Invalid'}]
        with pytest.raises(TimestampValidationError):
            format_to_vtt(segments)


class TestParseSrt:
    """Tests for parse_srt function."""
    
    def test_parse_single_segment(self):
        """Test parsing a single SRT segment."""
        srt_content = '''1
00:00:00,000 --> 00:00:02,500
Hello
'''
        segments = parse_srt(srt_content)
        
        assert len(segments) == 1
        assert segments[0]['start'] == 0.0
        assert segments[0]['end'] == 2.5
        assert segments[0]['text'] == 'Hello'
    
    def test_parse_multiple_segments(self):
        """Test parsing multiple SRT segments."""
        srt_content = '''1
00:00:00,000 --> 00:00:02,500
Hello

2
00:00:02,500 --> 00:00:05,000
World
'''
        segments = parse_srt(srt_content)
        
        assert len(segments) == 2
        assert segments[0]['text'] == 'Hello'
        assert segments[1]['text'] == 'World'
    
    def test_parse_multiline_text(self):
        """Test parsing SRT with multiline text."""
        srt_content = '''1
00:00:00,000 --> 00:00:02,500
Hello
World
'''
        segments = parse_srt(srt_content)
        
        assert len(segments) == 1
        assert segments[0]['text'] == 'Hello\nWorld'
    
    def test_parse_empty_content_raises_error(self):
        """Test parsing empty content raises error."""
        with pytest.raises(CaptionFormatError) as exc_info:
            parse_srt("")
        assert "Empty" in str(exc_info.value)
    
    def test_parse_invalid_index_raises_error(self):
        """Test parsing invalid index raises error."""
        srt_content = '''abc
00:00:00,000 --> 00:00:02,500
Hello
'''
        with pytest.raises(CaptionFormatError) as exc_info:
            parse_srt(srt_content)
        assert "Invalid segment index" in str(exc_info.value)


class TestParseVtt:
    """Tests for parse_vtt function."""
    
    def test_parse_single_segment(self):
        """Test parsing a single VTT segment."""
        vtt_content = '''WEBVTT

00:00:00.000 --> 00:00:02.500
Hello
'''
        segments = parse_vtt(vtt_content)
        
        assert len(segments) == 1
        assert segments[0]['start'] == 0.0
        assert segments[0]['end'] == 2.5
        assert segments[0]['text'] == 'Hello'
    
    def test_parse_multiple_segments(self):
        """Test parsing multiple VTT segments."""
        vtt_content = '''WEBVTT

00:00:00.000 --> 00:00:02.500
Hello

00:00:02.500 --> 00:00:05.000
World
'''
        segments = parse_vtt(vtt_content)
        
        assert len(segments) == 2
        assert segments[0]['text'] == 'Hello'
        assert segments[1]['text'] == 'World'
    
    def test_parse_multiline_text(self):
        """Test parsing VTT with multiline text."""
        vtt_content = '''WEBVTT

00:00:00.000 --> 00:00:02.500
Hello
World
'''
        segments = parse_vtt(vtt_content)
        
        assert len(segments) == 1
        assert segments[0]['text'] == 'Hello\nWorld'
    
    def test_parse_with_cue_identifier(self):
        """Test parsing VTT with optional cue identifiers."""
        vtt_content = '''WEBVTT

cue-1
00:00:00.000 --> 00:00:02.500
Hello
'''
        segments = parse_vtt(vtt_content)
        
        assert len(segments) == 1
        assert segments[0]['text'] == 'Hello'
    
    def test_parse_missing_header_raises_error(self):
        """Test parsing VTT without WEBVTT header raises error."""
        vtt_content = '''00:00:00.000 --> 00:00:02.500
Hello
'''
        with pytest.raises(CaptionFormatError) as exc_info:
            parse_vtt(vtt_content)
        assert "WEBVTT" in str(exc_info.value)
    
    def test_parse_empty_content_raises_error(self):
        """Test parsing empty content raises error."""
        with pytest.raises(CaptionFormatError) as exc_info:
            parse_vtt("")
        assert "Empty" in str(exc_info.value)
