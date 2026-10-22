from dataclasses import replace
from typing import cast

import pytest

from FCB1010 import actions
from FCB1010.actions import SongLike, step
from FCB1010.settings import DEFAULTS, Settings

from .fake_live import FakeSong

WRAP = replace(DEFAULTS, navigation="wrap")


def run(name: str, song: FakeSong, settings: Settings = DEFAULTS) -> str:
    return actions.run(name, cast(SongLike, song), settings)


def test_catalogue_matches_settings_actions() -> None:
    from FCB1010.settings import ACTIONS

    assert set(actions.CATALOGUE) == set(ACTIONS)


# --- step() -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("index", "delta", "count", "mode", "expected"),
    [
        (0, 1, 4, "clamp", 1),
        (3, 1, 4, "clamp", None),
        (0, -1, 4, "clamp", None),
        (3, 1, 4, "wrap", 0),
        (0, -1, 4, "wrap", 3),
        (None, 1, 4, "clamp", 0),
        (None, -1, 4, "clamp", 3),
        (None, 1, 0, "clamp", None),
        (0, 1, 1, "wrap", 0),
    ],
)
def test_step(index: int | None, delta: int, count: int, mode: str, expected: int | None) -> None:
    assert step(index, delta, count, mode) == expected


# --- 1/2 Track ← / → ---------------------------------------------------------


def test_track_next_and_prev() -> None:
    song = FakeSong()
    assert run("track_next", song) == "track 2"
    assert song.view.selected_track is song.visible_tracks[1]
    assert run("track_prev", song) == "track 1"
    assert song.view.selected_track is song.visible_tracks[0]


def test_track_clamps_at_ends() -> None:
    song = FakeSong()
    assert run("track_prev", song).startswith("no-op")
    song.select(3, 0)
    assert run("track_next", song).startswith("no-op")
    assert song.view.selected_track is song.visible_tracks[3]
    assert song.changes == []


def test_track_wraps_when_configured() -> None:
    song = FakeSong()
    run("track_prev", song, WRAP)
    assert song.view.selected_track is song.visible_tracks[3]


def test_track_nav_keeps_scene() -> None:
    song = FakeSong()
    song.select(0, 5)
    run("track_next", song)
    assert song.view.selected_scene is song.scenes[5]


def test_track_nav_from_return_track_enters_regular_tracks() -> None:
    song = FakeSong()
    song.view._track = song.return_track
    run("track_next", song)
    assert song.view.selected_track is song.visible_tracks[0]
    song.view._track = song.return_track
    run("track_prev", song)
    assert song.view.selected_track is song.visible_tracks[3]


# --- 6/7 Scene ↑ / ↓ ---------------------------------------------------------


def test_scene_down_three_then_up_three_returns_to_start() -> None:
    song = FakeSong()
    song.select(0, 2)
    for _ in range(3):
        run("scene_next", song)
    assert song.view.selected_scene is song.scenes[5]
    for _ in range(3):
        run("scene_prev", song)
    assert song.view.selected_scene is song.scenes[2]
    assert song.changes == ["selected_scene"] * 6


def test_scene_clamps_at_ends() -> None:
    song = FakeSong()
    assert run("scene_prev", song).startswith("no-op")
    song.select(0, 7)
    assert run("scene_next", song).startswith("no-op")
    assert song.changes == []


def test_scene_wraps_when_configured() -> None:
    song = FakeSong()
    song.select(0, 7)
    run("scene_next", song, WRAP)
    assert song.view.selected_scene is song.scenes[0]


def test_scene_nav_keeps_track() -> None:
    song = FakeSong()
    song.select(2, 0)
    run("scene_next", song)
    assert song.view.selected_track is song.visible_tracks[2]


# --- 3 Launch clip -------------------------------------------------------------


def test_clip_launch_fires_slot_with_clip() -> None:
    song = FakeSong()
    song.select(1, 3)
    song.slot(1, 3).has_clip = True
    assert run("clip_launch", song) == "fired clip"
    assert song.slot(1, 3).fired == 1


def test_clip_launch_retriggers_playing_clip() -> None:
    song = FakeSong()
    song.slot(0, 0).has_clip = True
    song.visible_tracks[0].playing_slot_index = 0
    run("clip_launch", song)
    run("clip_launch", song)
    assert song.slot(0, 0).fired == 2


def test_clip_launch_on_empty_slot_does_nothing() -> None:
    song = FakeSong()
    song.visible_tracks[0].playing_slot_index = 2
    assert run("clip_launch", song).startswith("no-op")
    assert song.slot(0, 0).fired == 0
    assert song.visible_tracks[0].stopped == []


# --- 4 Stop clip ---------------------------------------------------------------


def test_clip_stop_stops_focused_track_quantized() -> None:
    song = FakeSong()
    song.select(2, 0)
    song.visible_tracks[2].playing_slot_index = 4
    song.visible_tracks[3].playing_slot_index = 1
    assert run("clip_stop", song) == "stopped track"
    assert song.visible_tracks[2].stopped == [True]
    assert song.visible_tracks[3].stopped == []


def test_clip_stop_with_nothing_playing_does_nothing() -> None:
    song = FakeSong()
    assert run("clip_stop", song).startswith("no-op")
    assert song.visible_tracks[0].stopped == []


# --- 5 Record slot -------------------------------------------------------------


def test_slot_record_arms_and_fires_empty_slot() -> None:
    song = FakeSong()
    assert run("slot_record", song) == "started recording"
    assert song.visible_tracks[0].arm is True
    assert song.slot(0, 0).fired == 1


def test_slot_record_on_armed_track_fires() -> None:
    song = FakeSong()
    song.visible_tracks[0].arm = True
    run("slot_record", song)
    assert song.slot(0, 0).fired == 1


def test_slot_record_again_ends_recording() -> None:
    song = FakeSong()
    slot = song.slot(0, 0)
    slot.has_clip = True
    slot.is_recording = True
    assert run("slot_record", song) == "ended recording"
    assert slot.fired == 1


def test_slot_record_never_overwrites_clip() -> None:
    song = FakeSong()
    song.slot(0, 0).has_clip = True
    assert run("slot_record", song).startswith("no-op")
    assert song.slot(0, 0).fired == 0
    assert song.visible_tracks[0].arm is False


def test_slot_record_while_triggered_does_nothing() -> None:
    song = FakeSong()
    song.slot(0, 0).is_triggered = True
    assert run("slot_record", song).startswith("no-op")
    assert song.slot(0, 0).fired == 0


@pytest.mark.parametrize(
    "setup",
    [
        lambda t: setattr(t, "can_be_armed", False),  # group track
        lambda t: setattr(t, "has_audio_input", False),  # no input
    ],
)
def test_slot_record_on_unarmable_track_does_nothing(setup) -> None:
    song = FakeSong()
    setup(song.visible_tracks[0])
    assert run("slot_record", song).startswith("no-op")
    assert song.slot(0, 0).fired == 0
    assert song.visible_tracks[0].arm is False


def test_slot_record_on_midi_track() -> None:
    song = FakeSong()
    track = song.visible_tracks[0]
    track.has_audio_input, track.has_midi_input = False, True
    assert run("slot_record", song) == "started recording"


def test_slot_record_on_return_track_does_nothing() -> None:
    song = FakeSong()
    song.view._track = song.return_track
    assert run("slot_record", song).startswith("no-op")


# --- 8 Launch scene ------------------------------------------------------------


def test_scene_launch_fires_without_moving_focus() -> None:
    song = FakeSong()
    song.select(0, 4)
    assert run("scene_launch", song) == "fired scene 5"
    assert song.scenes[4].fired == [(False, False)]
    assert song.view.selected_scene is song.scenes[4]


def test_scene_launch_can_advance_focus() -> None:
    song = FakeSong()
    song.select(0, 4)
    run("scene_launch", song, replace(DEFAULTS, scene_launch_advances=True))
    assert song.scenes[4].fired == [(False, False)]
    assert song.view.selected_scene is song.scenes[5]


def test_scene_launch_advance_clamps_at_last_scene() -> None:
    song = FakeSong()
    song.select(0, 7)
    run("scene_launch", song, replace(DEFAULTS, scene_launch_advances=True))
    assert song.view.selected_scene is song.scenes[7]


# --- 9 Stop all / 10 Undo ------------------------------------------------------


def test_stop_all_is_quantized() -> None:
    song = FakeSong()
    assert run("stop_all", song) == "stopped all clips"
    assert song.stopped_all == [True]


def test_undo() -> None:
    song = FakeSong()
    run("undo", song)
    assert song.undone == 1


def test_undo_with_nothing_to_undo() -> None:
    song = FakeSong()
    song.can_undo = False
    assert run("undo", song).startswith("no-op")
    assert song.undone == 0


def test_none_action() -> None:
    assert run("none", FakeSong()).startswith("no-op")


# --- Empty Set -----------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(actions.CATALOGUE))
def test_every_action_is_safe_in_empty_set(name: str) -> None:
    song = FakeSong(tracks=0, scenes=0)
    song.can_undo = False
    result = run(name, song)
    assert result.startswith("no-op") or name == "stop_all"
    assert song.changes == []


@pytest.mark.parametrize("name", sorted(actions.CATALOGUE))
def test_every_action_is_safe_with_scenes_but_no_tracks(name: str) -> None:
    song = FakeSong(tracks=0, scenes=3)
    song.can_undo = False
    run(name, song)
