from pathlib import Path

from scripts.batch_engine import BatchReport, CoverMode
from ui_batch_app.models import UiCoverMode, UiRunState
from ui_batch_app.controller import UiBatchController


def _valid_state(tmp_path: Path, **overrides) -> UiRunState:
    target = tmp_path / "input"
    output = tmp_path / "output"
    target.mkdir(exist_ok=True)
    output.mkdir(exist_ok=True)

    data = {
        "target_folder": str(target),
        "output_folder": str(output),
        "caption_enabled": True,
        "watermark_enabled": True,
        "cover_mode": UiCoverMode.DELAY_OVERLAY,
        "cover_delay_sec": "1.25",
        "intro_video_path": "",
        "manual_logo_path": "",
    }
    data.update(overrides)
    return UiRunState(**data)


def test_controller_emits_summary_event_when_run_finishes(tmp_path: Path):
    events: list[dict] = []

    def fake_run_batch(config, adapters, on_event):
        assert config.cover_mode is CoverMode.DELAY_OVERLAY
        assert config.cover_delay_sec == 1.25
        assert adapters == "adapters"
        assert callable(on_event)
        return BatchReport(
            exit_code=0,
            results=[
                {"status": "success", "video": "a.mp4", "output_path": "out/a.mp4"},
                {"status": "skipped", "video": "b.mp4", "message": "Output already exists"},
            ],
        )

    controller = UiBatchController(
        on_event=events.append,
        run_batch_fn=fake_run_batch,
        adapters_factory=lambda: "adapters",
    )

    worker = controller.start_run(_valid_state(tmp_path))
    worker.join(timeout=2)

    summary_events = [event for event in events if event.get("type") == "summary"]
    assert len(summary_events) == 1
    summary = summary_events[0]
    assert summary["exit_code"] == 0
    assert summary["total"] == 2
    assert summary["success"] == 1
    assert summary["failed"] == 0
    assert summary["skipped"] == 1


def test_controller_wires_engine_on_event_payloads_to_callback(tmp_path: Path):
    events: list[dict] = []

    def fake_run_batch(config, adapters, on_event):
        on_event(
            {
                "type": "video_processed",
                "result": {
                    "status": "failed",
                    "video": "clip-1.mp4",
                    "stage": "processing",
                    "error": "Failed to merge videos: ffmpeg stderr",
                },
            }
        )
        on_event({"type": "startup_failed", "error": "logo missing"})
        on_event({"type": "no_input_videos"})
        return BatchReport(exit_code=2, results=[{"status": "failed", "video": "clip-1.mp4"}])

    controller = UiBatchController(
        on_event=events.append,
        run_batch_fn=fake_run_batch,
        adapters_factory=lambda: object(),
    )

    worker = controller.start_run(_valid_state(tmp_path))
    worker.join(timeout=2)

    progress_events = [event for event in events if event.get("type") == "progress"]
    assert len(progress_events) == 1
    assert progress_events[0]["processed"] == 1
    assert progress_events[0]["result"]["video"] == "clip-1.mp4"

    error_events = [event for event in events if event.get("type") == "error"]
    assert len(error_events) == 1
    assert "logo missing" in error_events[0]["message"]

    log_events = [event for event in events if event.get("type") == "log"]
    assert any("No input videos" in event["message"] for event in log_events)
    assert any(
        "Processed clip-1.mp4: failed" in event["message"]
        and "stage=processing" in event["message"]
        and "error=Failed to merge videos: ffmpeg stderr" in event["message"]
        for event in log_events
    )


def test_controller_emits_error_event_when_run_batch_raises(tmp_path: Path):
    events: list[dict] = []

    def fake_run_batch(config, adapters, on_event):
        raise RuntimeError("engine exploded")

    controller = UiBatchController(
        on_event=events.append,
        run_batch_fn=fake_run_batch,
        adapters_factory=lambda: object(),
    )

    worker = controller.start_run(_valid_state(tmp_path))
    worker.join(timeout=2)

    error_events = [event for event in events if event.get("type") == "error"]
    summary_events = [event for event in events if event.get("type") == "summary"]

    assert len(error_events) == 1
    assert "engine exploded" in error_events[0]["message"]
    assert summary_events == []


def test_controller_emits_error_event_when_adapters_factory_raises(tmp_path: Path):
    events: list[dict] = []

    controller = UiBatchController(
        on_event=events.append,
        run_batch_fn=lambda **kwargs: BatchReport(exit_code=0, results=[]),
        adapters_factory=lambda: (_ for _ in ()).throw(RuntimeError("adapters init failed")),
    )

    worker = controller.start_run(_valid_state(tmp_path))
    worker.join(timeout=2)

    error_events = [event for event in events if event.get("type") == "error"]
    summary_events = [event for event in events if event.get("type") == "summary"]

    assert len(error_events) == 1
    assert "adapters init failed" in error_events[0]["message"]
    assert summary_events == []
