from __future__ import annotations

from typing import TYPE_CHECKING

from typing_extensions import override

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from limelight.config import DemoConfig
from limelight.overlay.bridge import Bridge
from limelight.overlay.cursor import BOX_POLL_MS, Cursor
from limelight.overlay.playback import Playback

from fakes import FakeLocator, FakePage

if TYPE_CHECKING:
    from playwright.sync_api import FloatRect

    from collections.abc import Mapping


CONFIG = DemoConfig(mode='narrate', video=True)


class TimingOutLocator(FakeLocator):
    @override
    def bounding_box(self, *, timeout: float | None = None) -> FloatRect | None:
        message = 'bounding box timed out'
        raise PlaywrightTimeoutError(message)


def cursor_build(page: FakePage, *, visible: bool = True) -> Cursor:
    bridge = Bridge(page.as_page(), CONFIG)

    return Cursor(bridge, Playback(bridge, CONFIG), visible=visible)


def test_glide_travels_to_the_settled_center() -> None:
    page = FakePage()
    cursor = cursor_build(page)

    box: Mapping[str, float] = {'x': 100, 'y': 200, 'width': 40, 'height': 20}
    locator = FakeLocator(boxes=[box])

    assert cursor.glide(locator.as_locator()) == (120.0, 210.0)
    assert page.evaluations[-1][1] == {'x': 120.0, 'y': 210.0, 'ms': 500}
    assert page.waits_ms == [BOX_POLL_MS, 500.0]


def test_glide_without_a_box_goes_nowhere() -> None:
    page = FakePage()
    cursor = cursor_build(page)

    assert cursor.glide(FakeLocator().as_locator()) is None
    assert page.evaluations == []


def test_drag_moves_in_chunks_between_press_and_release() -> None:
    page = FakePage()
    cursor = cursor_build(page)

    cursor.drag(x_start=10.0, x_end=200.0, y=20.0, ms=700)

    move_actions = [action for action in page.mouse.actions if action[0] == 'move']

    assert page.mouse.actions[0] == ('move', 10.0, 20.0, 1)
    assert page.mouse.actions[1] == ('down',)
    assert page.mouse.actions[-1] == ('up',)
    assert move_actions[-1] == ('move', 200.0, 20.0, 3)
    assert len(move_actions) == 9


def test_a_box_that_never_answers_reads_as_missing() -> None:
    page = FakePage()
    cursor = cursor_build(page)
    locator = TimingOutLocator()

    assert cursor.box(locator.as_locator()) is None


def test_a_hidden_cursor_draws_nothing_and_keeps_the_pacing() -> None:
    page = FakePage()
    cursor = cursor_build(page, visible=False)

    box: Mapping[str, float] = {'x': 100, 'y': 200, 'width': 40, 'height': 20}
    locator = FakeLocator(boxes=[box])

    assert cursor.glide(locator.as_locator()) == (120.0, 210.0)
    assert page.evaluations == []
    assert page.waits_ms == [BOX_POLL_MS, 500.0]


def test_a_hidden_cursor_still_drives_the_real_mouse() -> None:
    page = FakePage()
    cursor = cursor_build(page, visible=False)

    cursor.drag(x_start=10.0, x_end=200.0, y=20.0, ms=700)

    move_actions = [action for action in page.mouse.actions if action[0] == 'move']

    assert page.evaluations == []
    assert move_actions[-1] == ('move', 200.0, 20.0, 3)
