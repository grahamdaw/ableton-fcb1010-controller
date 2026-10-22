from dataclasses import replace

import pytest

from FCB1010.midi import PressDecoder
from FCB1010.settings import DEFAULTS

CH16 = 0x0F


def pc(n: int, ch: int = CH16) -> tuple[int, ...]:
    return (0xC0 | ch, n)


def note_on(n: int, ch: int = CH16) -> tuple[int, ...]:
    return (0x90 | ch, n, 64)


def note_off(n: int, ch: int = CH16) -> tuple[int, ...]:
    return (0x80 | ch, n, 64)


@pytest.fixture
def decoder() -> PressDecoder:
    return PressDecoder(DEFAULTS)


@pytest.mark.parametrize("switch", range(1, 11))
def test_pc_maps_to_switch(decoder: PressDecoder, switch: int) -> None:
    assert decoder.feed(pc(switch - 1), 0) == switch


@pytest.mark.parametrize("switch", range(1, 11))
def test_note_on_and_off_map_to_switch(decoder: PressDecoder, switch: int) -> None:
    assert decoder.feed(note_on(59 + switch), 0) == switch
    assert decoder.feed(note_off(59 + switch), 1000) == switch


def test_note_on_with_zero_velocity_counts(decoder: PressDecoder) -> None:
    assert decoder.feed((0x9F, 60, 0), 0) == 1


def test_pc_then_note_is_one_press(decoder: PressDecoder) -> None:
    assert decoder.feed(pc(6), 0) == 7
    assert decoder.feed(note_on(66), 2) is None


def test_note_then_pc_is_one_press(decoder: PressDecoder) -> None:
    assert decoder.feed(note_on(66), 0) == 7
    assert decoder.feed(pc(6), 2) is None


def test_pc_and_note_outside_window_are_two_presses(decoder: PressDecoder) -> None:
    assert decoder.feed(pc(6), 0) == 7
    assert decoder.feed(note_on(66), 51) == 7


def test_repeated_presses_with_pc_and_note_each_count(decoder: PressDecoder) -> None:
    events = []
    for i in range(10):
        t = i * 120
        events.append(decoder.feed(pc(6), t))
        events.append(decoder.feed(note_on(66) if i % 2 == 0 else note_off(66), t + 1))
    assert [e for e in events if e is not None] == [7] * 10


def test_repeated_presses_with_only_note_toggle_each_count(decoder: PressDecoder) -> None:
    # Firmware that does not re-send the PC for the active preset.
    events = [decoder.feed(pc(6), 0), decoder.feed(note_on(66), 1)]
    for i in range(1, 10):
        events.append(decoder.feed(note_off(66) if i % 2 else note_on(66), i * 120))
    assert [e for e in events if e is not None] == [7] * 10


def test_fast_repeats_of_same_kind_are_never_merged(decoder: PressDecoder) -> None:
    assert decoder.feed(note_on(60), 0) == 1
    assert decoder.feed(note_off(60), 10) == 1


def test_one_pair_only_swallows_one_message(decoder: PressDecoder) -> None:
    assert decoder.feed(pc(0), 0) == 1
    assert decoder.feed(note_on(60), 1) is None
    assert decoder.feed(pc(0), 20) == 1


def test_different_switches_are_not_merged(decoder: PressDecoder) -> None:
    assert decoder.feed(pc(0), 0) == 1
    assert decoder.feed(note_on(61), 1) == 2


@pytest.mark.parametrize(
    "msg",
    [
        pc(0, ch=0),
        note_on(60, ch=3),
        (0xBF, 7, 100),  # CC on channel 16
        (0xF0, 0x7E, 0x7F, 0xF7),  # SysEx
        (0xF8,),  # clock
        pc(42),  # unmapped PC
        note_on(70),  # unmapped note
        (0xEF, 0, 64),  # pitch bend
        (),
        (0xCF,),  # truncated PC
    ],
)
def test_ignored_messages(decoder: PressDecoder, msg: tuple[int, ...]) -> None:
    assert decoder.feed(msg, 0) is None


def test_ignored_message_does_not_break_pairing(decoder: PressDecoder) -> None:
    assert decoder.feed(pc(0), 0) == 1
    assert decoder.feed((0xBF, 7, 100), 1) is None
    assert decoder.feed(note_on(60), 2) is None


def test_custom_channel_and_map() -> None:
    switches = dict(DEFAULTS.switches)
    switches[1] = replace(switches[1], pc=100, note=10)
    decoder = PressDecoder(replace(DEFAULTS, midi_channel=1, switches=switches))
    assert decoder.feed((0xC0, 100), 0) == 1
    assert decoder.feed((0x90, 10, 64), 500) == 1
    assert decoder.feed(pc(0), 1000) is None
    assert decoder.notes == [10, *range(61, 70)]
