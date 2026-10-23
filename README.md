# ableton-fcb1010-controller

An Ableton Live 12 MIDI Remote Script that turns a **stock Behringer FCB1010**
into a hands-free Session View controller, with Live's session highlight box
showing where the focus is — the way Push and Launchpad do.

> **Status:** v0.1.0, not yet verified in Live. See [docs/TODO.md](docs/TODO.md)
> for the first hardware test.

## Key features

- **Ten switches, one job each** (bank 00):

  | Row    | Left      |           | Middle         |                  | Right         |
  | ------ | --------- | --------- | -------------- | ---------------- | ------------- |
  | Top    | 6 Scene ↑ | 7 Scene ↓ | 8 Launch scene | 9 Stop all clips | 10 Undo       |
  | Bottom | 1 Track ← | 2 Track → | 3 Launch clip  | 4 Stop clip      | 5 Record slot |

- **Focus box** around the selected scene, drawn by Live itself. It follows
  Live's selection, so the mouse, arrow keys and the pedal all move the same
  focus.
- **Safe edge cases:** no wrapping at the ends, Launch clip on an empty slot
  does nothing, and Record slot never overwrites a clip.
- **One press, one action:** the PC and note the pedal sends for each press
  are merged, so rapid repeated presses all count, with no doubles.
- **One `config.toml`:** remap switches, change channel, PC or notes, and
  choose clamp or wrap, row or slot box, and debug logging. Apply it by
  re-selecting the control surface; no restart needed.
- **Works in any Set**, including an empty one, with no per-Set setup.
- **Never crashes Live:** errors are logged to Log.txt with an `FCB1010:`
  prefix, and the press is dropped.

## Limitations

- **No feedback on the pedal.** The stock FCB1010 firmware can't receive
  LED or display updates.
- **Bank 00 only;** banks 01–09 are reserved for later. Expression pedals
  are disabled.
- **Session View only:** no device, mixer or Arrangement control, and no
  transport beyond Stop all clips.
- **Live 12 on macOS** (12.4.x targeted). The `install.sh` script and the dev
  tools assume macOS.
- **Built on Live's undocumented `ableton.v3` framework**, so a future Live
  update could break the script.
- **The pedal must be programmed by hand** from an FCB1010 editor; the
  preset dump (`.syx`) isn't in the repo yet.

## Docs

- [docs/specs/INITIAL_SPEC.md](docs/specs/INITIAL_SPEC.md): the original v1
  requirements (switch behaviour, MIDI handling, config, acceptance tests).
- [docs/LIVING_SPEC.md](docs/LIVING_SPEC.md): what the code does today,
  decisions and deviations from the initial spec, what we've learned about
  Live and the pedal, and references.
- [docs/TODO.md](docs/TODO.md): open work, starting with testing on a real
  setup.
- [pedal/README.md](pedal/README.md): how to program the FCB1010.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/grahamdaw/ableton-fcb1010-controller/main/install.sh | bash
```

Then:

1. Restart Live.
2. Preferences → Link, Tempo & MIDI: **Control Surface** = `FCB1010`,
   **Input** = your USB-MIDI interface, **Output** = None.
3. Turn **Track** and **Remote** off for that input port.

Run `install.sh` again to update; your `config.toml` is kept.

## Configuration

Edit `FCB1010/config.toml`, then re-select the control surface in
Preferences. Each key is explained in
[config.example.toml](FCB1010/config.example.toml).

| Key | Default | Meaning |
| --- | --- | --- |
| `midi_channel` | `16` | Channel the pedal sends on (1–16) |
| `dedup_window_ms` | `50` | A PC and a note for the same switch this close together are one press |
| `navigation` | `"clamp"` | At the first/last scene or track: `"clamp"` stops, `"wrap"` wraps around |
| `box_width` | `"row"` | Box the whole scene row (`"row"`) or only the focused slot (`"slot"`) |
| `scene_launch_advances` | `false` | Move focus to the next scene after Launch scene |
| `debug` | `false` | Log every press to Log.txt |
| `[switches]` | layout above | `N = { action = "...", pc = 0-127, note = 0-127 }` |

Actions: `track_prev`, `track_next`, `clip_launch`, `clip_stop`,
`slot_record`, `scene_prev`, `scene_next`, `scene_launch`, `stop_all`,
`undo`, `none`.

An invalid value logs one `FCB1010:` error line naming the key, and that
key's default is used.

## Development

```bash
uv sync
```

```bash
make check
```

- `make check` runs ruff, pyright and pytest, the same as CI.
- `make install` links this checkout into Remote Scripts. After editing
  the code, restart Live to load it; re-selecting the control surface only
  re-reads `config.toml`.
- `make log` follows Log.txt, filtered to `FCB1010:` lines.
- `make smoke PORT="IAC Driver Bus 1"` sends the ten presses to a running
  Live; it needs `debug = true`.

`FCB1010/live_adapter.py` is the only module that imports Live. Everything
else is plain Python, tested in `tests/` against a fake Song.

**Release:**

1. `make check` passes and CI is green.
2. Run the smoke test, then the acceptance checklist with the pedal.
3. Bump the version in `pyproject.toml`, update `CHANGELOG.md`, and tag the
   release.
