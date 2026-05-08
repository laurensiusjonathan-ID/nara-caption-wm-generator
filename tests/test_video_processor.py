"""
Tests for the video processor module.

Tests caption burning and combined video processing functionality.
"""

from pathlib import Path
from unittest.mock import Mock

import pytest

from app.services import video_processor
from app.services.video_processor import (
    VideoProcessingError,
    OUTPUT_FORMAT,
    OUTPUT_CODEC,
    AUDIO_CODEC,
    get_output_format,
)


class TestGetOutputFormat:
    """Tests for get_output_format function."""
    
    def test_returns_mp4(self):
        """Output format should always be mp4."""
        assert get_output_format() == "mp4"
    
    def test_matches_constant(self):
        """Should match OUTPUT_FORMAT constant."""
        assert get_output_format() == OUTPUT_FORMAT


class TestConstants:
    """Tests for module constants."""
    
    def test_output_format_is_mp4(self):
        """OUTPUT_FORMAT should be mp4."""
        assert OUTPUT_FORMAT == "mp4"
    
    def test_output_codec_is_libx264(self):
        """OUTPUT_CODEC should be libx264."""
        assert OUTPUT_CODEC == "libx264"
    
    def test_audio_codec_is_aac(self):
        """AUDIO_CODEC should be aac."""
        assert AUDIO_CODEC == "aac"


class TestVideoProcessingError:
    """Tests for VideoProcessingError exception."""

    def test_exception_message(self):
        """Should preserve error message."""
        error = VideoProcessingError("Test error message")
        assert str(error) == "Test error message"

    def test_exception_inheritance(self):
        """Should inherit from Exception."""
        error = VideoProcessingError("Test")
        assert isinstance(error, Exception)


class _FakeStream:
    def __init__(self) -> None:
        self.filters: list[tuple[str, tuple, dict]] = []

    def filter(self, name: str, *args, **kwargs):
        self.filters.append((name, args, kwargs))
        return self


class _FakeInput:
    def __init__(self) -> None:
        self.video = _FakeStream()
        self.audio = _FakeStream()


class _FakeOutput:
    pass


def test_merge_videos_reencode_normalizes_cover_to_main_dimensions_and_fps(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    cover = tmp_path / "cover.mp4"
    main = tmp_path / "main.mp4"
    output = tmp_path / "merged.mp4"
    cover.write_bytes(b"c")
    main.write_bytes(b"m")

    inputs: list[_FakeInput] = []

    def fake_input(_path, **_kwargs):
        obj = _FakeInput()
        inputs.append(obj)
        return obj

    def fake_probe(path):
        if str(path) == str(main):
            return {
                "streams": [
                    {
                        "codec_type": "video",
                        "width": 1920,
                        "height": 1080,
                        "r_frame_rate": "30/1",
                        "sample_aspect_ratio": "1:1",
                    }
                ]
            }
        raise AssertionError("Unexpected ffprobe path")

    fake_output = _FakeOutput()
    output_kwargs: dict = {}

    def fake_ffmpeg_output(*_args, **kwargs):
        output_kwargs.update(kwargs)
        return fake_output

    def fake_concat(*_args, **_kwargs):
        return _FakeStream()

    def fake_run(_output, **_kwargs):
        output.write_bytes(b"merged")

    monkeypatch.setattr(video_processor.ffmpeg, "input", fake_input)
    monkeypatch.setattr(video_processor.ffmpeg, "probe", fake_probe)
    monkeypatch.setattr(video_processor.ffmpeg, "output", fake_ffmpeg_output)
    monkeypatch.setattr(video_processor.ffmpeg, "concat", fake_concat)
    monkeypatch.setattr(video_processor.ffmpeg, "run", fake_run)

    result = video_processor.merge_videos(
        cover_video_path=str(cover),
        main_video_path=str(main),
        output_path=str(output),
        re_encode=True,
    )

    assert result == str(output)
    assert len(inputs) == 2

    cover_video_filters = inputs[0].video.filters
    main_video_filters = inputs[1].video.filters

    assert ("scale", (1920, 1080), {}) in cover_video_filters
    assert ("fps", (), {"fps": "30/1"}) in cover_video_filters
    assert ("setsar", (), {"sar": "1/1"}) in cover_video_filters

    assert ("scale", (1920, 1080), {}) in main_video_filters
    assert ("fps", (), {"fps": "30/1"}) in main_video_filters
    assert ("setsar", (), {"sar": "1/1"}) in main_video_filters

    assert output_kwargs["vcodec"] == OUTPUT_CODEC
    assert output_kwargs["acodec"] == AUDIO_CODEC
    assert output_kwargs["preset"] == "medium"
    assert output_kwargs["crf"] == 18


def test_merge_videos_reencode_raises_when_main_video_metadata_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    cover = tmp_path / "cover.mp4"
    main = tmp_path / "main.mp4"
    output = tmp_path / "merged.mp4"
    cover.write_bytes(b"c")
    main.write_bytes(b"m")

    fake_output = _FakeOutput()

    monkeypatch.setattr(video_processor.ffmpeg, "probe", lambda _path: {"streams": []})
    monkeypatch.setattr(video_processor.ffmpeg, "input", lambda *_args, **_kwargs: _FakeInput())
    monkeypatch.setattr(video_processor.ffmpeg, "output", lambda *_args, **_kwargs: fake_output)
    monkeypatch.setattr(video_processor.ffmpeg, "concat", lambda *_args, **_kwargs: _FakeStream())
    monkeypatch.setattr(video_processor.ffmpeg, "run", lambda *_args, **_kwargs: output.write_bytes(b"merged"))

    with pytest.raises(VideoProcessingError, match="Failed to read main video metadata"):
        video_processor.merge_videos(
            cover_video_path=str(cover),
            main_video_path=str(main),
            output_path=str(output),
            re_encode=True,
        )


def test_merge_videos_fast_path_keeps_concat_file_until_run_finishes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    cover = tmp_path / "cover.mp4"
    main = tmp_path / "main.mp4"
    output = tmp_path / "merged.mp4"
    cover.write_bytes(b"c")
    main.write_bytes(b"m")

    concat_file_path_holder: dict[str, str] = {}

    class _FakeTempFile:
        def __init__(self, name: str) -> None:
            self.name = name
            self._buffer: list[str] = []

        def write(self, text: str) -> int:
            self._buffer.append(text)
            return len(text)

        def close(self) -> None:
            Path(self.name).write_text("".join(self._buffer), encoding="utf-8")

    def fake_named_tempfile(**_kwargs):
        temp_path = tmp_path / "concat-list.txt"
        concat_file_path_holder["path"] = str(temp_path)
        return _FakeTempFile(str(temp_path))

    output_kwargs: dict = {}

    def fake_output(*_args, **kwargs):
        output_kwargs.update(kwargs)
        return _FakeOutput()

    def fake_run(_output, **_kwargs):
        concat_file = Path(concat_file_path_holder["path"])
        assert concat_file.exists()
        output.write_bytes(b"merged")

    monkeypatch.setattr(video_processor.tempfile, "NamedTemporaryFile", fake_named_tempfile)
    monkeypatch.setattr(video_processor.ffmpeg, "input", lambda *_args, **_kwargs: _FakeInput())
    monkeypatch.setattr(video_processor.ffmpeg, "output", fake_output)
    monkeypatch.setattr(video_processor.ffmpeg, "run", fake_run)

    result = video_processor.merge_videos(
        cover_video_path=str(cover),
        main_video_path=str(main),
        output_path=str(output),
        re_encode=False,
    )

    assert result == str(output)
    assert output_kwargs["c"] == "copy"
    assert "preset" not in output_kwargs
    assert not Path(concat_file_path_holder["path"]).exists()


def test_burn_captions_uses_subtitles_filename_keyword_for_windows_absolute_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    video = tmp_path / "input.mp4"
    output = tmp_path / "output.mp4"
    video.write_bytes(b"video")

    windows_caption_path = r"D:\captions\04.09. Fundamental Github Merge.srt"

    fake_input = _FakeInput()

    def fake_ffmpeg_input(path, **_kwargs):
        assert path == str(video)
        return fake_input

    def fake_ffmpeg_output(*_args, **_kwargs):
        return _FakeOutput()

    def fake_ffmpeg_run(*_args, **_kwargs):
        output.write_bytes(b"processed")

    real_exists = video_processor.os.path.exists

    def fake_exists(path):
        if path == windows_caption_path:
            return True
        return real_exists(path)

    monkeypatch.setattr(video_processor.os.path, "exists", fake_exists)
    monkeypatch.setattr(video_processor.ffmpeg, "input", fake_ffmpeg_input)
    monkeypatch.setattr(video_processor.ffmpeg, "output", fake_ffmpeg_output)
    monkeypatch.setattr(video_processor.ffmpeg, "run", fake_ffmpeg_run)

    result = video_processor.burn_captions(
        video_path=str(video),
        caption_path=windows_caption_path,
        output_path=str(output),
    )

    assert result == str(output)
    subtitle_calls = [call for call in fake_input.video.filters if call[0] == "subtitles"]
    assert subtitle_calls == [("subtitles", (), {"filename": windows_caption_path})]


def test_process_video_uses_subtitles_filename_keyword_for_windows_absolute_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    video = tmp_path / "input.mp4"
    output = tmp_path / "output.mp4"
    video.write_bytes(b"video")

    windows_caption_path = r"D:\captions\04.09. Fundamental Github Merge.srt"

    fake_input = _FakeInput()

    def fake_ffmpeg_input(path, **_kwargs):
        assert path == str(video)
        return fake_input

    def fake_ffmpeg_output(*_args, **_kwargs):
        return _FakeOutput()

    def fake_ffmpeg_run(*_args, **_kwargs):
        output.write_bytes(b"processed")

    real_exists = video_processor.os.path.exists

    def fake_exists(path):
        if path == windows_caption_path:
            return True
        return real_exists(path)

    monkeypatch.setattr(video_processor.os.path, "exists", fake_exists)
    monkeypatch.setattr(video_processor.ffmpeg, "input", fake_ffmpeg_input)
    monkeypatch.setattr(video_processor.ffmpeg, "output", fake_ffmpeg_output)
    monkeypatch.setattr(video_processor.ffmpeg, "run", fake_ffmpeg_run)

    result = video_processor.process_video(
        video_path=str(video),
        output_path=str(output),
        caption_path=windows_caption_path,
    )

    assert result == str(output)
    subtitle_calls = [call for call in fake_input.video.filters if call[0] == "subtitles"]
    assert subtitle_calls == [("subtitles", (), {"filename": windows_caption_path})]
