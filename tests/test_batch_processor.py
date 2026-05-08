from pathlib import Path

import pytest

from scripts.batch_engine import BatchReport, CoverMode
from scripts import batch_processor


def test_build_batch_run_config_parses_paths_and_backward_compatible_defaults(tmp_path: Path):
    target_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    target_dir.mkdir()
    output_dir.mkdir()

    cfg = batch_processor.build_batch_run_config(
        {
            "target_folder": str(target_dir),
            "output_folder": str(output_dir),
            "cover_duration_sec": 2.5,
            "supported_video_formats": ["mp4", "mov"],
        }
    )

    assert cfg.target_folder == target_dir.resolve()
    assert cfg.output_folder == output_dir.resolve()
    assert cfg.caption_enabled is True
    assert cfg.manual_logo_path is None
    assert cfg.cover_mode is CoverMode.DELAY_OVERLAY
    assert cfg.cover_delay_sec == 2.5
    assert cfg.intro_video_path is None


def test_build_batch_run_config_forces_watermark_on_even_when_disabled_in_json(tmp_path: Path):
    target_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    target_dir.mkdir()
    output_dir.mkdir()

    cfg = batch_processor.build_batch_run_config(
        {
            "target_folder": str(target_dir),
            "output_folder": str(output_dir),
            "watermark_enabled": False,
        }
    )

    assert cfg.watermark_enabled is True


def test_process_batch_delegates_to_run_batch_and_preserves_exit_code(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    target_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    target_dir.mkdir()

    observed = {}

    def fake_run_batch(config, adapters, on_event=None):
        observed["config"] = config
        observed["adapters"] = adapters
        observed["on_event"] = on_event
        return BatchReport(
            exit_code=1,
            results=[{"status": "failed", "video": "sample.mp4", "stage": "processing", "error": "boom"}],
        )

    monkeypatch.setattr("scripts.batch_processor.run_batch", fake_run_batch)

    exit_code, results = batch_processor.process_batch(
        {
            "target_folder": str(target_dir),
            "output_folder": str(output_dir),
            "watermark_enabled": False,
            "caption_enabled": False,
            "cover_mode": "delay_overlay",
            "cover_duration_sec": 3.0,
        }
    )

    assert exit_code == 1
    assert len(results) == 1
    assert results[0]["status"] == "failed"
    assert observed["config"].watermark_enabled is True
    assert observed["config"].caption_enabled is False
    assert observed["config"].cover_mode is CoverMode.DELAY_OVERLAY
    assert observed["config"].cover_delay_sec == 3.0
    assert output_dir.exists()


def test_main_keeps_exit_code_message_behavior(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]):
    monkeypatch.setattr(batch_processor, "print_banner", lambda: None)
    monkeypatch.setattr(batch_processor, "load_config", lambda: {"target_folder": "x", "output_folder": "y"})

    monkeypatch.setattr(
        batch_processor,
        "process_batch",
        lambda _config: (
            3,
            [],
        ),
    )

    exit_code = batch_processor.main()
    output = capsys.readouterr().out

    assert exit_code == 3
    assert "Batch ended: no input videos." in output


def test_main_returns_2_and_prints_error_when_process_batch_raises_value_or_key_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    monkeypatch.setattr(batch_processor, "print_banner", lambda: None)
    monkeypatch.setattr(batch_processor, "load_config", lambda: {"target_folder": "x", "output_folder": "y"})

    def raise_value_error(_config):
        raise ValueError("invalid cover_duration_sec")

    monkeypatch.setattr(batch_processor, "process_batch", raise_value_error)

    exit_code = batch_processor.main()
    output = capsys.readouterr().out

    assert exit_code == 2
    assert "[ERROR]" in output
    assert "invalid cover_duration_sec" in output


def test_main_returns_2_and_prints_error_when_process_batch_raises_generic_exception(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    monkeypatch.setattr(batch_processor, "print_banner", lambda: None)
    monkeypatch.setattr(batch_processor, "load_config", lambda: {"target_folder": "x", "output_folder": "y"})

    def raise_generic_error(_config):
        raise RuntimeError("ffmpeg crashed")

    monkeypatch.setattr(batch_processor, "process_batch", raise_generic_error)

    exit_code = batch_processor.main()
    output = capsys.readouterr().out

    assert exit_code == 2
    assert "[ERROR]" in output
    assert "ffmpeg crashed" in output
