"""Turn raw MIDI from a stock FCB1010 into exactly one event per switch press.

The stock firmware sends a Program Change and then a note for each press,
and alternates note-on/note-off on repeated presses of the same preset. A
PC and a note for the same switch within the de-duplication window are one
press; either message alone is also a press.
"""

from __future__ import annotations

from dataclasses import dataclass

from .settings import Settings

PROGRAM_CHANGE = 0xC0
NOTE_ON = 0x90
NOTE_OFF = 0x80


@dataclass
class _LastEvent:
    switch: int
    kind: str
    time_ms: float
    paired: bool = False


class PressDecoder:
    """Stateful decoder: feed it MIDI messages, get back switch numbers (1-10)."""

    def __init__(self, settings: Settings) -> None:
        self._channel = settings.midi_channel - 1
        self._window_ms = settings.dedup_window_ms
        self._by_pc = {sw.pc: sw.number for sw in settings.switches.values()}
        self._by_note = {sw.note: sw.number for sw in settings.switches.values()}
        self._last: _LastEvent | None = None

    @property
    def notes(self) -> list[int]:
        """Notes the decoder listens for, so the caller can ask Live to forward them."""
        return sorted(self._by_note)

    def feed(self, midi_bytes: tuple[int, ...], now_ms: float) -> int | None:
        """Return the switch number pressed by this message, or None if it is not a new press."""
        parsed = self._parse(midi_bytes)
        if parsed is None:
            return None
        switch, kind = parsed
        last = self._last
        if (
            last is not None
            and not last.paired
            and last.switch == switch
            and last.kind != kind
            and now_ms - last.time_ms <= self._window_ms
        ):
            last.paired = True
            return None
        self._last = _LastEvent(switch, kind, now_ms)
        return switch

    def _parse(self, midi_bytes: tuple[int, ...]) -> tuple[int, str] | None:
        if not midi_bytes:
            return None
        status = midi_bytes[0]
        if status >= 0xF0 or status & 0x0F != self._channel:
            return None
        message = status & 0xF0
        if message == PROGRAM_CHANGE and len(midi_bytes) >= 2:
            switch = self._by_pc.get(midi_bytes[1])
            return (switch, "pc") if switch is not None else None
        if message in (NOTE_ON, NOTE_OFF) and len(midi_bytes) >= 3:
            switch = self._by_note.get(midi_bytes[1])
            return (switch, "note") if switch is not None else None
        return None
