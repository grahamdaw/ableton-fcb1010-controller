"""What each switch does to the Live Set.

Functions here talk to objects shaped like Live's ``Song``, ``Track``,
``Scene`` and ``ClipSlot`` (see the protocols below) but never import
``Live``: in Live they receive the real objects, in tests a fake Song.
Each action returns a short description of what it did, for debug logging.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Protocol, TypeVar

from .settings import Settings


class ClipSlotLike(Protocol):
    @property
    def has_clip(self) -> bool: ...
    @property
    def is_recording(self) -> bool: ...
    @property
    def is_triggered(self) -> bool: ...
    def fire(self) -> None: ...


class TrackLike(Protocol):
    @property
    def clip_slots(self) -> Sequence[ClipSlotLike]: ...
    @property
    def can_be_armed(self) -> bool: ...
    @property
    def has_audio_input(self) -> bool: ...
    @property
    def has_midi_input(self) -> bool: ...

    arm: bool

    @property
    def playing_slot_index(self) -> int: ...
    def stop_all_clips(self, quantized: bool = True, /) -> None: ...


class SceneLike(Protocol):
    def fire(
        self, force_legato: bool = False, can_select_scene_on_launch: bool = True, /
    ) -> None: ...


class SongViewLike(Protocol):
    selected_track: TrackLike
    selected_scene: SceneLike


class SongLike(Protocol):
    @property
    def visible_tracks(self) -> Sequence[TrackLike]: ...
    @property
    def scenes(self) -> Sequence[SceneLike]: ...
    @property
    def view(self) -> SongViewLike: ...
    @property
    def can_undo(self) -> bool: ...
    def undo(self) -> object: ...
    def stop_all_clips(self, quantized: bool = True, /) -> None: ...


T = TypeVar("T")


def index_of(items: Sequence[T], item: object) -> int | None:
    """Index of ``item`` in ``items`` by identity or equality, or None."""
    for i, candidate in enumerate(items):
        if candidate is item or candidate == item:
            return i
    return None


def step(index: int | None, delta: int, count: int, mode: str) -> int | None:
    """Move ``index`` by ``delta`` within ``count`` items; None means "do nothing".

    ``mode`` is "clamp" (stop at the ends) or "wrap". An unknown current
    index (e.g. a return track is selected) enters the list from the end the
    move points away from: forward lands on the first item, back on the last.
    """
    if count == 0:
        return None
    if index is None:
        return 0 if delta > 0 else count - 1
    target = index + delta
    if 0 <= target < count:
        return target
    if mode == "wrap":
        return target % count
    return None


def focused_track(song: SongLike) -> TrackLike | None:
    """The selected track if it is a regular, visible track."""
    tracks = song.visible_tracks
    i = index_of(tracks, song.view.selected_track)
    return tracks[i] if i is not None else None


def focused_scene_index(song: SongLike) -> int | None:
    """Index of the selected scene, or None in a Set with no scenes."""
    return index_of(song.scenes, song.view.selected_scene)


def focused_slot(song: SongLike) -> ClipSlotLike | None:
    """The clip slot where the selected track and scene meet, if both are valid."""
    track = focused_track(song)
    scene = focused_scene_index(song)
    if track is None or scene is None:
        return None
    slots = track.clip_slots
    return slots[scene] if scene < len(slots) else None


def _move_track(song: SongLike, settings: Settings, delta: int) -> str:
    tracks = song.visible_tracks
    target = step(
        index_of(tracks, song.view.selected_track), delta, len(tracks), settings.navigation
    )
    if target is None:
        return "no-op: no track in that direction"
    song.view.selected_track = tracks[target]
    return f"track {target + 1}"


def _move_scene(song: SongLike, settings: Settings, delta: int) -> str:
    scenes = song.scenes
    target = step(focused_scene_index(song), delta, len(scenes), settings.navigation)
    if target is None:
        return "no-op: no scene in that direction"
    song.view.selected_scene = scenes[target]
    return f"scene {target + 1}"


def track_prev(song: SongLike, settings: Settings) -> str:
    """Select the previous regular track."""
    return _move_track(song, settings, -1)


def track_next(song: SongLike, settings: Settings) -> str:
    """Select the next regular track."""
    return _move_track(song, settings, 1)


def scene_prev(song: SongLike, settings: Settings) -> str:
    """Select the previous scene."""
    return _move_scene(song, settings, -1)


def scene_next(song: SongLike, settings: Settings) -> str:
    """Select the next scene."""
    return _move_scene(song, settings, 1)


def clip_launch(song: SongLike, settings: Settings) -> str:
    """Fire the focused slot if it holds a clip; an empty slot is left alone."""
    slot = focused_slot(song)
    if slot is None or not slot.has_clip:
        return "no-op: focused slot is empty"
    slot.fire()
    return "fired clip"


def clip_stop(song: SongLike, settings: Settings) -> str:
    """Quantized stop of whatever plays on the focused track."""
    track = focused_track(song)
    if track is None or track.playing_slot_index < 0:
        return "no-op: nothing playing on focused track"
    track.stop_all_clips(True)
    return "stopped track"


def slot_record(song: SongLike, settings: Settings) -> str:
    """Record into the focused empty slot, or end a recording in progress there.

    Never overwrites a clip, and does nothing on a track that cannot be armed.
    """
    track = focused_track(song)
    slot = focused_slot(song)
    if track is None or slot is None:
        return "no-op: no focused slot"
    if slot.has_clip:
        if slot.is_recording:
            slot.fire()
            return "ended recording"
        return "no-op: slot already holds a clip"
    if slot.is_triggered:
        return "no-op: recording already triggered"
    if not track.can_be_armed or not (track.has_audio_input or track.has_midi_input):
        return "no-op: track cannot be armed"
    if not track.arm:
        track.arm = True
    slot.fire()
    return "started recording"


def scene_launch(song: SongLike, settings: Settings) -> str:
    """Fire the selected scene; optionally move focus to the next scene."""
    index = focused_scene_index(song)
    if index is None:
        return "no-op: no scene"
    song.scenes[index].fire(False, False)
    if settings.scene_launch_advances:
        _move_scene(song, settings, 1)
    return f"fired scene {index + 1}"


def stop_all(song: SongLike, settings: Settings) -> str:
    """Quantized stop of every clip; the transport keeps running."""
    song.stop_all_clips(True)
    return "stopped all clips"


def undo(song: SongLike, settings: Settings) -> str:
    """Live's Undo, if there is anything to undo."""
    if not song.can_undo:
        return "no-op: nothing to undo"
    song.undo()
    return "undo"


def none(song: SongLike, settings: Settings) -> str:
    """A switch mapped to nothing."""
    return "no-op: unmapped"


Action = Callable[[SongLike, Settings], str]

CATALOGUE: dict[str, Action] = {
    "track_prev": track_prev,
    "track_next": track_next,
    "clip_launch": clip_launch,
    "clip_stop": clip_stop,
    "slot_record": slot_record,
    "scene_prev": scene_prev,
    "scene_next": scene_next,
    "scene_launch": scene_launch,
    "stop_all": stop_all,
    "undo": undo,
    "none": none,
}


def run(action: str, song: SongLike, settings: Settings) -> str:
    """Run the named action from :data:`CATALOGUE` against ``song``."""
    return CATALOGUE[action](song, settings)
