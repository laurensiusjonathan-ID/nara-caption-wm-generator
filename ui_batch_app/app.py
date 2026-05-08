from __future__ import annotations

import queue
from pathlib import Path
import tkinter.filedialog as fd

import customtkinter as ctk

from ui_batch_app.controller import UiBatchController
from ui_batch_app.models import UiCoverMode, UiRunState, UiWatermarkPosition
from ui_batch_app.validators import validate_ui_state


class BatchApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Nara Batch Caption + Watermark")
        self.geometry("960x760")

        self._event_queue: queue.Queue[dict] = queue.Queue()
        self._controller = UiBatchController(on_event=self._event_queue.put)

        self._build_variables()
        self._build_layout()
        self._on_cover_mode_change()

        self.after(100, self._pump_events)

    def _build_variables(self) -> None:
        self.target_folder_var = ctk.StringVar(value="")
        self.output_folder_var = ctk.StringVar(value="")
        self.manual_logo_var = ctk.StringVar(value="")
        self.intro_video_var = ctk.StringVar(value="")

        self.caption_enabled_var = ctk.BooleanVar(value=True)
        self.watermark_enabled_var = ctk.BooleanVar(value=True)
        self.cover_mode_var = ctk.StringVar(value=UiCoverMode.DELAY_OVERLAY.value)
        self.cover_delay_var = ctk.StringVar(value="0")
        self.watermark_position_var = ctk.StringVar(value=UiWatermarkPosition.BOTTOM_RIGHT.value)

        self.summary_total_var = ctk.StringVar(value="Total: 0")
        self.summary_success_var = ctk.StringVar(value="Success: 0")
        self.summary_failed_var = ctk.StringVar(value="Failed: 0")
        self.summary_skipped_var = ctk.StringVar(value="Skipped: 0")

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=1)

        content = ctk.CTkFrame(self)
        content.grid(row=0, column=0, padx=16, pady=16, sticky="nsew")
        content.grid_columnconfigure(0, weight=1)

        self._build_paths_card(content)
        self._build_options_card(content)
        self._build_controls_card(content)
        self._build_summary_card(content)
        self._build_log_panel(content)

        content.grid_rowconfigure(5, weight=1)

    def _build_paths_card(self, content: ctk.CTkFrame) -> None:
        paths_card = ctk.CTkFrame(content)
        paths_card.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        paths_card.grid_columnconfigure(1, weight=1)

        self._build_path_row(paths_card, 0, "Target folder", self.target_folder_var, self._pick_target_folder)
        self._build_path_row(paths_card, 1, "Output folder", self.output_folder_var, self._pick_output_folder)
        self._build_path_row(paths_card, 2, "Manual logo (.png)", self.manual_logo_var, self._pick_manual_logo)
        self._build_intro_row(paths_card)

    def _build_intro_row(self, parent: ctk.CTkFrame) -> None:
        self.intro_label = ctk.CTkLabel(parent, text="Intro video")
        self.intro_label.grid(row=3, column=0, padx=8, pady=8, sticky="w")

        self.intro_entry = ctk.CTkEntry(parent, textvariable=self.intro_video_var)
        self.intro_entry.grid(row=3, column=1, padx=8, pady=8, sticky="ew")

        self.intro_browse_button = ctk.CTkButton(
            parent,
            text="Browse",
            width=100,
            command=self._pick_intro_video,
        )
        self.intro_browse_button.grid(row=3, column=2, padx=8, pady=8)

    def _build_options_card(self, content: ctk.CTkFrame) -> None:
        options_card = ctk.CTkFrame(content)
        options_card.grid(row=1, column=0, sticky="ew", padx=8, pady=8)
        options_card.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        ctk.CTkSwitch(options_card, text="Caption ON", variable=self.caption_enabled_var).grid(
            row=0,
            column=0,
            padx=8,
            pady=8,
            sticky="w",
        )

        watermark_switch = ctk.CTkSwitch(
            options_card,
            text="Watermark ON (locked)",
            variable=self.watermark_enabled_var,
            state="disabled",
        )
        watermark_switch.grid(row=0, column=1, padx=8, pady=8, sticky="w")
        self.watermark_enabled_var.set(True)

        ctk.CTkLabel(options_card, text="Watermark position").grid(
            row=1, column=0, padx=8, pady=4, sticky="w"
        )
        positions = [
            ("Kanan bawah", UiWatermarkPosition.BOTTOM_RIGHT),
            ("Kiri bawah", UiWatermarkPosition.BOTTOM_LEFT),
            ("Kanan atas", UiWatermarkPosition.TOP_RIGHT),
            ("Kiri atas", UiWatermarkPosition.TOP_LEFT),
        ]
        for idx, (label, pos) in enumerate(positions):
            ctk.CTkRadioButton(
                options_card,
                text=label,
                variable=self.watermark_position_var,
                value=pos.value,
            ).grid(row=1, column=1 + idx, padx=4, pady=4, sticky="w")

        ctk.CTkLabel(options_card, text="Cover mode").grid(row=2, column=0, padx=8, pady=4, sticky="w")
        ctk.CTkRadioButton(
            options_card,
            text="Delay overlay",
            variable=self.cover_mode_var,
            value=UiCoverMode.DELAY_OVERLAY.value,
            command=self._on_cover_mode_change,
        ).grid(row=2, column=1, padx=8, pady=4, sticky="w")
        ctk.CTkRadioButton(
            options_card,
            text="Intro merge",
            variable=self.cover_mode_var,
            value=UiCoverMode.INTRO_MERGE.value,
            command=self._on_cover_mode_change,
        ).grid(row=2, column=2, padx=8, pady=4, sticky="w")

        self.delay_frame = ctk.CTkFrame(options_card)
        self.delay_frame.grid(row=3, column=0, columnspan=3, sticky="ew", padx=8, pady=8)
        ctk.CTkLabel(self.delay_frame, text="Delay seconds").grid(row=0, column=0, padx=8, pady=8, sticky="w")
        ctk.CTkEntry(self.delay_frame, textvariable=self.cover_delay_var, width=150).grid(
            row=0,
            column=1,
            padx=8,
            pady=8,
            sticky="w",
        )

    def _build_controls_card(self, content: ctk.CTkFrame) -> None:
        controls_card = ctk.CTkFrame(content)
        controls_card.grid(row=2, column=0, sticky="ew", padx=8, pady=8)
        controls_card.grid_columnconfigure(0, weight=1)

        self.start_button = ctk.CTkButton(controls_card, text="Start", command=self._start_run)
        self.start_button.grid(row=0, column=0, padx=8, pady=8, sticky="w")

        self.progress_bar = ctk.CTkProgressBar(controls_card)
        self.progress_bar.grid(row=1, column=0, padx=8, pady=8, sticky="ew")
        self.progress_bar.set(0.0)

    def _build_summary_card(self, content: ctk.CTkFrame) -> None:
        summary_card = ctk.CTkFrame(content)
        summary_card.grid(row=3, column=0, sticky="ew", padx=8, pady=8)

        vars_to_render = [
            self.summary_total_var,
            self.summary_success_var,
            self.summary_failed_var,
            self.summary_skipped_var,
        ]
        for index, var in enumerate(vars_to_render):
            ctk.CTkLabel(summary_card, textvariable=var).grid(row=0, column=index, padx=8, pady=8, sticky="w")

    def _build_log_panel(self, content: ctk.CTkFrame) -> None:
        ctk.CTkLabel(content, text="Log").grid(row=4, column=0, sticky="w", padx=8, pady=(8, 0))
        self.log_textbox = ctk.CTkTextbox(content, height=280)
        self.log_textbox.grid(row=5, column=0, sticky="nsew", padx=8, pady=8)

    def _build_path_row(self, parent: ctk.CTkFrame, row: int, label: str, variable: ctk.StringVar, browse_command) -> None:
        ctk.CTkLabel(parent, text=label).grid(row=row, column=0, padx=8, pady=8, sticky="w")
        ctk.CTkEntry(parent, textvariable=variable).grid(row=row, column=1, padx=8, pady=8, sticky="ew")
        ctk.CTkButton(parent, text="Browse", width=100, command=browse_command).grid(
            row=row,
            column=2,
            padx=8,
            pady=8,
        )

    def _pick_target_folder(self) -> None:
        selected = fd.askdirectory(title="Select target folder")
        if selected:
            self.target_folder_var.set(selected)

    def _pick_output_folder(self) -> None:
        selected = fd.askdirectory(title="Select output folder")
        if selected:
            self.output_folder_var.set(selected)

    def _pick_manual_logo(self) -> None:
        selected = fd.askopenfilename(title="Select PNG logo", filetypes=[("PNG", "*.png")])
        if selected:
            self.manual_logo_var.set(selected)

    def _pick_intro_video(self) -> None:
        selected = fd.askopenfilename(
            title="Select intro video",
            filetypes=[("Video", "*.mp4 *.mov *.avi"), ("All files", "*.*")],
        )
        if selected:
            self.intro_video_var.set(selected)

    def _on_cover_mode_change(self) -> None:
        is_delay = self.cover_mode_var.get() == UiCoverMode.DELAY_OVERLAY.value
        if is_delay:
            self.delay_frame.grid()
            self.intro_label.grid_remove()
            self.intro_entry.grid_remove()
            self.intro_browse_button.grid_remove()
            return

        self.delay_frame.grid_remove()
        self.intro_label.grid()
        self.intro_entry.grid()
        self.intro_browse_button.grid()

    def _build_state(self) -> UiRunState:
        cover_mode = (
            UiCoverMode.INTRO_MERGE
            if self.cover_mode_var.get() == UiCoverMode.INTRO_MERGE.value
            else UiCoverMode.DELAY_OVERLAY
        )

        position = UiWatermarkPosition(self.watermark_position_var.get())

        return UiRunState(
            target_folder=self.target_folder_var.get(),
            output_folder=self.output_folder_var.get(),
            caption_enabled=bool(self.caption_enabled_var.get()),
            watermark_enabled=True,
            cover_mode=cover_mode,
            cover_delay_sec=self.cover_delay_var.get(),
            intro_video_path=self.intro_video_var.get(),
            manual_logo_path=self.manual_logo_var.get(),
            watermark_position=position,
        )

    def _start_run(self) -> None:
        state = self._build_state()
        errors = validate_ui_state(state)
        if errors:
            self._append_log("Validation error(s):")
            for error in errors:
                self._append_log(f"- {error}")
            return

        output_path = Path(state.output_folder)
        try:
            output_path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self._append_log(f"ERROR: Failed to create output folder: {exc}")
            self.start_button.configure(state="normal")
            return

        self.progress_bar.set(0.0)
        self._append_log("Starting run...")
        self.start_button.configure(state="disabled")
        self._controller.start_run(state)

    def _pump_events(self) -> None:
        handled_any = False
        while True:
            try:
                event = self._event_queue.get_nowait()
            except queue.Empty:
                break
            handled_any = True
            self._handle_event(event)

        if handled_any:
            self.update_idletasks()
        self.after(100, self._pump_events)

    def _handle_event(self, event: dict) -> None:
        event_type = event.get("type")
        if event_type == "log":
            self._append_log(str(event.get("message", "")))
            return

        if event_type == "error":
            self._append_log(f"ERROR: {event.get('message', 'Unknown error')}")
            self.start_button.configure(state="normal")
            return

        if event_type == "progress":
            processed = int(event.get("processed", 0))
            self._append_log(f"Processed items: {processed}")
            return

        if event_type == "summary":
            total = int(event.get("total", 0))
            success = int(event.get("success", 0))
            failed = int(event.get("failed", 0))
            skipped = int(event.get("skipped", 0))

            self.summary_total_var.set(f"Total: {total}")
            self.summary_success_var.set(f"Success: {success}")
            self.summary_failed_var.set(f"Failed: {failed}")
            self.summary_skipped_var.set(f"Skipped: {skipped}")

            ratio = 0.0 if total == 0 else min(1.0, max(0.0, (success + failed + skipped) / total))
            self.progress_bar.set(ratio)
            self._append_log(f"Finished with exit code {event.get('exit_code', 2)}")
            self.start_button.configure(state="normal")

    def _append_log(self, message: str) -> None:
        self.log_textbox.insert("end", f"{message}\n")
        self.log_textbox.see("end")
