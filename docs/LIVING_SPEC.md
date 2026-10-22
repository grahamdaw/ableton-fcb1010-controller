# Living spec

This document describes what the code does now. The original requirements
stay unchanged in [specs/INITIAL_SPEC.md](specs/INITIAL_SPEC.md); this file
records where the implementation settled, why, and what we've learned along
the way. Update it whenever behaviour, a decision or a finding changes.

Last updated: 2026-10-22 (v0.1.0, before the first test in Live).

## Status

| Area | State |
| --- | --- |
| Decision logic (settings, MIDI, actions, box geometry, glue) | Done; 150 unit tests |
| Live adapter (`ableton.v3`) | Written, **not yet loaded in Live** |
| install.sh / dev tasks / smoke test | Done; install.sh tested in temp dirs |
| Pedal preset `.syx` | Missing; must be exported from an editor |
| Acceptance checklist | Not run; see [TODO.md](TODO.md) |

## Architecture

```
FCB1010/
  __init__.py        create_instance only (lazy import, so tests can import the package)
  live_adapter.py    the only module that imports Live / ableton.v3
  controller.py      Live-free glue: MIDI -> press -> action; box redraws; guarded logging
  midi.py            PressDecoder: channel filter, PC/note -> switch, de-duplication
  actions.py         the ten switch jobs, written against Song/Track/Scene/ClipSlot protocols
  session_box.py     highlight geometry from the current selection
  settings.py        defaults + config.toml validation
  config.example.toml
tests/fake_live.py   in-memory Song used by every test
```

A press flows: Live → `FCB1010.receive_midi` → `Controller.on_midi` →
`PressDecoder.feed` → `actions.run` → Live API. Changes to the selection or
to the track and scene lists trigger listeners → `Controller.refresh_box` →
`FocusBox.show` → `c_instance.set_session_highlight`.

The "only `live_adapter.py` imports Live" rule is enforced by a test
(`tests/test_package.py`).

## Decisions and deviations from the initial spec

| Topic | Initial spec | Implemented | Why |
| --- | --- | --- | --- |
| Framework | `ableton.v3` (default) | `ableton.v3` `ControlSurface` | Followed the default. PR #6 first used `_Framework`, then switched to v3. |
| Focus box | v3 "ready session-ring component" | Own `FocusBox` v3 `Component` using the injected `set_session_highlight` | v3's `SessionRingComponent` has a fixed width and is only enabled after a SysEx identity reply (see Learnings) |
| Module layout | `midi`, `actions`, `session_box`, `settings`, `live_adapter` | Plus `controller.py` | Keeps the MIDI → action → box path testable without Live |
| `config.toml` | One file beside the script | `config.example.toml` committed; `config.toml` git-ignored and created once by install.sh | Local edits survive `git pull` updates |
| Track ←/→ from a return or master track | Not specified | → goes to the first regular track, ← to the last | Gives a predictable way back into the grid |
| Record slot on a slot already waiting to record | Not specified | No-op | Avoids a second fire cancelling or restarting a pending recording |
| "Track cannot be armed" | Group, return, no input | `can_be_armed` is false, or the track has neither audio nor MIDI input | Matches the Live API properties |
| Launch scene | Focus stays, or advances via config | `scene.fire(False, False)`, then an explicit move if `scene_launch_advances` | Stops Live's own "Select Next Scene on Launch" preference from moving the focus |
| Folded and hidden tracks | Visible only (default) | Uses `song.visible_tracks` | Default kept |
| Smoke test | Checks Log.txt for `FCB1010:` lines | Requires `debug = true` | Presses are only logged in debug mode |
| Dev tasks | `smoke`, `log` | `make smoke`, `make log`, `make check`, `make install` | One entry point |

The other open-question defaults stand: clamp at the ends, row-width box,
focus stays on Launch scene.

## Learnings

### Live's MIDI API
- **Program Change can't be forwarded to a script.** `Live.MidiMap` can
  forward only notes, CCs and pitch bend (`forward_midi_note`,
  `forward_midi_cc`, `forward_midi_pitchbend`). The script asks Live to
  forward the ten notes. PC handling stays in `PressDecoder` in case Live
  passes PCs through anyway. So the **note path is probably the one that
  matters**, and it already turns every press into an event, because the
  firmware toggles note-on and note-off.
- The `midi_channel` argument to `forward_midi_note` is 0-based (channel 16
  is 15).
- v3's default `receive_midi` sends messages to its control elements and
  logs anything it doesn't recognise as "Got unknown message". The script
  overrides `receive_midi` because it has no elements.

### `ableton.v3`
- **v3 has no public documentation.** Its API was read from decompiled Live 12
  scripts (see References). Some decompiled files are partial, so expect
  small differences in Live 12.4.
- `ControlSurface.__init__(specification, c_instance=...)` builds the elements
  from `specification.elements_type` and then calls `setup()` inside its
  component guard, so dependencies like `set_session_highlight` are
  injected. `elements_type = ElementsBase` gives a surface with no elements.
- **The stock session ring isn't usable here.** v3 only enables
  `SessionRingComponent` once the controller answers a SysEx identity request
  (`_can_enable_session_ring = is_identifiable and …`). With no output port,
  the FCB1010 can't answer, so the ring would never show. Its
  `num_tracks` is also fixed when it is created, while the spec wants the
  full grid width.
- Hiding the highlight is `set_session_highlight(-1, -1, -1, -1, False)`,
  the same call v3's ring uses.
- `register_slot(subject, listener, "event")` adds Live listeners that the
  framework removes on disconnect.
- `self.song` is a property in v2/v3 (it was a method in `_Framework`). The
  adapter calls `c_instance.song()` so it works either way.

### Live object model
- `Scene.fire(force_legato, can_select_scene_on_launch)` takes positional
  arguments only. Passing `False` for the second stops Live moving the
  selection.
- `Song.stop_all_clips(quantized=True)` and
  `Track.stop_all_clips(quantized=True)` are quantized by default and keep
  the transport running.
- `ClipSlot.is_recording` and `ClipSlot.is_triggered` let Record slot tell
  "recording" from "waiting to record" without looking at the clip.
- Live wraps objects in new Python proxies, so they're compared with `==`,
  never `is` (`actions.index_of`).
- `song.visible_tracks` already excludes return and master tracks, and
  tracks inside folded groups.

### Stock FCB1010 firmware
- It can't receive anything from the Mac (no LEDs or display), and the
  Up/Down switches send no MIDI.
- For each press it sends PC1 and then the note. Pressing the same preset
  again toggles note-on and note-off. **Not yet confirmed:** whether it
  re-sends the PC on a repeated press (open question 1). The code works
  either way.

### Tooling
- [`ableton-live-stubs`](https://pypi.org/project/ableton-live-stubs/)
  (12.3.6) let pyright check calls to the `Live` module. `ableton.v3` has no
  stubs, so its imports carry `# pyright: ignore[reportMissingImports]`.
- Live embeds Python 3.11. `tomllib` is in the 3.11 standard library, but if
  Live's bundled Python lacks it, `load_settings` logs one error and falls
  back to the defaults.

## Open questions

- [ ] Does the stock firmware re-send the PC on a repeated press? Check with
  a MIDI monitor (see [TODO.md](TODO.md)).
- [ ] Does Live pass Program Change messages to `receive_midi` at all,
  with no forwarding set up?
- [ ] Does Live follow the symlink install.sh creates in Remote Scripts?
- [ ] Does selecting a scene off screen scroll Session View so the box stays
  visible?
- [ ] Is `c_instance.log_message` still the right logging path under v3, or
  should we switch to Python `logging`?

## References

- Initial requirements: [specs/INITIAL_SPEC.md](specs/INITIAL_SPEC.md)
- Decompiled Live 12 MIDI Remote Scripts, the source for the v3 API:
  [gluon/AbletonLive12_MIDIRemoteScripts](https://github.com/gluon/AbletonLive12_MIDIRemoteScripts).
  Files read: `ableton/v3/control_surface/control_surface.py`,
  `control_surface_specification.py`, `components/session_ring.py`,
  `elements_base.py`, `ableton/v2/control_surface/control_surface.py`, and
  `MPK_mini_Plus/` as a minimal v3 script.
- Live API type stubs: [PhotonicVelocity/LiveAPI](https://github.com/PhotonicVelocity/LiveAPI)
  (`ableton-live-stubs` on PyPI)
- [Unofficial MIDI Remote Script docs, LOM 9–12](https://forum.ableton.com/viewtopic.php?p=1837228)
- [Ableton: Creating your own Control Surface script](https://help.ableton.com/hc/en-us/articles/206240184)
- [gaelhuot/FCB1010-Ableton-live](https://github.com/gaelhuot/FCB1010-Ableton-live)
- [FCB1010 spec sheet](https://es.juno.co.uk/downloads/manual/493879-01U.pdf/)
- [FCB1010 message details](https://eventideaudio.com/?p=140248)
