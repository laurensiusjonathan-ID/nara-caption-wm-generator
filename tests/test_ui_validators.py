from ui_batch_app.models import UiCoverMode, UiRunState
from ui_batch_app.validators import validate_ui_state


def _base_state(tmp_path, **overrides) -> UiRunState:
    data = {
        "target_folder": str(tmp_path / "input"),
        "output_folder": str(tmp_path / "output"),
        "caption_enabled": True,
        "watermark_enabled": True,
        "cover_mode": UiCoverMode.DELAY_OVERLAY,
        "cover_delay_sec": "0",
        "intro_video_path": "",
        "manual_logo_path": "",
    }
    data.update(overrides)
    return UiRunState(**data)


def test_validate_requires_target_folder(tmp_path):
    state = _base_state(tmp_path, target_folder="")

    errors = validate_ui_state(state)

    assert any("target" in error.lower() for error in errors)


def test_validate_requires_output_folder(tmp_path):
    state = _base_state(tmp_path, output_folder="")

    errors = validate_ui_state(state)

    assert any("output" in error.lower() for error in errors)


def test_validate_handles_none_for_required_folders_without_crashing(tmp_path):
    state = _base_state(tmp_path, target_folder=None, output_folder=None)

    errors = validate_ui_state(state)

    assert any("target" in error.lower() for error in errors)
    assert any("output" in error.lower() for error in errors)


def test_validate_handles_non_string_manual_logo_path_without_crashing(tmp_path):
    state = _base_state(tmp_path, manual_logo_path=123)

    errors = validate_ui_state(state)

    assert any("logo" in error.lower() and ".png" in error.lower() for error in errors)


def test_validate_rejects_watermark_off(tmp_path):
    state = _base_state(tmp_path, watermark_enabled=False)

    errors = validate_ui_state(state)

    assert any("watermark" in error.lower() for error in errors)


def test_validate_requires_intro_for_intro_merge(tmp_path):
    state = _base_state(
        tmp_path,
        cover_mode=UiCoverMode.INTRO_MERGE,
        intro_video_path="",
    )

    errors = validate_ui_state(state)

    assert any("intro" in error.lower() for error in errors)


def test_validate_rejects_non_numeric_delay_for_delay_overlay(tmp_path):
    state = _base_state(tmp_path, cover_delay_sec="abc")

    errors = validate_ui_state(state)

    assert any("delay" in error.lower() and "number" in error.lower() for error in errors)


def test_validate_rejects_negative_delay_for_delay_overlay(tmp_path):
    state = _base_state(tmp_path, cover_delay_sec="-0.1")

    errors = validate_ui_state(state)

    assert any(">= 0" in error or "non-negative" in error.lower() for error in errors)


def test_validate_rejects_non_finite_delay_for_delay_overlay(tmp_path):
    for value in ("nan", "inf", "-inf"):
        state = _base_state(tmp_path, cover_delay_sec=value)

        errors = validate_ui_state(state)

        assert any("delay" in error.lower() and "finite" in error.lower() for error in errors)


def test_validate_allows_manual_logo_empty(tmp_path):
    state = _base_state(tmp_path, manual_logo_path="")

    errors = validate_ui_state(state)

    assert all("logo" not in error.lower() for error in errors)


def test_validate_rejects_manual_logo_non_png(tmp_path):
    state = _base_state(tmp_path, manual_logo_path="C:/logos/logo.jpg")

    errors = validate_ui_state(state)

    assert any("logo" in error.lower() and ".png" in error.lower() for error in errors)


def test_validate_accepts_valid_delay_overlay_state(tmp_path):
    state = _base_state(tmp_path, cover_delay_sec="1.5", manual_logo_path="/tmp/logo.PNG")

    errors = validate_ui_state(state)

    assert errors == []


def test_validate_accepts_valid_intro_merge_state(tmp_path):
    state = _base_state(
        tmp_path,
        cover_mode=UiCoverMode.INTRO_MERGE,
        intro_video_path="/tmp/intro.mp4",
        cover_delay_sec="not-used",
    )

    errors = validate_ui_state(state)

    assert errors == []
