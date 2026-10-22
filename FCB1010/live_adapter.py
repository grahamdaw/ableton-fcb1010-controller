"""The Control Surface Live instantiates: the only module that imports Live.

It forwards the pedal's notes to the script, passes incoming MIDI to the
:class:`~FCB1010.controller.Controller`, and draws Live's session highlight
box wherever Live's selection is.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import Live
from _Framework.ControlSurface import (  # pyright: ignore[reportMissingImports]
    ControlSurface,
)

from .controller import Controller
from .session_box import HIDDEN
from .settings import load_settings

CONFIG_PATH = Path(__file__).with_name("config.toml")


class FCB1010(ControlSurface):
    """Behringer FCB1010 (stock firmware) driving Session View."""

    def __init__(self, c_instance: Any) -> None:
        # Built before the framework's __init__, which may call back into us.
        settings, errors = load_settings(CONFIG_PATH)
        self._controller = Controller(
            settings,
            song=c_instance.song,
            log=c_instance.log_message,
            set_highlight=lambda box: c_instance.set_session_highlight(
                box.track_offset, box.scene_offset, box.width, box.height, False
            ),
        )
        self._listening = False
        super().__init__(c_instance)
        for error in errors:
            self._controller.log(f"config.toml {error}")
        self._guard(self._add_listeners)
        self._controller.refresh_box()
        self._controller.log(f"loaded; config {'found' if CONFIG_PATH.exists() else 'not found'}")

    # --- Live callbacks ------------------------------------------------------

    def build_midi_map(self, midi_map_handle: int) -> None:
        """Ask Live to forward the pedal's notes on the configured channel to us."""
        super().build_midi_map(midi_map_handle)

        def forward() -> None:
            channel = self._controller.settings.midi_channel - 1
            handle = self._c_instance.handle()
            for note in self._controller.notes:
                Live.MidiMap.forward_midi_note(handle, midi_map_handle, channel, note)

        self._guard(forward)

    def receive_midi(self, midi_bytes: tuple[int, ...]) -> None:
        """Every forwarded message (and any Program Change Live passes on) lands here."""
        self._controller.on_midi(tuple(midi_bytes), time.monotonic() * 1000)

    def refresh_state(self) -> None:
        """Live asks the script to resend its state, e.g. after a port change."""
        super().refresh_state()
        self._controller.forget_box()
        self._controller.refresh_box()

    def disconnect(self) -> None:
        """Script disabled or Live quitting: remove listeners and the box."""
        self._guard(self._remove_listeners)
        self._guard(lambda: self._controller.draw(HIDDEN))
        super().disconnect()

    # --- Helpers ---------------------------------------------------------------

    def _on_change(self) -> None:
        self._controller.refresh_box()

    def _add_listeners(self) -> None:
        song = self._c_instance.song()
        song.view.add_selected_scene_listener(self._on_change)
        song.view.add_selected_track_listener(self._on_change)
        song.add_scenes_listener(self._on_change)
        song.add_visible_tracks_listener(self._on_change)
        self._listening = True

    def _remove_listeners(self) -> None:
        if not self._listening:
            return
        self._listening = False
        song = self._c_instance.song()
        for has, remove in (
            (song.view.selected_scene_has_listener, song.view.remove_selected_scene_listener),
            (song.view.selected_track_has_listener, song.view.remove_selected_track_listener),
            (song.scenes_has_listener, song.remove_scenes_listener),
            (song.visible_tracks_has_listener, song.remove_visible_tracks_listener),
        ):
            if has(self._on_change):
                remove(self._on_change)

    def _guard(self, fn: Any) -> None:
        try:
            fn()
        except Exception as e:
            self._controller.log(f"error in {getattr(fn, '__name__', 'callback')}: {e!r}")
