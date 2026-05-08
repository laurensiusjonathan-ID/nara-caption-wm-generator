import math
from typing import Any

from ui_batch_app.models import UiCoverMode, UiRunState


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    return str(value).strip() == ""


def validate_ui_state(state: UiRunState) -> list[str]:
    errors: list[str] = []

    if not state.watermark_enabled:
        errors.append("Watermark must be ON")

    if _is_blank(state.target_folder):
        errors.append("Target folder is required")

    if _is_blank(state.output_folder):
        errors.append("Output folder is required")

    if state.cover_mode is UiCoverMode.INTRO_MERGE and _is_blank(state.intro_video_path):
        errors.append("Intro video path is required for intro merge mode")

    if state.cover_mode is UiCoverMode.DELAY_OVERLAY:
        try:
            delay_sec = float(state.cover_delay_sec)
        except (TypeError, ValueError):
            errors.append("Cover delay must be a number")
        else:
            if not math.isfinite(delay_sec):
                errors.append("Cover delay must be finite")
            elif delay_sec < 0:
                errors.append("Cover delay must be >= 0")

    if not _is_blank(state.manual_logo_path):
        logo_path = str(state.manual_logo_path)
        if not logo_path.lower().endswith(".png"):
            errors.append("Manual logo path must end with .png")

    return errors
