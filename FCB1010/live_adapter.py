"""The Control Surface Live instantiates: the only module that imports Live.

Built on Live's ``ableton.v3`` framework. It forwards the pedal's notes to the
script, passes incoming MIDI to the :class:`~FCB1010.controller.Controller`,
and draws Live's session highlight box wherever Live's selection is.

v3's stock ``SessionRingComponent`` is not used for the box: its width is
fixed at creation and v3 only enables it once the controller answers a SysEx
identity request, which the stock FCB1010 cannot. :class:`FocusBox` takes the
same ``set_session_highlight`` dependency v3 injects into its ring.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import Live
from ableton.v3.base import const, depends, nop  # pyright: ignore[reportMissingImports]
from ableton.v3.control_surface import (  # pyright: ignore[reportMissingImports]
    Component,
    ControlSurface,
    ControlSurfaceSpecification,
    ElementsBase,
)

from .controller import Controller
from .session_box import HIDDEN, Box
from .settings import load_settings

CONFIG_PATH = Path(__file__).with_name("config.toml")


class FocusBox(Component):
    """Live's session highlight, placed and sized from a :class:`Box`."""

    @depends(set_session_highlight=const(nop))
    def __init__(self, set_session_highlight: Callable[..., None] = nop, *a: Any, **k: Any) -> None:
        self._set_session_highlight = set_session_highlight
        self._box = HIDDEN
        super().__init__(*a, name="Focus_Box", **k)

    def show(self, box: Box) -> None:
        """Draw ``box`` (or hide the highlight for :data:`HIDDEN`) while enabled."""
        self._box = box
        self._update()

    def on_enabled_changed(self) -> None:
        super().on_enabled_changed()
        self._update()

    def disconnect(self) -> None:
        self._set_session_highlight(-1, -1, -1, -1, False)
        super().disconnect()

    def _update(self) -> None:
        box = self._box if self.is_enabled() else HIDDEN
        self._set_session_highlight(
            box.track_offset, box.scene_offset, box.width, box.height, False
        )


class Specification(ControlSurfaceSpecification):
    """No elements or mappings: the pedal's MIDI is handled in receive_midi."""

    elements_type = ElementsBase


class FCB1010(ControlSurface):
    """Behringer FCB1010 (stock firmware) driving Session View."""

    def __init__(self, c_instance: Any) -> None:
        # Built before the framework's __init__, which calls setup() on us.
        settings, errors = load_settings(CONFIG_PATH)
        self._focus_box: FocusBox | None = None
        self._controller = Controller(
            settings,
            song=c_instance.song,
            log=c_instance.log_message,
            set_highlight=self._show_box,
        )
        super().__init__(specification=Specification, c_instance=c_instance)
        for error in errors:
            self._controller.log(f"config.toml {error}")
        self._guard(self._add_listeners)
        self._controller.refresh_box()
        self._controller.log(f"loaded; config {'found' if CONFIG_PATH.exists() else 'not found'}")

    def setup(self) -> None:
        """Called by v3 inside its component guard, with dependencies injected."""
        super().setup()
        self._focus_box = FocusBox()

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
        """Every forwarded message (and any Program Change Live passes on) lands here.

        Replaces v3's element dispatch, which would log the pedal's messages as unknown.
        """
        with self.component_guard():
            self._controller.on_midi(tuple(midi_bytes), time.monotonic() * 1000)

    def refresh_state(self) -> None:
        """Live asks the script to resend its state, e.g. after a port change."""
        super().refresh_state()
        self._controller.forget_box()
        self._controller.refresh_box()

    # --- Helpers ---------------------------------------------------------------

    def _show_box(self, box: Box) -> None:
        if self._focus_box is not None:
            self._focus_box.show(box)

    def _on_change(self) -> None:
        self._controller.refresh_box()

    def _add_listeners(self) -> None:
        # register_slot listeners are removed by the framework on disconnect.
        song = self._c_instance.song()
        self.register_slot(song.view, self._on_change, "selected_scene")
        self.register_slot(song.view, self._on_change, "selected_track")
        self.register_slot(song, self._on_change, "scenes")
        self.register_slot(song, self._on_change, "visible_tracks")

    def _guard(self, fn: Callable[[], None]) -> None:
        try:
            fn()
        except Exception as e:
            self._controller.log(f"error in {getattr(fn, '__name__', 'callback')}: {e!r}")
