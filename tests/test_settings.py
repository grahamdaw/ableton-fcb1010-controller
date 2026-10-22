from pathlib import Path

import pytest

from FCB1010.settings import DEFAULTS, Settings, load_settings, parse_settings

EXAMPLE = Path(__file__).parent.parent / "FCB1010" / "config.example.toml"


def test_missing_file_gives_defaults(tmp_path: Path) -> None:
    settings, errors = load_settings(tmp_path / "config.toml")
    assert settings == Settings()
    assert errors == []


def test_example_file_matches_defaults() -> None:
    settings, errors = load_settings(EXAMPLE)
    assert errors == []
    assert settings == DEFAULTS


def test_default_layout_matches_spec() -> None:
    sw = DEFAULTS.switches
    assert [sw[n].action for n in range(1, 11)] == [
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
    ]
    assert [sw[n].pc for n in range(1, 11)] == list(range(10))
    assert [sw[n].note for n in range(1, 11)] == list(range(60, 70))


def test_empty_document_gives_defaults() -> None:
    assert parse_settings({}) == (Settings(), [])


def test_malformed_toml_logs_and_uses_defaults(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text("midi_channel = = 3")
    settings, errors = load_settings(path)
    assert settings == Settings()
    assert len(errors) == 1 and "config.toml" in errors[0]


def test_swapping_two_switches() -> None:
    settings, errors = parse_settings(
        {"switches": {"1": {"action": "track_next"}, "2": {"action": "track_prev"}}}
    )
    assert errors == []
    assert settings.switches[1].action == "track_next"
    assert settings.switches[2].action == "track_prev"
    assert settings.switches[1].pc == 0


def test_unknown_action_logs_one_line_and_uses_default() -> None:
    settings, errors = parse_settings({"switches": {"3": {"action": "explode"}}})
    assert settings.switches[3].action == "clip_launch"
    assert len(errors) == 1
    assert "switches.3.action" in errors[0] and "explode" in errors[0]


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("midi_channel", 0),
        ("midi_channel", 17),
        ("midi_channel", "16"),
        ("midi_channel", True),
        ("dedup_window_ms", -1),
        ("navigation", "bounce"),
        ("box_width", "column"),
        ("scene_launch_advances", "yes"),
        ("debug", 1),
    ],
)
def test_invalid_scalar_falls_back_to_default(key: str, value: object) -> None:
    settings, errors = parse_settings({key: value})
    assert getattr(settings, key) == getattr(DEFAULTS, key)
    assert len(errors) == 1 and errors[0].startswith(f"{key}:")


def test_valid_scalars_are_used() -> None:
    settings, errors = parse_settings(
        {
            "midi_channel": 1,
            "dedup_window_ms": 30,
            "navigation": "wrap",
            "box_width": "slot",
            "scene_launch_advances": True,
            "debug": True,
        }
    )
    assert errors == []
    assert settings == Settings(
        midi_channel=1,
        dedup_window_ms=30,
        navigation="wrap",
        box_width="slot",
        scene_launch_advances=True,
        debug=True,
    )


def test_out_of_range_note() -> None:
    settings, errors = parse_settings({"switches": {"4": {"note": 200}}})
    assert settings.switches[4].note == 63
    assert len(errors) == 1 and "switches.4.note" in errors[0]


def test_duplicate_pc_keeps_first_and_defaults_later() -> None:
    settings, errors = parse_settings({"switches": {"5": {"pc": 0}}})
    assert settings.switches[1].pc == 0
    assert settings.switches[5].pc == 4
    assert len(errors) == 1 and "switches.5.pc" in errors[0]


def test_duplicate_note_that_still_clashes_resets_all_notes() -> None:
    # Switch 1 moves to 61 (switch 2's default); switch 2 asks for 61 too, so
    # its fallback (61) still clashes and every note falls back to its default.
    settings, errors = parse_settings({"switches": {"1": {"note": 61}, "2": {"note": 61}}})
    assert [settings.switches[n].note for n in range(1, 11)] == list(range(60, 70))
    assert len(errors) == 2


def test_unknown_switch_and_keys_are_reported() -> None:
    settings, errors = parse_settings(
        {"switches": {"11": {"action": "undo"}, "1": {"colour": "red"}}, "tempo": 120}
    )
    assert settings == DEFAULTS
    assert len(errors) == 3


def test_switches_not_a_table() -> None:
    settings, errors = parse_settings({"switches": "nope"})
    assert settings.switches == DEFAULTS.switches
    assert len(errors) == 1
