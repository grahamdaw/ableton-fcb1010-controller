"""A minimal in-memory stand-in for Live's Song, enough to drive the actions."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(eq=False)
class FakeClipSlot:
    has_clip: bool = False
    is_recording: bool = False
    is_triggered: bool = False
    fired: int = 0

    def fire(self) -> None:
        self.fired += 1


@dataclass(eq=False)
class FakeTrack:
    name: str
    clip_slots: list[FakeClipSlot] = field(default_factory=list)
    can_be_armed: bool = True
    has_audio_input: bool = True
    has_midi_input: bool = False
    arm: bool = False
    playing_slot_index: int = -1
    stopped: list[bool] = field(default_factory=list)

    def stop_all_clips(self, quantized: bool = True, /) -> None:
        self.stopped.append(quantized)


@dataclass(eq=False)
class FakeScene:
    name: str
    fired: list[tuple[bool, bool]] = field(default_factory=list)

    def fire(self, force_legato: bool = False, can_select_scene_on_launch: bool = True, /) -> None:
        self.fired.append((force_legato, can_select_scene_on_launch))


class FakeView:
    def __init__(self, on_change: Callable[[str], None]) -> None:
        self._on_change = on_change
        self._track: FakeTrack | None = None
        self._scene: FakeScene | None = None

    @property
    def selected_track(self) -> FakeTrack | None:
        return self._track

    @selected_track.setter
    def selected_track(self, value: FakeTrack) -> None:
        self._track = value
        self._on_change("selected_track")

    @property
    def selected_scene(self) -> FakeScene | None:
        return self._scene

    @selected_scene.setter
    def selected_scene(self, value: FakeScene) -> None:
        self._scene = value
        self._on_change("selected_scene")


class FakeSong:
    def __init__(self, tracks: int = 4, scenes: int = 8) -> None:
        self.changes: list[str] = []
        self.view = FakeView(self.changes.append)
        self.scenes = [FakeScene(f"S{i + 1}") for i in range(scenes)]
        self.visible_tracks = [
            FakeTrack(f"T{i + 1}", [FakeClipSlot() for _ in range(scenes)]) for i in range(tracks)
        ]
        self.return_track = FakeTrack("A-Return", can_be_armed=False)
        self.can_undo = True
        self.undone = 0
        self.stopped_all: list[bool] = []
        self.view._track = self.visible_tracks[0] if tracks else self.return_track
        self.view._scene = self.scenes[0] if scenes else None

    def undo(self) -> str:
        self.undone += 1
        return "undo"

    def stop_all_clips(self, quantized: bool = True, /) -> None:
        self.stopped_all.append(quantized)

    def select(self, track: int, scene: int) -> None:
        self.view._track = self.visible_tracks[track]
        self.view._scene = self.scenes[scene]

    def slot(self, track: int, scene: int) -> FakeClipSlot:
        return self.visible_tracks[track].clip_slots[scene]
