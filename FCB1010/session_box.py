"""Geometry of the session highlight box ("ring") Live draws for the script.

The box always follows Live's own selection: it is recomputed from the
selected track and scene whenever either, or the track/scene lists, change.
"""

from __future__ import annotations

from dataclasses import dataclass

from .actions import SongLike, focused_scene_index, index_of


@dataclass(frozen=True)
class Box:
    """A highlight rectangle in Session View, in visible-track/scene coordinates."""

    track_offset: int
    scene_offset: int
    width: int
    height: int


HIDDEN = Box(-1, -1, -1, -1)
"""The value Live's ``set_session_highlight`` takes to remove the box."""


def compute_box(
    track_index: int | None, scene_index: int | None, num_tracks: int, box_width: str
) -> Box:
    """Box for the given focus.

    ``box_width`` "row" spans every regular track of the focused scene;
    "slot" frames only the focused slot. With no scenes, or no tracks, the box
    is hidden. In "slot" mode a non-regular selected track (return/master)
    falls back to the whole row so the box never disappears mid-navigation.
    """
    if scene_index is None or num_tracks == 0:
        return HIDDEN
    if box_width == "slot" and track_index is not None:
        return Box(track_index, scene_index, 1, 1)
    return Box(0, scene_index, num_tracks, 1)


def box_for_song(song: SongLike, box_width: str) -> Box:
    """Box for the Song's current selection."""
    tracks = song.visible_tracks
    return compute_box(
        index_of(tracks, song.view.selected_track),
        focused_scene_index(song),
        len(tracks),
        box_width,
    )
