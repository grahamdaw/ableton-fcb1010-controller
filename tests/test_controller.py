from dataclasses import replace
from typing import cast

from FCB1010.actions import SongLike
from FCB1010.controller import Controller
from FCB1010.session_box import HIDDEN, Box
from FCB1010.settings import DEFAULTS, Settings

from .fake_live import FakeSong


class Harness:
    def __init__(self, song: FakeSong | None = None, settings: Settings = DEFAULTS) -> None:
        self.song = song or FakeSong()
        self.logs: list[str] = []
        self.boxes: list[Box] = []
        self.controller = Controller(
            settings,
            song=lambda: cast(SongLike, self.song),
            log=self.logs.append,
            set_highlight=self.boxes.append,
        )
        self.t = 0.0

    def press(self, switch: int, with_note: bool = True) -> None:
        self.t += 200
        self.controller.on_midi((0xCF, switch - 1), self.t)
        if with_note:
            self.controller.on_midi((0x9F, 59 + switch, 64), self.t + 1)
        self.controller.refresh_box()


def test_ten_presses_yield_ten_events() -> None:
    h = Harness()
    for _ in range(10):
        h.press(7)  # Scene ↓, PC + note each time
    assert h.song.changes == ["selected_scene"] * 7  # clamps at scene 8
    assert h.song.view.selected_scene is h.song.scenes[7]


def test_box_moves_on_every_scene_press_and_not_on_track_press() -> None:
    h = Harness()
    h.controller.refresh_box()
    h.press(7)
    h.press(7)
    h.press(2)
    assert h.boxes == [Box(0, 0, 4, 1), Box(0, 1, 4, 1), Box(0, 2, 4, 1)]


def test_box_follows_selection_changed_elsewhere() -> None:
    h = Harness()
    h.controller.refresh_box()
    h.song.select(1, 5)  # e.g. a mouse click
    h.controller.refresh_box()
    assert h.boxes[-1] == Box(0, 5, 4, 1)
    h.press(7)
    assert h.song.view.selected_scene is h.song.scenes[6]


def test_debug_logging_off_by_default() -> None:
    h = Harness()
    h.press(7)
    assert h.logs == []


def test_debug_logging_names_switch_and_result() -> None:
    h = Harness(settings=replace(DEFAULTS, debug=True))
    h.press(7)
    assert h.logs == ["FCB1010: switch 7 scene_next: scene 2"]


def test_action_error_is_logged_and_dropped() -> None:
    h = Harness()

    def boom() -> None:
        raise RuntimeError("Live said no")

    h.song.undo = boom  # type: ignore[method-assign]
    h.press(10)
    assert len(h.logs) == 1
    assert h.logs[0].startswith("FCB1010: error handling") and "Live said no" in h.logs[0]
    h.press(7)  # still works afterwards
    assert h.song.view.selected_scene is h.song.scenes[1]


def test_box_error_is_logged() -> None:
    h = Harness()
    h.song.view._scene = object()  # type: ignore[assignment]
    h.song.scenes = None  # type: ignore[assignment]
    h.controller.refresh_box()
    assert h.logs and h.logs[0].startswith("FCB1010: error updating highlight box")


def test_empty_set_every_switch_is_quiet() -> None:
    song = FakeSong(tracks=0, scenes=0)
    song.can_undo = False
    h = Harness(song)
    for switch in range(1, 11):
        h.press(switch)
    assert h.logs == []
    assert h.boxes == [HIDDEN]


def test_draw_hidden_then_refresh_redraws() -> None:
    h = Harness()
    h.controller.refresh_box()
    h.controller.draw(HIDDEN)
    h.controller.refresh_box()
    assert h.boxes == [Box(0, 0, 4, 1), HIDDEN, Box(0, 0, 4, 1)]


def test_notes_for_midi_map() -> None:
    assert Harness().controller.notes == list(range(60, 70))
