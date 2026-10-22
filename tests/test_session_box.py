from typing import cast

import pytest

from FCB1010.actions import SongLike
from FCB1010.session_box import HIDDEN, Box, box_for_song, compute_box

from .fake_live import FakeScene, FakeSong, FakeTrack


def box(song: FakeSong, width: str = "row") -> Box:
    return box_for_song(cast(SongLike, song), width)


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        ((0, 0, 4, "row"), Box(0, 0, 4, 1)),
        ((2, 5, 4, "row"), Box(0, 5, 4, 1)),
        ((2, 5, 4, "slot"), Box(2, 5, 1, 1)),
        ((None, 5, 4, "slot"), Box(0, 5, 4, 1)),
        ((None, 5, 4, "row"), Box(0, 5, 4, 1)),
        ((0, None, 4, "row"), HIDDEN),
        ((None, 0, 0, "row"), HIDDEN),
    ],
)
def test_compute_box(args: tuple, expected: Box) -> None:
    assert compute_box(*args) == expected


def test_box_follows_selection() -> None:
    song = FakeSong()
    assert box(song) == Box(0, 0, 4, 1)
    song.select(3, 6)
    assert box(song) == Box(0, 6, 4, 1)
    assert box(song, "slot") == Box(3, 6, 1, 1)


def test_box_recomputed_when_tracks_added() -> None:
    song = FakeSong()
    song.visible_tracks.append(FakeTrack("T5"))
    assert box(song) == Box(0, 0, 5, 1)


def test_box_recomputed_when_scene_inserted_above() -> None:
    song = FakeSong()
    song.select(0, 3)
    song.scenes.insert(0, FakeScene("new"))
    assert box(song) == Box(0, 4, 4, 1)


def test_box_recomputed_when_tracks_reordered() -> None:
    song = FakeSong()
    song.select(0, 0)
    song.visible_tracks.reverse()
    assert box(song, "slot") == Box(3, 0, 1, 1)


def test_box_follows_new_selection_after_scene_deleted() -> None:
    song = FakeSong()
    song.select(0, 3)
    del song.scenes[3]
    song.view.selected_scene = song.scenes[2]  # Live picks a new selection
    assert box(song) == Box(0, 2, 4, 1)


def test_empty_set_hides_box() -> None:
    assert box(FakeSong(tracks=0, scenes=0)) == HIDDEN
    assert box(FakeSong(tracks=0, scenes=2)) == HIDDEN
