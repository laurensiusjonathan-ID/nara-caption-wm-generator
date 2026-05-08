"""
Caption formatting service for the Video Caption Watermark API.

This module provides functions for formatting and parsing caption files
in SRT (SubRip) and VTT (WebVTT) formats. It handles timestamp conversion,
format validation, and round-trip parsing/formatting operations.

Validates: Requirements 2.3, 2.4, 2.5, 3.2, 3.3
"""

from typing import List, Dict, Tuple
import re
from dataclasses import dataclass


@dataclass
class CaptionSegment:
    """
    Represents a single caption segment with timing and text.
    
    Attributes:
        start: Start time in seconds
        end: End time in seconds
        text: Caption text content
    """
    start: float
    end: float
    text: str


class CaptionFormatError(Exception):
    """Raised when caption format is invalid or cannot be parsed."""
    pass


class TimestampValidationError(Exception):
    """Raised when caption timestamps are invalid."""
    pass


def validate_timestamps(segments: List[CaptionSegment]) -> None:
    """
    Validate caption timestamps for correctness.
    
    Ensures:
    1. Each segment has start_time < end_time
    2. Segments are in chronological order
    3. No overlapping time ranges
    
    Args:
        segments: List of caption segments to validate
        
    Raises:
        TimestampValidationError: If validation fails
        
    Validates: Requirements 2.3
    """
    if not segments:
        return
    
    for i, segment in enumerate(segments):
        # Check start < end
        if segment.start >= segment.end:
            raise TimestampValidationError(
                f"Segment {i + 1}: start time ({segment.start}s) must be less than "
                f"end time ({segment.end}s)"
            )
        
        # Check chronological order and no overlaps
        if i > 0:
            prev_segment = segments[i - 1]
            if segment.start < prev_segment.end:
                raise TimestampValidationError(
                    f"Segment {i + 1}: start time ({segment.start}s) overlaps with "
                    f"previous segment end time ({prev_segment.end}s)"
                )


def _format_srt_timestamp(seconds: float) -> str:
    """
    Format seconds to SRT timestamp format (HH:MM:SS,mmm).
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted timestamp string
        
    Example:
        >>> _format_srt_timestamp(65.5)
        '00:01:05,500'
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _format_vtt_timestamp(seconds: float) -> str:
    """
    Format seconds to VTT timestamp format (HH:MM:SS.mmm).
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted timestamp string
        
    Example:
        >>> _format_vtt_timestamp(65.5)
        '00:01:05.500'
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def _parse_srt_timestamp(timestamp: str) -> float:
    """
    Parse SRT timestamp format (HH:MM:SS,mmm) to seconds.
    
    Args:
        timestamp: SRT formatted timestamp
        
    Returns:
        Time in seconds
        
    Raises:
        CaptionFormatError: If timestamp format is invalid
    """
    pattern = r'(\d{2}):(\d{2}):(\d{2}),(\d{3})'
    match = re.match(pattern, timestamp.strip())
    
    if not match:
        raise CaptionFormatError(f"Invalid SRT timestamp format: {timestamp}")
    
    hours, minutes, seconds, millis = map(int, match.groups())
    return hours * 3600 + minutes * 60 + seconds + millis / 1000


def _parse_vtt_timestamp(timestamp: str) -> float:
    """
    Parse VTT timestamp format (HH:MM:SS.mmm) to seconds.
    
    Args:
        timestamp: VTT formatted timestamp
        
    Returns:
        Time in seconds
        
    Raises:
        CaptionFormatError: If timestamp format is invalid
    """
    pattern = r'(\d{2}):(\d{2}):(\d{2})\.(\d{3})'
    match = re.match(pattern, timestamp.strip())
    
    if not match:
        raise CaptionFormatError(f"Invalid VTT timestamp format: {timestamp}")
    
    hours, minutes, seconds, millis = map(int, match.groups())
    return hours * 3600 + minutes * 60 + seconds + millis / 1000


def format_to_srt(segments: List[Dict]) -> str:
    """
    Format caption segments to SRT (SubRip) format.
    
    SRT format specification:
    - Sequential index numbers starting at 1
    - Timestamps in HH:MM:SS,mmm format with --> separator
    - Text content
    - Blank line between segments
    
    Args:
        segments: List of segment dictionaries with 'start', 'end', and 'text' keys
        
    Returns:
        Formatted SRT content as string
        
    Raises:
        TimestampValidationError: If timestamps are invalid
        
    Example:
        >>> segments = [
        ...     {'start': 0.0, 'end': 2.5, 'text': 'Hello'},
        ...     {'start': 2.5, 'end': 5.0, 'text': 'World'}
        ... ]
        >>> print(format_to_srt(segments))
        1
        00:00:00,000 --> 00:00:02,500
        Hello
        
        2
        00:00:02,500 --> 00:00:05,000
        World
        
    Validates: Requirements 2.4
    """
    # Convert to CaptionSegment objects for validation
    caption_segments = [
        CaptionSegment(start=s['start'], end=s['end'], text=s['text'])
        for s in segments
    ]
    
    # Validate timestamps
    validate_timestamps(caption_segments)
    
    # Format to SRT
    srt_lines = []
    for i, segment in enumerate(caption_segments, start=1):
        srt_lines.append(str(i))
        srt_lines.append(
            f"{_format_srt_timestamp(segment.start)} --> "
            f"{_format_srt_timestamp(segment.end)}"
        )
        srt_lines.append(segment.text)
        srt_lines.append("")  # Blank line between segments
    
    return "\n".join(srt_lines)


def format_to_vtt(segments: List[Dict]) -> str:
    """
    Format caption segments to VTT (WebVTT) format.
    
    VTT format specification:
    - Starts with "WEBVTT" header
    - Blank line after header
    - Timestamps in HH:MM:SS.mmm format with --> separator
    - Text content
    - Blank line between segments
    
    Args:
        segments: List of segment dictionaries with 'start', 'end', and 'text' keys
        
    Returns:
        Formatted VTT content as string
        
    Raises:
        TimestampValidationError: If timestamps are invalid
        
    Example:
        >>> segments = [
        ...     {'start': 0.0, 'end': 2.5, 'text': 'Hello'},
        ...     {'start': 2.5, 'end': 5.0, 'text': 'World'}
        ... ]
        >>> print(format_to_vtt(segments))
        WEBVTT
        
        00:00:00.000 --> 00:00:02.500
        Hello
        
        00:00:02.500 --> 00:00:05.000
        World
        
    Validates: Requirements 2.5
    """
    # Convert to CaptionSegment objects for validation
    caption_segments = [
        CaptionSegment(start=s['start'], end=s['end'], text=s['text'])
        for s in segments
    ]
    
    # Validate timestamps
    validate_timestamps(caption_segments)
    
    # Format to VTT
    vtt_lines = ["WEBVTT", ""]  # Header and blank line
    
    for segment in caption_segments:
        vtt_lines.append(
            f"{_format_vtt_timestamp(segment.start)} --> "
            f"{_format_vtt_timestamp(segment.end)}"
        )
        vtt_lines.append(segment.text)
        vtt_lines.append("")  # Blank line between segments
    
    return "\n".join(vtt_lines)


def parse_srt(content: str) -> List[Dict]:
    """
    Parse SRT format caption content into segments.
    
    Args:
        content: SRT formatted caption content
        
    Returns:
        List of segment dictionaries with 'start', 'end', and 'text' keys
        
    Raises:
        CaptionFormatError: If content is not valid SRT format
        
    Example:
        >>> srt_content = '''1
        ... 00:00:00,000 --> 00:00:02,500
        ... Hello
        ...
        ... 2
        ... 00:00:02,500 --> 00:00:05,000
        ... World
        ... '''
        >>> segments = parse_srt(srt_content)
        >>> len(segments)
        2
        >>> segments[0]['text']
        'Hello'
        
    Validates: Requirements 3.2, 3.3
    """
    if not content or not content.strip():
        raise CaptionFormatError("Empty caption content")
    
    segments = []
    lines = content.strip().split('\n')
    i = 0
    
    while i < len(lines):
        # Skip empty lines
        if not lines[i].strip():
            i += 1
            continue
        
        # Read index
        try:
            index = int(lines[i].strip())
        except (ValueError, IndexError):
            raise CaptionFormatError(f"Invalid segment index at line {i + 1}: {lines[i]}")
        
        i += 1
        if i >= len(lines):
            raise CaptionFormatError(f"Incomplete segment {index}: missing timestamp")
        
        # Read timestamp line
        timestamp_line = lines[i].strip()
        if '-->' not in timestamp_line:
            raise CaptionFormatError(
                f"Invalid timestamp format at line {i + 1}: {timestamp_line}"
            )
        
        try:
            start_str, end_str = timestamp_line.split('-->')
            start = _parse_srt_timestamp(start_str)
            end = _parse_srt_timestamp(end_str)
        except Exception as e:
            raise CaptionFormatError(
                f"Failed to parse timestamp at line {i + 1}: {str(e)}"
            )
        
        i += 1
        if i >= len(lines):
            raise CaptionFormatError(f"Incomplete segment {index}: missing text")
        
        # Read text (may be multiple lines)
        text_lines = []
        while i < len(lines) and lines[i].strip():
            text_lines.append(lines[i])
            i += 1
        
        if not text_lines:
            raise CaptionFormatError(f"Segment {index} has no text content")
        
        text = '\n'.join(text_lines)
        
        segments.append({
            'start': start,
            'end': end,
            'text': text
        })
    
    if not segments:
        raise CaptionFormatError("No valid segments found in SRT content")
    
    return segments


def parse_vtt(content: str) -> List[Dict]:
    """
    Parse VTT format caption content into segments.
    
    Args:
        content: VTT formatted caption content
        
    Returns:
        List of segment dictionaries with 'start', 'end', and 'text' keys
        
    Raises:
        CaptionFormatError: If content is not valid VTT format
        
    Example:
        >>> vtt_content = '''WEBVTT
        ...
        ... 00:00:00.000 --> 00:00:02.500
        ... Hello
        ...
        ... 00:00:02.500 --> 00:00:05.000
        ... World
        ... '''
        >>> segments = parse_vtt(vtt_content)
        >>> len(segments)
        2
        >>> segments[0]['text']
        'Hello'
        
    Validates: Requirements 3.2, 3.3
    """
    if not content or not content.strip():
        raise CaptionFormatError("Empty caption content")
    
    lines = content.strip().split('\n')
    
    # Check for WEBVTT header
    if not lines[0].strip().startswith('WEBVTT'):
        raise CaptionFormatError("Missing WEBVTT header")
    
    segments = []
    i = 1  # Skip header
    
    while i < len(lines):
        # Skip empty lines
        if not lines[i].strip():
            i += 1
            continue
        
        # Read timestamp line (VTT doesn't require index numbers)
        timestamp_line = lines[i].strip()
        
        # Skip optional cue identifiers (lines without -->)
        if '-->' not in timestamp_line:
            i += 1
            if i >= len(lines):
                break
            timestamp_line = lines[i].strip()
        
        if '-->' not in timestamp_line:
            raise CaptionFormatError(
                f"Invalid timestamp format at line {i + 1}: {timestamp_line}"
            )
        
        try:
            start_str, end_str = timestamp_line.split('-->')
            # Remove any cue settings after the end timestamp
            end_str = end_str.split()[0] if ' ' in end_str else end_str
            start = _parse_vtt_timestamp(start_str)
            end = _parse_vtt_timestamp(end_str)
        except Exception as e:
            raise CaptionFormatError(
                f"Failed to parse timestamp at line {i + 1}: {str(e)}"
            )
        
        i += 1
        if i >= len(lines):
            raise CaptionFormatError(f"Incomplete segment: missing text")
        
        # Read text (may be multiple lines)
        text_lines = []
        while i < len(lines) and lines[i].strip():
            text_lines.append(lines[i])
            i += 1
        
        if not text_lines:
            raise CaptionFormatError(f"Segment has no text content")
        
        text = '\n'.join(text_lines)
        
        segments.append({
            'start': start,
            'end': end,
            'text': text
        })
    
    if not segments:
        raise CaptionFormatError("No valid segments found in VTT content")
    
    return segments
