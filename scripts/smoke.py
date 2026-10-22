"""Smoke test against a running Live.

Sends the ten switch presses (PC + note, as the stock FCB1010 does) through
a virtual MIDI port, then checks Live's Log.txt for one ``FCB1010:`` line per
press. Requires ``debug = true`` in config.toml and the port selected as the
FCB1010 control surface's input.

    uv run python scripts/smoke.py --port "IAC Driver Bus 1"
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import mido


def find_log() -> Path:
    logs = sorted(
        Path.home().glob("Library/Preferences/Ableton/Live */Log.txt"),
        key=lambda p: p.stat().st_mtime,
    )
    if not logs:
        sys.exit("Live's Log.txt not found")
    return logs[-1]


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--port", default="IAC Driver Bus 1", help="MIDI output port name")
    parser.add_argument("--channel", type=int, default=16, help="MIDI channel 1-16")
    parser.add_argument("--gap", type=float, default=0.3, help="seconds between presses")
    args = parser.parse_args()

    log = find_log()
    start = log.stat().st_size
    channel = args.channel - 1
    with mido.open_output(args.port) as out:  # pyright: ignore[reportAttributeAccessIssue]
        for switch in range(1, 11):
            out.send(mido.Message("program_change", channel=channel, program=switch - 1))
            out.send(mido.Message("note_on", channel=channel, note=59 + switch, velocity=64))
            time.sleep(args.gap)
    time.sleep(0.5)

    with log.open("rb") as f:
        f.seek(start)
        lines = [
            line for line in f.read().decode(errors="replace").splitlines() if "FCB1010:" in line
        ]
    for line in lines:
        print(line)
    presses = [line for line in lines if "FCB1010: switch " in line]
    errors = [line for line in lines if "FCB1010: error" in line]
    expected = [f"FCB1010: switch {n} " for n in range(1, 11)]
    missing = [e for e in expected if not any(e in line for line in presses)]
    if errors or missing or len(presses) != 10:
        print(f"FAIL: {len(presses)} presses logged, missing {missing}, {len(errors)} errors")
        return 1
    print("OK: 10 presses, no errors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
