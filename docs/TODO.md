# TODO

Record what each check found in [LIVING_SPEC.md](LIVING_SPEC.md).

## 1. Test on a real setup

Nothing has run inside Live yet, so the first run is a shakedown: the most
likely failures are at load time, where the code meets `ableton.v3`.

Before you start:
- **The code isn't on `main` until the stacked PRs are merged.** The default
  `install.sh` clones `main`, so install from the stack's top branch instead
  (step 1.1).
- **Don't install from a temporary worktree.** If it is deleted, the link in
  Remote Scripts breaks. Use your main checkout.
- **The smoke test changes the Set.** Switch 5 arms track 1 and starts
  recording, and switch 10 runs Undo. Use a scratch Set.

### 1.1 Install from the branch
- [ ] In your main checkout of the repo:
  ```bash
  git fetch && git checkout claude/fcb-08-docs && uv sync && make install
  ```
  This links the checkout into
  `~/Music/Ableton/User Library/Remote Scripts/FCB1010` and creates
  `FCB1010/config.toml`.

### 1.2 Smoke test without the pedal (IAC Driver)
- [ ] In Audio MIDI Setup → MIDI Studio, open IAC Driver and tick "Device is
  online".
- [ ] Set `debug = true` in `FCB1010/config.toml`.
- [ ] Restart Live and make a scratch Set with 4 audio tracks and 8 scenes.
- [ ] In Preferences → Link, Tempo & MIDI, set Control Surface = `FCB1010`,
  Input = `IAC Driver Bus 1`, Output = None.
- [ ] In one terminal, follow the log:
  ```bash
  make log
  ```
- [ ] In another terminal, send the ten presses:
  ```bash
  make smoke PORT="IAC Driver Bus 1"
  ```
- [ ] You should see `FCB1010: loaded`, ten `FCB1010: switch N …` lines,
  the highlight box around the selected scene, and
  `OK: 10 presses, no errors`.

### 1.3 If the script fails to load
- [ ] Load errors don't carry the `FCB1010:` prefix, so `make log` won't
  show them. Look in `~/Library/Preferences/Ableton/Live 12.x/Log.txt` for
  a Python traceback around the script's name.
- [ ] The likely causes are:
  - A v3 API difference in Live 12.4. Compare the traceback with
    LIVING_SPEC → Learnings → `ableton.v3`.
  - Live not following the symlink. If so, copy the `FCB1010` folder into
    Remote Scripts instead of linking it.

### 1.4 Program the pedal
- [ ] With an FCB1010 editor (Mountain Utilities, FCB1010 Manager or iFCB),
  program bank 00 as described in [pedal/README.md](../pedal/README.md):
  channel 16, PC 0–9 plus notes 60–69, expression pedals off.
- [ ] Export the dump as `pedal/fcb1010-bank00.syx` and commit it.

### 1.5 Answer the open MIDI questions
- [ ] With a MIDI monitor (e.g. snoize MIDI Monitor), press the same switch
  twice and check whether the Program Change repeats (open question 1). The
  script works either way.
- [ ] With `debug = true`, check whether a press logs exactly one
  `FCB1010: switch` line. That shows whether Live passes PCs to the script
  at all.

### 1.6 Switch to the real pedal
- [ ] Change Live's Input to the USB-MIDI interface.
- [ ] Turn Track and Remote off for that port.
- [ ] Re-select the control surface: set it to None, then back to `FCB1010`.

### 1.7 Acceptance checklist
- [ ] Run the checklist in
  [specs/INITIAL_SPEC.md → Acceptance tests](specs/INITIAL_SPEC.md#acceptance-tests)
  with the pedal, first on the 4-track, 8-scene Set and then on an empty Set.
- [ ] For each item that fails, save the `FCB1010:` lines from `make log`.
- [ ] When everything passes, merge the stacked PRs in order, starting with
  PR #1.

## 2. Release

- [ ] Once the PRs are merged, confirm the default install works:
  `curl … install.sh | bash` on a Mac without the script.
- [ ] Bump the version, update `CHANGELOG.md`, and tag `v0.1.0`.

## 3. Later (not v1)

- [ ] Generate the pedal `.syx` from `config.toml` so the pedal and the
  script can't drift.
- [ ] Use banks 01–09 for more pages, such as transport or devices.
- [ ] Map the expression pedals: master volume, a send, or a device macro.
