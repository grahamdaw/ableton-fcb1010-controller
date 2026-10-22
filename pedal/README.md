# Programming the FCB1010 (bank 00)

The script expects these presets. Program them from an editor over SysEx
(Mountain Utilities FCB1010, FCB1010 Manager or iFCB), then save the
editor's dump here as `pedal/fcb1010-bank00.syx` so the pedal can be
restored in one send.

> The `.syx` file is not in the repo yet: it has to be exported from an
> editor connected to the pedal.

**Global settings, every preset in bank 00**

- PC1 and NOTE: enabled, MIDI channel 16
- PC2–PC5, CC1, CC2: disabled
- EXP A and EXP B: disabled
- Relay switches 1/2: off
- Direct Select: off

| Switch | Function | PC (display / MIDI value) | Note |
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

If you change a PC or note here, change the matching `pc`/`note` in
`FCB1010/config.toml` too.
