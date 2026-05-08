from dataclasses import dataclass
from enum import Enum


class UiCoverMode(str, Enum):
    DELAY_OVERLAY = "delay_overlay"
    INTRO_MERGE = "intro_merge"


class UiWatermarkPosition(str, Enum):
    TOP_LEFT = "top-left"
    TOP_RIGHT = "top-right"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM_RIGHT = "bottom-right"


@dataclass(frozen=True)
class UiRunState:
    target_folder: str
    output_folder: str
    caption_enabled: bool
    watermark_enabled: bool
    cover_mode: UiCoverMode
    cover_delay_sec: str
    intro_video_path: str
    manual_logo_path: str
    watermark_position: UiWatermarkPosition = UiWatermarkPosition.BOTTOM_RIGHT
