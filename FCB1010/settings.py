"""Load and validate ``config.toml``.

Every setting has a built-in default. A missing file or key falls back to
the default; an invalid value logs one error naming the key and the default
is used for that key. Loading never raises.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

ACTIONS: tuple[str, ...] = (
    "track_prev",
    "track_next",
    "clip_launch",
    "clip_stop",
    "slot_record",
    "scene_prev",
    "scene_next",
    "scene_launch",
    "stop_all",
    "undo",
    "none",
)

NAVIGATION_MODES: tuple[str, ...] = ("clamp", "wrap")
BOX_WIDTHS: tuple[str, ...] = ("row", "slot")
SWITCH_COUNT = 10


@dataclass(frozen=True)
class Switch:
    """One footswitch: the action it triggers and the PC/note the pedal sends for it."""

    number: int
    action: str
    pc: int
    note: int


def _default_switches() -> dict[int, Switch]:
    layout = (
        "track_prev",
        "track_next",
        "clip_launch",
        "clip_stop",
        "slot_record",
        "scene_prev",
        "scene_next",
        "scene_launch",
        "stop_all",
        "undo",
    )
    return {
        n: Switch(number=n, action=layout[n - 1], pc=n - 1, note=59 + n)
        for n in range(1, SWITCH_COUNT + 1)
    }


@dataclass(frozen=True)
class Settings:
    """All runtime configuration for the script."""

    midi_channel: int = 16
    switches: dict[int, Switch] = field(default_factory=_default_switches)
    dedup_window_ms: int = 50
    navigation: str = "clamp"
    box_width: str = "row"
    scene_launch_advances: bool = False
    debug: bool = False


DEFAULTS = Settings()


def load_settings(path: Path) -> tuple[Settings, list[str]]:
    """Read ``path`` and return the settings plus one error line per rejected key.

    A missing file is not an error: the defaults are returned silently.
    """
    if not path.exists():
        return Settings(), []
    try:
        import tomllib

        with path.open("rb") as f:
            data = tomllib.load(f)
    except Exception as e:  # tomllib may be absent or the file malformed
        return Settings(), [f"{path.name}: cannot be read ({e}); using defaults"]
    return parse_settings(data)


def parse_settings(data: dict[str, Any]) -> tuple[Settings, list[str]]:
    """Validate an already-parsed TOML document; see :func:`load_settings`."""
    errors: list[str] = []
    d = DEFAULTS

    def pick_int(key: str, default: int, lo: int, hi: int) -> int:
        value = data.get(key, default)
        if isinstance(value, bool) or not isinstance(value, int) or not lo <= value <= hi:
            errors.append(f"{key}: expected an integer {lo}-{hi}, got {value!r}; using {default}")
            return default
        return value

    def pick_choice(key: str, default: str, choices: tuple[str, ...]) -> str:
        value = data.get(key, default)
        if value not in choices:
            errors.append(
                f"{key}: expected one of {', '.join(choices)}, got {value!r}; using {default!r}"
            )
            return default
        return value

    def pick_bool(key: str, default: bool) -> bool:
        value = data.get(key, default)
        if not isinstance(value, bool):
            errors.append(f"{key}: expected true or false, got {value!r}; using {default}")
            return default
        return value

    settings = Settings(
        midi_channel=pick_int("midi_channel", d.midi_channel, 1, 16),
        switches=_parse_switches(data.get("switches", {}), errors),
        dedup_window_ms=pick_int("dedup_window_ms", d.dedup_window_ms, 0, 1000),
        navigation=pick_choice("navigation", d.navigation, NAVIGATION_MODES),
        box_width=pick_choice("box_width", d.box_width, BOX_WIDTHS),
        scene_launch_advances=pick_bool("scene_launch_advances", d.scene_launch_advances),
        debug=pick_bool("debug", d.debug),
    )
    for key in data:
        if key not in _KNOWN_KEYS:
            errors.append(f"{key}: unknown setting; ignored")
    return settings, errors


_KNOWN_KEYS = frozenset(
    (
        "midi_channel",
        "switches",
        "dedup_window_ms",
        "navigation",
        "box_width",
        "scene_launch_advances",
        "debug",
    )
)


def _parse_switches(raw: Any, errors: list[str]) -> dict[int, Switch]:
    defaults = DEFAULTS.switches
    if not isinstance(raw, dict):
        errors.append(f"switches: expected a table, got {raw!r}; using the default layout")
        return dict(defaults)

    switches = dict(defaults)
    for key, entry in raw.items():
        name = f"switches.{key}"
        number = int(key) if str(key).isdigit() else 0
        if not 1 <= number <= SWITCH_COUNT:
            errors.append(f"{name}: unknown switch, expected 1-{SWITCH_COUNT}; ignored")
            continue
        if not isinstance(entry, dict):
            errors.append(f"{name}: expected a table {{ action, pc, note }}; using default")
            continue
        default = defaults[number]
        sw = default
        if "action" in entry:
            if entry["action"] in ACTIONS:
                sw = replace(sw, action=entry["action"])
            else:
                errors.append(
                    f"{name}.action: unknown action {entry['action']!r}; using {default.action!r}"
                )
        for field_name in ("pc", "note"):
            if field_name in entry:
                value = entry[field_name]
                if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 127:
                    errors.append(
                        f"{name}.{field_name}: expected an integer 0-127, got {value!r}; "
                        f"using {getattr(default, field_name)}"
                    )
                else:
                    sw = replace(sw, **{field_name: value})
        for extra in entry.keys() - {"action", "pc", "note"}:
            errors.append(f"{name}.{extra}: unknown key; ignored")
        switches[number] = sw

    for field_name in ("pc", "note"):
        _resolve_duplicates(switches, field_name, errors)
    return switches


def _resolve_duplicates(switches: dict[int, Switch], field_name: str, errors: list[str]) -> None:
    """Give a later switch reusing a PC/note its default; reset all if they still clash."""
    seen: dict[int, int] = {}
    for number in sorted(switches):
        value = getattr(switches[number], field_name)
        if value in seen:
            default = getattr(DEFAULTS.switches[number], field_name)
            errors.append(
                f"switches.{number}.{field_name}: {value} is already used by switch "
                f"{seen[value]}; using {default}"
            )
            switches[number] = replace(switches[number], **{field_name: default})
            value = default
        seen.setdefault(value, number)
    values = [getattr(sw, field_name) for sw in switches.values()]
    if len(set(values)) != len(values):
        errors.append(
            f"switches: {field_name} values still clash; using every default {field_name}"
        )
        for number, sw in switches.items():
            switches[number] = replace(
                sw, **{field_name: getattr(DEFAULTS.switches[number], field_name)}
            )
