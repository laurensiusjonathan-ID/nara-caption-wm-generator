from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable


class BatchConfigError(ValueError):
    """Raised when batch runtime configuration is invalid."""


class CoverMode(str, Enum):
    DELAY_OVERLAY = "delay_overlay"
    INTRO_MERGE = "intro_merge"


class WatermarkPosition(str, Enum):
    TOP_LEFT = "top-left"
    TOP_RIGHT = "top-right"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM_RIGHT = "bottom-right"


@dataclass(frozen=True)
class BatchRunConfig:
    target_folder: Path
    output_folder: Path
    watermark_enabled: bool
    caption_enabled: bool
    cover_mode: CoverMode
    cover_delay_sec: float
    intro_video_path: Path | None
    manual_logo_path: Path | None
    supported_video_formats: tuple[str, ...]
    caption_language: str
    caption_format: str
    whisper_model_size: str
    caption_sync_correction_sec: float
    watermark_opacity: float
    watermark_scale: float
    watermark_padding: int
    watermark_position: WatermarkPosition = WatermarkPosition.BOTTOM_RIGHT


def resolve_logo_path(manual_logo_path: Path | None, detected_logos: list[Path]) -> Path:
    if manual_logo_path is not None:
        return manual_logo_path

    if len(detected_logos) != 1:
        raise BatchConfigError(
            "Expected exactly one PNG logo in target folder when manual logo is empty"
        )

    return detected_logos[0]


def validate_runtime_rules(config: BatchRunConfig) -> None:
    if not config.watermark_enabled:
        raise BatchConfigError("watermark_enabled must always be True")

    if config.manual_logo_path is not None:
        if not config.manual_logo_path.exists() or not config.manual_logo_path.is_file():
            raise BatchConfigError("manual_logo_path must exist and be a file")
        if config.manual_logo_path.suffix.lower() != ".png":
            raise BatchConfigError("manual_logo_path must have .png suffix")

    if config.cover_mode is CoverMode.INTRO_MERGE:
        if config.intro_video_path is None:
            raise BatchConfigError("intro_video_path is required in intro_merge mode")
        if not config.intro_video_path.exists() or not config.intro_video_path.is_file():
            raise BatchConfigError("intro_video_path must exist and be a file")

        intro_ext = config.intro_video_path.suffix.lower().lstrip(".")
        supported_formats = tuple(
            fmt.lower().lstrip(".") for fmt in config.supported_video_formats
        )
        if intro_ext not in supported_formats:
            raise BatchConfigError(
                "intro_video_path suffix must be included in supported_video_formats"
            )

    if config.cover_mode is CoverMode.DELAY_OVERLAY and config.cover_delay_sec < 0:
        raise BatchConfigError("cover_delay_sec must be >= 0")

    needs_caption_shift = config.caption_enabled and (
        config.cover_mode is CoverMode.DELAY_OVERLAY
        or config.caption_sync_correction_sec != 0
    )
    if needs_caption_shift and config.caption_format.lower() != "srt":
        raise BatchConfigError(
            "caption_format must be 'srt' when timestamp shifting is required"
        )


@dataclass(frozen=True)
class ProcessingAdapters:
    generate_captions: Callable[..., Any]
    process_video: Callable[..., Any]
    merge_videos: Callable[..., Any]
    shift_srt_timestamps: Callable[..., Any]


@dataclass(frozen=True)
class BatchReport:
    exit_code: int
    results: list[dict[str, Any]]


def discover_input_files(
    target_folder: Path,
    supported_video_formats: tuple[str, ...],
) -> tuple[list[Path], list[Path]]:
    supported_exts = {f".{fmt.lower().lstrip('.')}" for fmt in supported_video_formats}

    videos: list[Path] = []
    logos: list[Path] = []

    for path in target_folder.iterdir():
        if not path.is_file():
            continue

        suffix = path.suffix.lower()
        if suffix in supported_exts:
            videos.append(path)
        if suffix == ".png":
            logos.append(path)

    return videos, logos


def map_exit_code(total_videos: int, failed_count: int, fatal: bool) -> int:
    if fatal:
        return 2
    if total_videos == 0:
        return 3
    if failed_count > 0:
        return 1
    return 0


def run_batch(
    config: BatchRunConfig,
    adapters: ProcessingAdapters,
    on_event: Callable[[dict[str, Any]], None] | None = None,
) -> BatchReport:
    event_callback = on_event or (lambda _event: None)

    def emit_event(event: dict[str, Any]) -> None:
        try:
            event_callback(event)
        except Exception:  # noqa: BLE001
            return

    try:
        validate_runtime_rules(config)
        videos, logos = discover_input_files(
            target_folder=config.target_folder,
            supported_video_formats=config.supported_video_formats,
        )
        resolved_logo_path = resolve_logo_path(
            manual_logo_path=config.manual_logo_path,
            detected_logos=logos,
        )
    except Exception as exc:  # noqa: BLE001
        result = {
            "status": "failed",
            "stage": "startup",
            "error": str(exc),
        }
        emit_event({"type": "startup_failed", **result})
        return BatchReport(exit_code=map_exit_code(0, 1, True), results=[result])

    sorted_videos = sorted(videos, key=lambda path: path.name.lower())
    if not sorted_videos:
        emit_event({"type": "no_input_videos"})
        return BatchReport(exit_code=map_exit_code(0, 0, False), results=[])

    results: list[dict[str, Any]] = []
    failed_count = 0

    for video_path in sorted_videos:
        row = process_single_video(
            video_path=video_path,
            output_folder=config.output_folder,
            resolved_logo_path=resolved_logo_path,
            config=config,
            adapters=adapters,
        )
        if row.get("status") == "failed":
            failed_count += 1

        results.append(row)
        emit_event({"type": "video_processed", "result": row})

    return BatchReport(
        exit_code=map_exit_code(
            total_videos=len(sorted_videos),
            failed_count=failed_count,
            fatal=False,
        ),
        results=results,
    )


def _map_watermark_position(position: WatermarkPosition):
    from app.models.enums import WatermarkPosition as AppWatermarkPosition

    mapping = {
        WatermarkPosition.TOP_LEFT: AppWatermarkPosition.TOP_LEFT,
        WatermarkPosition.TOP_RIGHT: AppWatermarkPosition.TOP_RIGHT,
        WatermarkPosition.BOTTOM_LEFT: AppWatermarkPosition.BOTTOM_LEFT,
        WatermarkPosition.BOTTOM_RIGHT: AppWatermarkPosition.BOTTOM_RIGHT,
    }
    return mapping.get(position, AppWatermarkPosition.BOTTOM_RIGHT)


def process_single_video(
    *,
    video_path: Path,
    output_folder: Path,
    resolved_logo_path: Path,
    config: BatchRunConfig,
    adapters: ProcessingAdapters,
) -> dict[str, Any]:
    app_watermark_position = _map_watermark_position(config.watermark_position)
    final_output_path = output_folder / f"{video_path.stem}_processed.mp4"

    if final_output_path.exists():
        return {
            "status": "skipped",
            "video": video_path.name,
            "message": "Output already exists",
        }

    main_processed_output_path = (
        output_folder / f"{video_path.stem}__main_processed.mp4"
        if config.cover_mode is CoverMode.INTRO_MERGE
        else final_output_path
    )

    caption_path_for_processing: str | None = None
    delayed_caption_path = output_folder / f"{video_path.stem}__delayed.srt"

    if config.caption_enabled:
        caption_path = output_folder / f"{video_path.stem}.{config.caption_format}"
        try:
            adapters.generate_captions(
                video_path=str(video_path),
                output_path=str(caption_path),
                language=config.caption_language,
                output_format=config.caption_format,
                model_size=config.whisper_model_size,
            )

            if config.cover_mode is CoverMode.DELAY_OVERLAY:
                adapters.shift_srt_timestamps(
                    source_path=str(caption_path),
                    output_path=str(delayed_caption_path),
                    offset_sec=config.cover_delay_sec + config.caption_sync_correction_sec,
                    min_start_sec=config.cover_delay_sec,
                )
                caption_path_for_processing = str(delayed_caption_path)
            elif config.caption_sync_correction_sec != 0:
                adapters.shift_srt_timestamps(
                    source_path=str(caption_path),
                    output_path=str(delayed_caption_path),
                    offset_sec=config.caption_sync_correction_sec,
                    min_start_sec=0.0,
                )
                caption_path_for_processing = str(delayed_caption_path)
            else:
                caption_path_for_processing = str(caption_path)
        except Exception as exc:  # noqa: BLE001
            return {
                "status": "failed",
                "video": video_path.name,
                "stage": "captions",
                "error": str(exc),
            }

    watermark_start_sec = (
        config.cover_delay_sec if config.cover_mode is CoverMode.DELAY_OVERLAY else 0.0
    )

    try:
        adapters.process_video(
            video_path=str(video_path),
            output_path=str(main_processed_output_path),
            caption_path=caption_path_for_processing,
            watermark_path=str(resolved_logo_path),
            watermark_opacity=config.watermark_opacity,
            watermark_scale=config.watermark_scale,
            watermark_padding=config.watermark_padding,
            watermark_start_sec=watermark_start_sec,
            watermark_position=app_watermark_position,
        )

        if config.cover_mode is CoverMode.INTRO_MERGE:
            adapters.merge_videos(
                cover_video_path=str(config.intro_video_path),
                main_video_path=str(main_processed_output_path),
                output_path=str(final_output_path),
                re_encode=True,
            )
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "failed",
            "video": video_path.name,
            "stage": "processing",
            "error": str(exc),
        }
    finally:
        if config.cover_mode is CoverMode.INTRO_MERGE:
            main_processed_output_path.unlink(missing_ok=True)

    return {
        "status": "success",
        "video": video_path.name,
        "output_path": str(final_output_path),
    }
