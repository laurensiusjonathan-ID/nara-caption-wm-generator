#!/usr/bin/env python

import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.batch_engine import (
    BatchRunConfig,
    CoverMode,
    ProcessingAdapters,
    run_batch,
)

FIXED_WATERMARK_SCALE = 0.12
FIXED_WATERMARK_PADDING = 24
FIXED_WATERMARK_OPACITY = 0.75

CONFIG_PATH = Path(__file__).parent / "batch_config.json"


def print_banner() -> None:
    print("=" * 60)
    print("  NARA CAPTION & WATERMARK BATCH PROCESSOR (LOCAL SIMPLE)")
    print("=" * 60)
    print()


def load_config(config_path: Path = CONFIG_PATH) -> dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def resolve_path(configured_path: str) -> Path:
    return (Path(__file__).parent / configured_path).resolve()


def _parse_cover_mode(raw_value: Any) -> CoverMode:
    normalized = str(raw_value or CoverMode.DELAY_OVERLAY.value).strip().lower()
    if normalized == CoverMode.INTRO_MERGE.value:
        return CoverMode.INTRO_MERGE
    return CoverMode.DELAY_OVERLAY


def _parse_optional_path(raw_value: Any) -> Path | None:
    if raw_value is None:
        return None

    normalized = str(raw_value).strip()
    if not normalized:
        return None

    return resolve_path(normalized)


def build_batch_run_config(config: dict[str, Any]) -> BatchRunConfig:
    target_folder = resolve_path(str(config["target_folder"]))
    output_folder = resolve_path(str(config["output_folder"]))

    cover_mode = _parse_cover_mode(config.get("cover_mode"))

    return BatchRunConfig(
        target_folder=target_folder,
        output_folder=output_folder,
        watermark_enabled=True,
        caption_enabled=bool(config.get("caption_enabled", True)),
        cover_mode=cover_mode,
        cover_delay_sec=float(config.get("cover_duration_sec", 0.0)),
        intro_video_path=_parse_optional_path(config.get("intro_video_path")),
        manual_logo_path=_parse_optional_path(config.get("manual_logo_path")),
        supported_video_formats=tuple(config.get("supported_video_formats", ["mp4", "mov", "avi"])),
        caption_language=str(config.get("caption_language", "id")),
        caption_format=str(config.get("caption_format", "srt")),
        whisper_model_size=str(config.get("whisper_model_size", "medium")),
        caption_sync_correction_sec=float(config.get("caption_sync_correction_sec", 0.0)),
        watermark_opacity=float(config.get("watermark_opacity", FIXED_WATERMARK_OPACITY)),
        watermark_scale=float(config.get("watermark_scale", FIXED_WATERMARK_SCALE)),
        watermark_padding=int(config.get("watermark_padding", FIXED_WATERMARK_PADDING)),
    )


def shift_srt_timestamps(
    source_path: Path | str,
    output_path: Path | str,
    offset_sec: float,
    min_start_sec: float = 0.0,
) -> None:
    source = Path(source_path)
    output = Path(output_path)

    if offset_sec == 0 and min_start_sec <= 0:
        shutil.copy2(source, output)
        return

    timecode_pattern = re.compile(
        r"^(\d{2}):(\d{2}):(\d{2}),(\d{3})\s-->\s(\d{2}):(\d{2}):(\d{2}),(\d{3})$"
    )

    def to_ms(h: str, m: str, s: str, ms: str) -> int:
        return ((int(h) * 3600 + int(m) * 60 + int(s)) * 1000) + int(ms)

    def from_ms(total_ms: int) -> str:
        if total_ms < 0:
            total_ms = 0
        h = total_ms // 3600000
        rem = total_ms % 3600000
        mm = rem // 60000
        rem = rem % 60000
        ss = rem // 1000
        mss = rem % 1000
        return f"{h:02d}:{mm:02d}:{ss:02d},{mss:03d}"

    offset_ms = int(offset_sec * 1000)
    min_start_ms = max(0, int(min_start_sec * 1000))
    transformed: list[str] = []

    for raw_line in source.read_text(encoding="utf-8").splitlines():
        match = timecode_pattern.match(raw_line.strip())
        if not match:
            transformed.append(raw_line)
            continue

        start_ms = to_ms(match.group(1), match.group(2), match.group(3), match.group(4)) + offset_ms
        end_ms = to_ms(match.group(5), match.group(6), match.group(7), match.group(8)) + offset_ms

        if start_ms < min_start_ms:
            duration_ms = max(1, end_ms - start_ms)
            start_ms = min_start_ms
            end_ms = max(start_ms + 1, start_ms + duration_ms)

        if end_ms < min_start_ms:
            end_ms = min_start_ms + 1
            start_ms = min_start_ms

        if end_ms <= start_ms:
            end_ms = start_ms + 1

        transformed.append(f"{from_ms(start_ms)} --> {from_ms(end_ms)}")

    output.write_text("\n".join(transformed) + "\n", encoding="utf-8")


def build_processing_adapters() -> ProcessingAdapters:
    from app.services.caption_generator import generate_captions
    from app.services.video_processor import merge_videos, process_video

    return ProcessingAdapters(
        generate_captions=generate_captions,
        process_video=process_video,
        merge_videos=merge_videos,
        shift_srt_timestamps=shift_srt_timestamps,
    )


def print_summary(results: list[dict[str, Any]]) -> None:
    total = len(results)
    success = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] == "failed")
    skipped = sum(1 for r in results if r["status"] == "skipped")

    print("\n" + "=" * 60)
    print("BATCH PROCESSING SUMMARY")
    print("=" * 60)
    print(f"Total videos : {total}")
    print(f"Successful   : {success}")
    print(f"Failed       : {failed}")
    print(f"Skipped      : {skipped}")
    print("=" * 60)

    for row in results:
        if row["status"] == "success":
            print(f"[OK] {row['video']} -> {Path(row['output_path']).name}")
        elif row["status"] == "skipped":
            print(f"[SKIP] {row['video']} -> {row.get('message', 'Skipped')}")
        else:
            print(f"[FAIL] {row['video']} ({row.get('stage', 'unknown')}) -> {row.get('error', 'Unknown error')}")


def process_batch(config: dict[str, Any]) -> tuple[int, list[dict[str, Any]]]:
    batch_config = build_batch_run_config(config)
    batch_config.output_folder.mkdir(parents=True, exist_ok=True)

    report = run_batch(
        config=batch_config,
        adapters=build_processing_adapters(),
    )
    return report.exit_code, report.results


def main() -> int:
    print_banner()

    try:
        config = load_config()
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[ERROR] Failed to load config: {exc}")
        return 2

    try:
        exit_code, results = process_batch(config)
    except (ValueError, KeyError) as exc:
        print(f"[ERROR] Failed to process batch due to invalid configuration: {exc}")
        return 2
    except Exception as exc:
        print(f"[ERROR] Failed to process batch: {exc}")
        return 2

    if results:
        print_summary(results)

    if exit_code == 0:
        print("\n[INFO] Batch completed successfully.")
    elif exit_code == 1:
        print("\n[WARNING] Batch completed with partial failures.")
    elif exit_code == 2:
        print("\n[ERROR] Batch terminated due to fatal startup/config error.")
    elif exit_code == 3:
        print("\n[INFO] Batch ended: no input videos.")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
