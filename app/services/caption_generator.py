"""
Caption generator service for the Video Caption Watermark API.

This module provides functionality for generating captions from video audio
using faster-whisper for speech-to-text transcription with Indonesian language support.
It integrates with the caption formatter for output generation.

Validates: Requirements 2.1, 2.2, 2.3
"""

import os
import tempfile
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

import ffmpeg

from app.models.enums import CaptionFormat
from app.services.caption_formatter import (
    format_to_srt,
    format_to_vtt,
    CaptionSegment,
)


class CaptionGenerationError(Exception):
    """Raised when caption generation fails."""
    pass


class AudioExtractionError(Exception):
    """Raised when audio extraction from video fails."""
    pass


@dataclass
class TranscriptionSegment:
    """
    Represents a transcription segment from faster-whisper.
    
    Attributes:
        start: Start time in seconds
        end: End time in seconds
        text: Transcribed text content
    """
    start: float
    end: float
    text: str


@dataclass
class TranscriptionWord:
    """Represents a word-level timestamp from faster-whisper."""

    start: float
    end: float
    text: str


def _build_segments_from_words(
    words: List[TranscriptionWord],
    max_chars: int = 48,
    max_duration: float = 4.0,
    max_gap: float = 0.45,
) -> List[TranscriptionSegment]:
    """
    Build readable caption segments from word timestamps.

    Splits on:
    - long silence gaps
    - max character threshold
    - max segment duration
    """
    if not words:
        return []

    segments: List[TranscriptionSegment] = []
    current_words: List[TranscriptionWord] = [words[0]]

    def flush_current() -> None:
        nonlocal current_words
        if not current_words:
            return

        start = current_words[0].start
        end = current_words[-1].end
        if end <= start:
            end = start + 0.01
        text = " ".join(w.text.strip() for w in current_words if w.text.strip()).strip()
        if text:
            segments.append(TranscriptionSegment(start=start, end=end, text=text))
        current_words = []

    for idx in range(1, len(words)):
        prev_word = words[idx - 1]
        word = words[idx]

        gap = max(0.0, word.start - prev_word.end)
        current_text = " ".join(w.text.strip() for w in current_words if w.text.strip()).strip()
        candidate_text = (current_text + " " + word.text.strip()).strip() if current_text else word.text.strip()
        current_duration = current_words[-1].end - current_words[0].start

        should_split = (
            gap >= max_gap
            or len(candidate_text) > max_chars
            or current_duration >= max_duration
        )

        if should_split:
            flush_current()
            current_words = [word]
        else:
            current_words.append(word)

    flush_current()
    return segments


def extract_audio(video_path: str, output_path: Optional[str] = None) -> str:
    """
    Extract audio from a video file using FFmpeg.
    
    Extracts audio to WAV format suitable for transcription.
    
    Args:
        video_path: Path to the source video file
        output_path: Optional path for the output audio file.
                    If not provided, creates a temporary file.
        
    Returns:
        Path to the extracted audio file
        
    Raises:
        AudioExtractionError: If audio extraction fails
        
    Validates: Requirements 2.1
    """
    if not os.path.exists(video_path):
        raise AudioExtractionError(f"Video file not found: {video_path}")
    
    # Generate output path if not provided
    if output_path is None:
        temp_dir = tempfile.gettempdir()
        video_name = Path(video_path).stem
        output_path = os.path.join(temp_dir, f"{video_name}_audio.wav")
    
    try:
        # Extract audio using ffmpeg
        # Convert to 16kHz mono WAV for optimal whisper performance
        (
            ffmpeg
            .input(video_path)
            .output(
                output_path,
                acodec='pcm_s16le',
                ac=1,  # mono
                ar=16000  # 16kHz sample rate
            )
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg.Error as e:
        stderr = e.stderr.decode() if e.stderr else "Unknown error"
        raise AudioExtractionError(f"Failed to extract audio: {stderr}")
    
    if not os.path.exists(output_path):
        raise AudioExtractionError("Audio extraction produced no output file")
    
    return output_path


def transcribe_audio(
    audio_path: str,
    language: str = "id",
    model_size: str = "base"
) -> List[TranscriptionSegment]:
    """
    Transcribe audio file using faster-whisper.
    
    Args:
        audio_path: Path to the audio file (WAV format recommended)
        language: Language code for transcription (default: "id" for Indonesian)
        model_size: Whisper model size (tiny, base, small, medium, large)
        
    Returns:
        List of TranscriptionSegment objects with timestamps and text
        
    Raises:
        CaptionGenerationError: If transcription fails
        
    Validates: Requirements 2.2
    """
    if not os.path.exists(audio_path):
        raise CaptionGenerationError(f"Audio file not found: {audio_path}")
    
    try:
        from faster_whisper import WhisperModel
        
        # Load the model
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        
        # Transcribe with stable, caption-focused defaults.
        # Keep this close to Clipper-style behavior: word timestamps on,
        # minimal extra heuristics.
        segments_iter, info = model.transcribe(
            audio_path,
            language=language,
            beam_size=5,
            word_timestamps=True,
        )
        
        # Prefer word-level timing, then compose readable subtitle chunks.
        words: List[TranscriptionWord] = []
        fallback_segments: List[TranscriptionSegment] = []

        for segment in segments_iter:
            segment_text = segment.text.strip() if segment.text else ""
            if segment_text:
                fallback_segments.append(
                    TranscriptionSegment(start=segment.start, end=segment.end, text=segment_text)
                )

            seg_words = getattr(segment, "words", None) or []
            for w in seg_words:
                text = (getattr(w, "word", "") or "").strip()
                start = getattr(w, "start", None)
                end = getattr(w, "end", None)
                if text and start is not None and end is not None and end >= start:
                    words.append(TranscriptionWord(start=float(start), end=float(end), text=text))

        if words:
            segments = _build_segments_from_words(words)
        else:
            segments = fallback_segments

        return segments
        
    except ImportError:
        raise CaptionGenerationError(
            "faster-whisper is not installed. "
            "Install it with: pip install faster-whisper"
        )
    except Exception as e:
        raise CaptionGenerationError(f"Transcription failed: {str(e)}")


def generate_captions(
    video_path: str,
    output_path: str,
    language: str = "id",
    output_format: CaptionFormat = CaptionFormat.SRT,
    model_size: str = "base"
) -> str:
    """
    Generate captions from a video file.
    
    This is the main entry point for caption generation. It:
    1. Extracts audio from the video
    2. Transcribes the audio using faster-whisper
    3. Formats the transcription to the requested caption format
    4. Saves the captions to the output path
    
    Args:
        video_path: Path to the source video file
        output_path: Path where the caption file will be saved
        language: Language code for transcription (default: "id" for Indonesian)
        output_format: Caption format (SRT or VTT)
        model_size: Whisper model size
        
    Returns:
        Path to the generated caption file
        
    Raises:
        AudioExtractionError: If audio extraction fails
        CaptionGenerationError: If transcription or formatting fails
        
    Validates: Requirements 2.1, 2.2, 2.3
    """
    # Extract audio
    audio_path = extract_audio(video_path)
    
    try:
        # Transcribe audio
        segments = transcribe_audio(audio_path, language, model_size)
        
        if not segments:
            raise CaptionGenerationError("No speech detected in video")
        
        # Convert to format expected by caption formatter
        segment_dicts = [
            {'start': s.start, 'end': s.end, 'text': s.text}
            for s in segments
        ]
        
        # Format captions
        if output_format == CaptionFormat.VTT:
            caption_content = format_to_vtt(segment_dicts)
        else:
            # Default to SRT
            caption_content = format_to_srt(segment_dicts)
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # Write caption file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(caption_content)
        
        return output_path
        
    finally:
        # Clean up temporary audio file
        if os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except OSError:
                pass  # Ignore cleanup errors


def segments_to_caption_content(
    segments: List[TranscriptionSegment],
    output_format: CaptionFormat = CaptionFormat.SRT
) -> str:
    """
    Convert transcription segments to caption content string.
    
    Utility function for converting segments without file I/O.
    
    Args:
        segments: List of TranscriptionSegment objects
        output_format: Caption format (SRT or VTT)
        
    Returns:
        Formatted caption content as string
        
    Validates: Requirements 2.3
    """
    if not segments:
        return ""
    
    segment_dicts = [
        {'start': s.start, 'end': s.end, 'text': s.text}
        for s in segments
    ]
    
    if output_format == CaptionFormat.VTT:
        return format_to_vtt(segment_dicts)
    else:
        return format_to_srt(segment_dicts)
