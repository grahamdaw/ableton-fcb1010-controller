# FCB1010 → Ableton Live Session Controller — Requirements

Oct 22, 2026 · @Graham

## Goal and scope

The FCB1010 drives Live's Session View hands-free: move the focused scene and track, launch or stop the focused clip or scene, record into the focused slot, undo — and show the focus as a highlight box in Live, the way Push and Launchpad do.

**In scope (v1)**

- Bank 00 of the FCB1010: 10 switches, one job each (layout below)
- Focus navigation, clip/scene launch and stop, record into slot, undo
- Session-highlight box around the focused scene, kept in sync with Live's own selection
- Works in any Set with no per-Set setup

**Out of scope (v1)**

- LED or display feedback on the pedal (the stock chip cannot receive it)
- Banks 01–09 (reserved for later pages such as transport or devices)
- Expression pedals (disabled; nothing sent)
- Device, mixer and Arrangement View control; transport beyond stop-all

## Environment and constraints

A Python MIDI Remote Script running inside Live, fed by a stock FCB1010 over a USB-MIDI interface. No external process.

- **Live:** Ableton Live 12 Suite, 12.4.x, macOS. The script runs in Live's embedded Python 3.11; no pip packages, Live's API only.
- **Pedal:** Behringer FCB1010 with the stock Behringer firmware (2.5.x). Consequences: no LED or display control from the Mac; the Up/Down switches only change banks and send no MIDI; a switch sends its preset's PC/note on press and toggles note-on/note-off on repeated presses.
- **Connection:** FCB1010 MIDI Out → class-compliant USB-MIDI interface → Mac. MIDI In on the pedal is only needed to load the preset file from an editor.
- **Script form:** a Control Surface class in its own folder under `~/Music/Ableton/User Library/Remote Scripts/`, selected in Preferences → Link, Tempo & MIDI. Framework (`_Framework` or `ableton.v3`) is an open decision below.
- **No per-Set configuration:** the script works in any Set, including an empty one.

## Switch layout and behaviour

All ten switches of bank 00 are used; each is a single press with one job. *Focus* means Live's selected scene × selected track; the *focused slot* is the clip slot where they meet.

| Row | Left |  | Middle |  | Right |
| --- | --- | --- | --- | --- | --- |
| Top (6–10) | 6 Scene ↑ | 7 Scene ↓ | 8 Launch scene | 9 Stop all clips | 10 Undo |
| Bottom (1–5) | 1 Track ← | 2 Track → | 3 Launch clip | 4 Stop clip | 5 Record slot |

| Switch | Function | Live behaviour | Edge cases |
| --- | --- | --- | --- |
| 1 | Track ← | Select the previous regular track (not returns or master) | At the first track: nothing (no wrap) |
| 2 | Track → | Select the next regular track | At the last track: nothing |
| 3 | Launch clip | Fire the focused slot; obeys global launch quantization; a playing clip re-triggers from its start | Empty slot: nothing (does not stop the track) |
| 4 | Stop clip | Quantized stop of whatever plays on the focused track | Nothing playing: nothing |
| 5 | Record slot | Focused slot empty → arm the focused track if needed, then fire it, so Session recording starts. Slot recording → fire again: recording ends and the clip plays | Slot already holds a clip: nothing (never overwrites). Track cannot be armed (group, return, no input): nothing |
| 6 | Scene ↑ | Select the previous scene | At the first scene: nothing |
| 7 | Scene ↓ | Select the next scene | At the last scene: nothing |
| 8 | Launch scene | Fire the selected scene; focus stays on it | Empty scene: Live's default (stops the tracks that have stop buttons in that row) |
| 9 | Stop all clips | Quantized stop of every clip; the transport keeps running | — |
| 10 | Undo | Live's Undo | Nothing to undo: nothing |

Repeated presses of the same switch (e.g. Scene ↓ five times) must each count — see MIDI handling.

## Session focus box

A highlight box frames the focused scene in Session View whenever the script is active, like the ring Push, APC and Launchpad draw.

- **Mechanism:** Live's own control-surface session highlight (the "ring"), set by the script — not a drawn overlay. Live draws it and picks the colour by control-surface slot; whatever colour Live assigns is fine.
- **Size:** one scene high, the full width of the Session grid (every regular track). The focused slot inside the row is shown by Live's normal track selection. A 1×1 box around the focused slot only is a config option.
- **One source of truth:** Live's selected scene and selected track. The switches change the selection; the box follows the selection through listeners. So a mouse click, arrow keys or another controller move the box too, and the switches continue from wherever the box is.
- **Visibility:** Session View scrolls so the box stays on screen when navigation leaves the visible rows.
- **Structure changes:** when scenes or tracks are added, removed or reordered the box is recomputed; if the focused scene is deleted, Live's new selection wins and the box follows it.
- **Lifecycle:** the box appears when Live loads the script and disappears when the script is disabled or Live quits.

## FCB1010 programming (bank 00)

Every preset sends one Program Change and one note on a dedicated MIDI channel; nothing else. The script treats the PC as the press event and the note as backup for repeated presses.

**Global settings**

- MIDI channel for PC1 and NOTE: 16 (keeps the pedal off instrument channels)
- PC2–PC5, CC1, CC2: disabled in all presets
- EXP A and EXP B: disabled in all presets, so the pedals send nothing and cannot spam jittery CCs
- Relay switches 1/2: off
- Direct Select: off; the pedal stays in bank 00

| Switch | Function | PC (pedal display / MIDI value) | Note |
| --- | --- | --- | --- |
| 1 | Track ← | 1 / 0 | 60 (C3) |
| 2 | Track → | 2 / 1 | 61 |
| 3 | Launch clip | 3 / 2 | 62 |
| 4 | Stop clip | 4 / 3 | 63 |
| 5 | Record slot | 5 / 4 | 64 |
| 6 | Scene ↑ | 6 / 5 | 65 |
| 7 | Scene ↓ | 7 / 6 | 66 |
| 8 | Launch scene | 8 / 7 | 67 |
| 9 | Stop all clips | 9 / 8 | 68 |
| 10 | Undo | 10 / 9 | 69 (A3) |

Note velocity is fixed by the firmware at 64. Program the pedal from an editor (Mountain Utilities FCB1010, FCB1010 Manager or iFCB) over SysEx; the resulting `.syx` file is part of the deliverable so the pedal can be restored in one dump.

## MIDI handling

The script owns the pedal's MIDI port and turns each press into exactly one event, whatever the stock firmware sends.

**Live setup**

- Preferences → Link, Tempo & MIDI: Control Surface = the script; Input = the USB-MIDI interface port; Output = None
- The same port's Track and Remote switches: off, so the pedal's notes never reach instruments and Live's MIDI Map never grabs them (control-surface input is independent of those switches)

**Press detection**

- Only channel 16 is read; other channels, CCs and SysEx on the port are ignored
- Primary event: Program Change n → switch n+1 pressed
- Backup event: note 60–69 on *or* off → the same switch; both directions count, because the firmware alternates note-on/note-off on repeated presses
- De-duplication: a PC and a note for the same switch within 50 ms are one press (the firmware sends PC first, then the note)
- Repeated presses of the active preset must still fire. If the firmware re-sends the PC, that suffices; if it only toggles the note, the note path covers it. Which one applies is the first open question
- The script sends nothing to the pedal

## Non-functional requirements

- **Latency:** press → Live action issued within 10 ms; launch quantization adds whatever the Set's global quantization says
- **Never crashes Live:** every handler is guarded; an error is logged with a `FCB1010:` prefix to Live's `Log.txt` and the press is dropped
- **Robust to Set changes:** works in a new or empty Set (no tracks or scenes → every switch is a no-op), survives adding, removing and reordering tracks and scenes, and reloading a Set
- **Install:** source lives in a GitHub repo. An install.sh script clones the repo (or pulls when it is already there) and links the script folder into the User Library's Remote Scripts; running it again updates. Then restart Live and pick the control surface once. No dependencies beyond Live's Python and git
- **Configuration:** one `config.toml` holds everything that may change; see Configuration below. Nothing per Set
- **Logging:** debug logging switchable in `config.toml`, off by default
- **Compatibility:** Live 12.4.x on macOS is the target; Live 12.x in general is expected to work
- **Deliverables:** the script folder, the FCB1010 `.syx` preset file, the install.sh install/update script, and a README with the setup steps

## Configuration

All settings live in one `config.toml` beside the script. Edit it and re-select the control surface in Preferences to apply — no Live restart, no code change.

| Setting | Default | Notes |
| --- | --- | --- |
| MIDI channel | 16 | Must match the pedal's global channel |
| Switch map | the layout above | Each of the 10 switches names an action from a fixed catalogue: `track_prev`, `track_next`, `clip_launch`, `clip_stop`, `slot_record`, `scene_prev`, `scene_next`, `scene_launch`, `stop_all`, `undo`, `none`. Rearranging the pedal is editing ten lines |
| PC and note per switch | 0–9 and 60–69 | Must match the pedal's presets |
| De-duplication window | 50 ms | PC + note of one press |
| Navigation at the ends | clamp | or `wrap` |
| Box width | row | or `slot` (1×1) |
| Launch scene advances focus | false |  |
| Debug logging | false |  |

- Defaults are built into the code; a missing file or key falls back to them
- The file is validated at load. An unknown action, a duplicate PC or note, or an out-of-range value logs one error line naming the key, and that key's default is used; the script still loads
- A commented example `config.toml` ships in the repo and the README explains each key in a line
- Bank pages later: the map can gain a per-bank table without changing the code structure

## Testing

All decision logic is tested outside Live with pytest; Live itself is only touched by a short smoke test and the acceptance checklist.

- **Testable structure:** everything that decides what to do — MIDI parsing and de-duplication, switch → action mapping, navigation and clamp rules, record-slot rules, box geometry, config loading — is plain Python that never imports `Live`. Live is reached through one thin adapter module, the only place that imports `Live`; tests swap in a fake Song with tracks, scenes and slots
- **Unit tests:** `pytest` under `tests/`, run locally on Python 3.11 (`uv run pytest`) and in CI. They cover every row of the switch table including its edge cases, repeated presses and PC/note de-duplication, clamping at the ends, box recomputation when tracks or scenes change, and config defaults and validation errors
- **Smoke test in Live:** a `smoke` task sends the ten presses as PC + note through a virtual MIDI port (macOS IAC Driver) with `mido`, then checks Log.txt for the expected `FCB1010:` lines. Run after install and before a release
- **Dev loop:** edit in the repo (linked into Remote Scripts), re-select the control surface to reload, and a `log` task tails Log.txt. Written up in the README
- **Acceptance checklist** below is run by hand with the pedal before each release

## Code standards

- **Python 3.11 only**, the version Live embeds; no third-party imports inside the script folder. Dev tools live in the repo's `uv` environment
- **Typed:** type hints on every function; `pyright` in basic mode with the community Live stubs, so Live API calls are checked
- **Lint and format:** `ruff` with zero warnings; `pre-commit` runs ruff and pyright on every commit
- **CI:** GitHub Actions runs ruff, pyright and pytest on every push and pull request; `main` stays green
- **Structure:** `__init__.py` holds only `create_instance`; `live_adapter.py` is the only module that imports `Live`; `midi.py`, `actions.py`, `session_box.py` and `settings.py` hold the logic; `config.toml` beside them
- **Errors:** no bare `except`; every entry point called by Live is guarded and logs with the `FCB1010:` prefix
- **Docs:** a docstring on each public function; README covers install, dev loop, config keys and release steps; a CHANGELOG with a version bumped per release

## Acceptance tests

v1 is done when every item passes on a Set with 4 audio tracks and 8 scenes, plus an empty Set.

- [ ] Script appears in the Control Surface list and loads with no errors in Log.txt
- [ ] Highlight box frames the selected scene right after loading, in a new Set and in an existing Set
- [ ] Scene ↓ ×3 then Scene ↑ ×3 ends on the starting scene; the box moves on every press; no wrap at the first or last scene
- [ ] Track ← / → move Live's track selection; the box stays on the same scene
- [ ] Clicking a slot with the mouse moves the box to that slot's scene
- [ ] Launch clip on a slot with a clip starts it on the next quantize point; on an empty slot nothing happens
- [ ] Stop clip stops only the focused track's clip; other tracks keep playing
- [ ] Launch scene starts every clip in the row; focus stays on that scene
- [ ] Stop all clips stops every clip; the transport keeps running
- [ ] Record slot on an empty slot of an audio track arms it and records; pressing again ends the recording and the clip plays; on a slot with a clip nothing happens
- [ ] Undo reverts the last action (e.g. a deleted clip comes back)
- [ ] Pressing the same switch 10 times quickly yields exactly 10 events (no doubles from PC+note, no drops)
- [ ] Deleting the focused scene or track breaks nothing; the box follows Live's new selection
- [ ] Expression pedals send nothing (checked with a MIDI monitor)
- [ ] An armed instrument track never receives the pedal's notes
- [ ] Empty Set: every switch is a no-op and nothing is logged as an error

* [ ] install.sh on a Mac without the script installs it; after a change in the repo, running it again updates the installed script in place

- [ ] `uv run pytest` passes locally and CI is green on `main`
- [ ] Swapping two switches in `config.toml` and re-selecting the control surface swaps their jobs without restarting Live
- [ ] An unknown action name in `config.toml` logs one clear error line and the script still loads with that key's default

## Open questions

Defaults are stated; each stands unless you change it.

- [ ] **PC re-send:** does the stock firmware re-send the Program Change when the active preset's switch is pressed again? A five-minute MIDI-monitor check; decides whether the note path is backup or essential
- [ ] **Framework:** `ableton.v3` (current, used by Push 3, has a ready session-ring component for the box) or `_Framework` (older, more community examples, including existing FCB1010 scripts). Default: v3
- [ ] **Box width:** whole scene row (default) or a 1×1 box around the focused slot
- [ ] **Navigation at the ends:** clamp (default) or wrap
- [ ] **Launch scene:** focus stays (default) or advances to the next scene, as Live's "Select Next Scene on Launch" does
- [ ] **Folded groups and hidden tracks:** Track ← / → step through visible tracks only (default) or all tracks
- [ ] **USB-MIDI interface:** which one is on hand; any class-compliant 1-in/1-out works
- [ ] **Expression pedals later:** candidates are master volume, a send, or a device macro — out of v1

* [ ] **Generate the pedal preset:** build the FCB `.syx` file from `config.toml` so the pedal and the script can never drift. Nice to have, not v1

**Sources used for the research**

- [Unofficial MIDI Remote Script docs, LOM 9–12](https://forum.ableton.com/viewtopic.php?p=1837228)
- [Ableton: Creating your own Control Surface script](https://help.ableton.com/hc/en-us/articles/206240184)
- [gaelhuot/FCB1010-Ableton-live](https://github.com/gaelhuot/FCB1010-Ableton-live)
- [FCB1010 spec sheet](https://es.juno.co.uk/downloads/manual/493879-01U.pdf/)
- [FCB1010 message details](https://eventideaudio.com/?p=140248)
