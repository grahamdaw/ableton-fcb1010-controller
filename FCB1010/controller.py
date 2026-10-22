"""Glue between Live's callbacks and the pure logic modules.

Holds no Live imports: ``live_adapter`` hands it the Song, a clock, a
logger and a callback that draws the highlight box, so the whole path from
a MIDI message to a Live action can be exercised in tests.
"""

from __future__ import annotations

from collections.abc import Callable

from . import actions
from .actions import SongLike
from .midi import PressDecoder
from .session_box import Box, box_for_song
from .settings import Settings

LOG_PREFIX = "FCB1010: "


class Controller:
    """Turns MIDI into actions and keeps the highlight box on Live's selection."""

    def __init__(
        self,
        settings: Settings,
        song: Callable[[], SongLike],
        log: Callable[[str], None],
        set_highlight: Callable[[Box], None],
    ) -> None:
        self.settings = settings
        self._song = song
        self._log = log
        self._set_highlight = set_highlight
        self._decoder = PressDecoder(settings)
        self._box: Box | None = None

    @property
    def notes(self) -> list[int]:
        """Notes Live must forward to the script."""
        return self._decoder.notes

    def log(self, message: str) -> None:
        """Write one prefixed line to Live's Log.txt."""
        self._log(LOG_PREFIX + message)

    def debug(self, message: str) -> None:
        """Log only when debug logging is enabled."""
        if self.settings.debug:
            self.log(message)

    def on_midi(self, midi_bytes: tuple[int, ...], now_ms: float) -> None:
        """Handle one incoming MIDI message; errors are logged and the press is dropped."""
        try:
            switch = self._decoder.feed(midi_bytes, now_ms)
            if switch is None:
                return
            action = self.settings.switches[switch].action
            result = actions.run(action, self._song(), self.settings)
            self.debug(f"switch {switch} {action}: {result}")
        except Exception as e:
            self.log(f"error handling {list(midi_bytes)}: {e!r}")

    def refresh_box(self) -> None:
        """Recompute the highlight box from Live's selection and redraw it if it moved."""
        try:
            box = box_for_song(self._song(), self.settings.box_width)
            if box != self._box:
                self._box = box
                self._set_highlight(box)
        except Exception as e:
            self.log(f"error updating highlight box: {e!r}")

    def draw(self, box: Box) -> None:
        """Draw ``box`` directly, e.g. :data:`~FCB1010.session_box.HIDDEN` on shutdown."""
        self._box = box
        self._set_highlight(box)

    def forget_box(self) -> None:
        """Forget the last drawn box so the next refresh redraws it."""
        self._box = None
