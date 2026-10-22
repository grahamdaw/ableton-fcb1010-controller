# ableton-fcb1010-controller

An Ableton Live 12 MIDI Remote Script that turns a **stock Behringer FCB1010**
into a hands-free Session View controller: move the focused scene and track,
launch and stop clips and scenes, record into the focused slot, undo — with
Live's session highlight box showing where the focus is, like Push and
Launchpad. The full requirements are in
[docs/specs/INITIAL_SPEC.md](docs/specs/INITIAL_SPEC.md).

## Pedal layout (bank 00)

| Row    | Left         |              | Middle        |                | Right         |
| ------ | ------------ | ------------ | ------------- | -------------- | ------------- |
| Top    | 6 Scene ↑    | 7 Scene ↓    | 8 Launch scene | 9 Stop all clips | 10 Undo     |
| Bottom | 1 Track ←    | 2 Track →    | 3 Launch clip | 4 Stop clip    | 5 Record slot |

Every preset sends one Program Change (0–9) and one note (60–69) on MIDI
channel 16, nothing else; see [pedal/README.md](pedal/README.md).

## Install

Requirements: macOS, Live 12 (12.4.x is the target), git, a class-compliant
USB-MIDI interface between the FCB1010's MIDI Out and the Mac.

```bash
curl -fsSL https://raw.githubusercontent.com/grahamdaw/ableton-fcb1010-controller/main/install.sh | bash
```

This clones the repo to `~/.local/share/ableton-fcb1010-controller`, creates
`FCB1010/config.toml` from the example, and links the `FCB1010` folder into
`~/Music/Ableton/User Library/Remote Scripts/`. Run it again to update; your
`config.toml` is kept.

Then, once:

1. Restart Live.
2. Preferences → Link, Tempo & MIDI: **Control Surface** = `FCB1010`,
   **Input** = the USB-MIDI interface, **Output** = None.
3. In the MIDI Ports list, turn **Track** and **Remote** off for that input,
   so the pedal's notes never reach instruments or MIDI Map.
4. Program the pedal (see [pedal/README.md](pedal/README.md)).

## Configuration

`FCB1010/config.toml` (copied from
[config.example.toml](FCB1010/config.example.toml)) holds every setting.
Edit it, then re-select the control surface in Preferences to apply — no
restart. Missing keys use their defaults; an invalid value logs one
`FCB1010:` error line in Log.txt naming the key, and that key's default is
used.

| Key | Default | Meaning |
| --- | --- | --- |
| `midi_channel` | `16` | Channel the pedal sends on (1–16) |
| `dedup_window_ms` | `50` | A PC and a note for the same switch this close together are one press |
| `navigation` | `"clamp"` | At the first/last scene or track: `"clamp"` stops, `"wrap"` wraps around |
| `box_width` | `"row"` | Highlight the whole focused scene (`"row"`) or only the focused slot (`"slot"`) |
| `scene_launch_advances` | `false` | After Launch scene, move focus to the next scene |
| `debug` | `false` | Log every press and what it did to Log.txt |
| `[switches]` | layout above | One line per switch: `N = { action = "...", pc = 0-127, note = 0-127 }` |

Actions: `track_prev`, `track_next`, `clip_launch`, `clip_stop`,
`slot_record`, `scene_prev`, `scene_next`, `scene_launch`, `stop_all`,
`undo`, `none`.

## Development

```bash
uv sync
```

```bash
make check
```

`make check` runs ruff, pyright (with
[ableton-live-stubs](https://pypi.org/project/ableton-live-stubs/)) and
pytest — the same as CI. Install the git hook with `uv run pre-commit install`.

Layout: `FCB1010/live_adapter.py` is the only module that imports Live;
`settings.py`, `midi.py`, `actions.py`, `session_box.py` and `controller.py`
are plain Python, tested in `tests/` against a fake Song.

**Dev loop**

1. `make install` links this checkout (instead of a separate clone) into
   Remote Scripts.
2. Edit code, then re-select the control surface in Live's Preferences
   (set it to None and back) to reload.
3. `make log` follows Log.txt, filtered to `FCB1010:` lines.

**Smoke test in Live**

1. Enable the IAC Driver in Audio MIDI Setup and pick its bus as the
   FCB1010 input in Live. Set `debug = true` in `config.toml`, re-select.
2. `make smoke PORT="IAC Driver Bus 1"` sends the ten presses as PC + note
   and checks Log.txt for ten `FCB1010: switch N` lines and no errors.

## Release

1. `make check` passes and CI is green on `main`.
2. Run the smoke test, then the acceptance checklist in the spec with the pedal.
3. Bump `version` in `pyproject.toml`, add a CHANGELOG entry, tag `vX.Y.Z`.
