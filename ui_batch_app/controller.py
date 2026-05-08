from __future__ import annotations

from pathlib import Path
from threading import Thread
from typing import Any, Callable

from scripts.batch_engine import BatchReport, BatchRunConfig, CoverMode, WatermarkPosition, run_batch
from scripts.batch_processor import build_processing_adapters
from ui_batch_app.models import UiCoverMode, UiRunState, UiWatermarkPosition

EventCallback = Callable[[dict[str, Any]], None]
RunBatchFn = Callable[..., BatchReport]
AdaptersFactory = Callable[[], Any]


class UiBatchController:
    def __init__(
        self,
        on_event: EventCallback,
        run_batch_fn: RunBatchFn = run_batch,
        adapters_factory: AdaptersFactory = build_processing_adapters,
    ) -> None:
        self._on_event = on_event
        self._run_batch_fn = run_batch_fn
        self._adapters_factory = adapters_factory

    def start_run(self, state: UiRunState) -> Thread:
        worker = Thread(target=self._run_worker, args=(state,), daemon=True)
        worker.start()
        return worker

    def _run_worker(self, state: UiRunState) -> None:
        try:
            config = self._to_batch_config(state)
            adapters = self._adapters_factory()
            processed_count = 0

            def handle_engine_event(event: dict[str, Any]) -> None:
                nonlocal processed_count
                event_type = event.get("type")

                if event_type == "video_processed":
                    processed_count += 1
                    result = event.get("result", {})
                    self._emit(
                        {
                            "type": "progress",
                            "processed": processed_count,
                            "result": result,
                        }
                    )
                    video_name = str(result.get("video", "<unknown>"))
                    status = str(result.get("status", "unknown"))

                    log_message = f"Processed {video_name}: {status}"
                    if status == "failed":
                        stage = str(result.get("stage", "unknown"))
                        error = str(result.get("error", "Unknown error"))
                        log_message = f"{log_message} | stage={stage} | error={error}"

                    self._emit({"type": "log", "message": log_message})
                    return

                if event_type == "startup_failed":
                    error_message = str(event.get("error", "Startup failed"))
                    self._emit({"type": "error", "message": error_message, "event": event})
                    return

                if event_type == "no_input_videos":
                    self._emit({"type": "log", "message": "No input videos were found"})
                    return

                self._emit({"type": "log", "message": f"Engine event: {event}"})

            report = self._run_batch_fn(
                config=config,
                adapters=adapters,
                on_event=handle_engine_event,
            )
            self._emit(self._build_summary_event(report))
        except Exception as exc:  # noqa: BLE001
            self._emit({"type": "error", "message": str(exc)})

    def _to_batch_config(self, state: UiRunState) -> BatchRunConfig:
        cover_mode = (
            CoverMode.INTRO_MERGE
            if state.cover_mode is UiCoverMode.INTRO_MERGE
            else CoverMode.DELAY_OVERLAY
        )

        manual_logo = Path(state.manual_logo_path.strip()) if state.manual_logo_path.strip() else None
        intro_video = Path(state.intro_video_path.strip()) if state.intro_video_path.strip() else None

        cover_delay_sec = 0.0
        if cover_mode is CoverMode.DELAY_OVERLAY:
            cover_delay_sec = float(state.cover_delay_sec)

        wm_position = WatermarkPosition(state.watermark_position.value)

        return BatchRunConfig(
            target_folder=Path(state.target_folder).resolve(),
            output_folder=Path(state.output_folder).resolve(),
            watermark_enabled=bool(state.watermark_enabled),
            caption_enabled=bool(state.caption_enabled),
            cover_mode=cover_mode,
            cover_delay_sec=cover_delay_sec,
            intro_video_path=intro_video.resolve() if intro_video is not None else None,
            manual_logo_path=manual_logo.resolve() if manual_logo is not None else None,
            supported_video_formats=("mp4", "mov", "avi"),
            caption_language="id",
            caption_format="srt",
            whisper_model_size="medium",
            caption_sync_correction_sec=0.0,
            watermark_opacity=0.75,
            watermark_scale=0.12,
            watermark_padding=24,
            watermark_position=wm_position,
        )

    def _build_summary_event(self, report: BatchReport) -> dict[str, Any]:
        success = sum(1 for row in report.results if row.get("status") == "success")
        failed = sum(1 for row in report.results if row.get("status") == "failed")
        skipped = sum(1 for row in report.results if row.get("status") == "skipped")

        return {
            "type": "summary",
            "exit_code": report.exit_code,
            "total": len(report.results),
            "success": success,
            "failed": failed,
            "skipped": skipped,
            "results": report.results,
        }

    def _emit(self, event: dict[str, Any]) -> None:
        try:
            self._on_event(event)
        except Exception:  # noqa: BLE001
            return
