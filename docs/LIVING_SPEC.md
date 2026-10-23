# Living spec

This document describes what the code does now. The original requirements
stay unchanged in [specs/INITIAL_SPEC.md](specs/INITIAL_SPEC.md); this file
records where the implementation settled, why, and what we've learned along
the way. Update it whenever behaviour, a decision or a finding changes.

Last updated: 2026-10-23 (v0.1.0, IAC smoke test passing on Live 12.4.3).

## Status

| Area | State |
| --- | --- |
| Decision logic (settings, MIDI, actions, box geometry, glue) | Done; 150 unit tests |
| Live adapter (`ableton.v3`) | Loads and handles presses in Live 12.4.3: IAC smoke test passes (10 presses, no errors). The first run, on 12.4.2, logged 0 presses (MIDI hook on the wrong method); fixed |
| install.sh / dev tasks / smoke test | Done; `make install` used against a real Live, which follows the symlink |
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

A press flows: Live → `FCB1010.process_midi_bytes` → `Controller.on_midi` →
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
  forward the ten notes. **Confirmed in Live 12.4.2:** the smoke test sent a
  PC and a note per press, and only the notes reached the script, so Live
  doesn't pass PCs on unasked either. The note path is the one that
  matters, and it turns every press into an event, because the firmware
  toggles note-on and note-off. PC handling stays in `PressDecoder`; it
  costs nothing and covers a Live that does pass them.
- The `midi_channel` argument to `forward_midi_note` is 0-based (channel 16
  is 15).
- **Live 12 calls `receive_midi_chunk`, not `receive_midi`.** Both go
  through `SimpleControlSurface.process_midi_bytes(midi_bytes,
  midi_processor)` in `ableton.v2` (v3 doesn't override it). That method
  sends messages to the control elements and logs anything it doesn't
  recognise as "Got unknown message". The script has no elements, so it
  overrides `process_midi_bytes`. Its callers already hold the component
  guard. An earlier `receive_midi` override was never called (found in the
  first IAC smoke test on Live 12.4.2).
- The warning is the sign of that failure: Log.txt shows
  `info: Python: WARNING:ableton.v2.control_surface.control_surface:… -
  Got unknown message: 0x9f 0x3c 0x40` (note-on, channel 16, note 60)
  for each press.
- `c_instance.log_message` works under v3: the script's lines appear in
  Log.txt as `info: RemoteScriptMessage: FCB1010: …`.

### Reading Live's own scripts
- Live's MIDI Remote Scripts, including `ableton.v2` and `ableton.v3`, ship
  as Python 3.11 bytecode in
  `/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/MIDI Remote Scripts/`.
  When the decompiled sources (see References) are unclear or out of date,
  this reads the installed version directly: skip the 16-byte header,
  `marshal.load` the rest and run `dis` on the code object, under Python
  3.11 (`uv run --no-project --python 3.11`). This is how the
  `process_midi_bytes` path was found.
- `strings` on a `.pyc` is a quicker first look: it lists the method names
  and log messages.

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

### Live setup on macOS
- **Each point release gets its own preferences folder**
  (`~/Library/Preferences/Ableton/Live 12.4`, `Live 12.4.1`, `Live 12.4.2`,
  …), and Log.txt moves with it. Live auto-updated from 12.4 through 12.4.2
  to 12.4.3 during the first test session, installing on restart. `make log` and `smoke.py` always pick the
  most recently written Log.txt, so they follow along. Look in the newest
  folder when reading the log by hand.
- **Live follows the symlink** that install.sh puts in Remote Scripts.
  Copying the folder isn't needed.
- On a fresh setup, `~/Music/Ableton/User Library/Remote Scripts` didn't
  exist. Creating it (install.sh does) was enough for Live to find the
  script after a restart. If the User Library has been moved in Live's
  settings, the link has to go there instead.
- **One port, two names.** CoreMIDI and `mido` call the IAC port
  `IAC Driver Bus 1` (what `make smoke` needs); Live's settings and Log.txt
  call it `IAC Driver (Bus 1)`.
- Live turned **Track** on for the new IAC input by default. That doesn't
  affect the smoke test, but for the pedal's port, Track and Remote must be
  off (TODO 1.6).
- **Code changes need a Live restart; `config.toml` changes don't.**
  Setting Control Surface to None and back re-runs `create_instance` and
  re-reads `config.toml`, but Python keeps the already-imported `FCB1010`
  modules, so edited code (or a re-pointed symlink) isn't loaded. Seen in
  the first session: after relinking to a worktree and re-selecting, the
  old code still ran and the worktree never got a `__pycache__`.

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
- [x] Does Live pass Program Change messages to the script at all, with no
  forwarding set up? **No** (Live 12.4.2, see Learnings → Live's MIDI API).
- [x] Does Live follow the symlink install.sh creates in Remote Scripts?
  **Yes.**
- [ ] Does selecting a scene off screen scroll Session View so the box stays
  visible?
- [x] Is `c_instance.log_message` still the right logging path under v3?
  **Yes;** lines show up as `RemoteScriptMessage: FCB1010: …`.
- [x] Does the `process_midi_bytes` fix make the IAC smoke test pass?
  **Yes,** on Live 12.4.3 after a restart.
- [ ] Why did Undo after the smoke test's record and scene launch report
  "nothing to undo" (`song.can_undo` false)? It may be that recording and
  launching aren't undo steps in Live. Check by hand during acceptance.

## References

- Initial requirements: [specs/INITIAL_SPEC.md](specs/INITIAL_SPEC.md)
- Decompiled Live 12 MIDI Remote Scripts, the source for the v3 API:
  [gluon/AbletonLive12_MIDIRemoteScripts](https://github.com/gluon/AbletonLive12_MIDIRemoteScripts).
  Files read: `ableton/v3/control_surface/control_surface.py`,
  `control_surface_specification.py`, `components/session_ring.py`,
  `elements_base.py`, `ableton/v2/control_surface/control_surface.py`, and
  `MPK_mini_Plus/` as a minimal v3 script.
- The installed bytecode of those scripts, inside the Live app bundle (see
  Learnings → Reading Live's own scripts). It is the final word for the
  installed Live version.
- Live API type stubs: [PhotonicVelocity/LiveAPI](https://github.com/PhotonicVelocity/LiveAPI)
  (`ableton-live-stubs` on PyPI)
- [Unofficial MIDI Remote Script docs, LOM 9–12](https://forum.ableton.com/viewtopic.php?p=1837228)
- [Ableton: Creating your own Control Surface script](https://help.ableton.com/hc/en-us/articles/206240184)
- [gaelhuot/FCB1010-Ableton-live](https://github.com/gaelhuot/FCB1010-Ableton-live)
- [FCB1010 spec sheet](https://es.juno.co.uk/downloads/manual/493879-01U.pdf/)
- [FCB1010 message details](https://eventideaudio.com/?p=140248)
