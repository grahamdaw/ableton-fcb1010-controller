"""FCB1010 MIDI Remote Script for Ableton Live 12."""

from typing import Any


def create_instance(c_instance: Any) -> Any:
    """Entry point Live calls when the control surface is selected."""
    from .live_adapter import FCB1010

    return FCB1010(c_instance)
