from __future__ import annotations

from limelight.config import DemoConfig
from limelight.overlay.bridge import Bridge
from limelight.overlay.keyboard import Keyboard
from limelight.overlay.playback import Playback

from fakes import FakeClock, FakeLocator, FakePage


CONFIG = DemoConfig(mode='narrate', video=True)


def keyboard_build(page: FakePage, *, clock: FakeClock | None = None) -> Keyboard:
    bridge = Bridge(page.as_page(), CONFIG)

    return Keyboard(bridge, Playback(bridge, CONFIG, clock=clock))


def test_type_clears_then_types_under_the_key_hud() -> None:
    page = FakePage()
    keyboard = keyboard_build(page)
    locator = FakeLocator()

    keyboard.type(locator.as_locator(), 'hello')

    expressions = [expression for expression, _ in page.evaluations]

    assert locator.fill_values == ['']
    assert locator.typed_sequences == [('hello', 55.0)]
    assert any('keyHudEnable(' in expression for expression in expressions)
    assert any('inputDriveEnd(' in expression for expression in expressions)


def test_type_under_a_clock_waits_one_frame_per_character() -> None:
    page = FakePage()
    clock = FakeClock()
    keyboard = keyboard_build(page, clock=clock)
    locator = FakeLocator()

    keyboard.type(locator.as_locator(), 'ab')

    assert [value for value, _delay in locator.typed_sequences] == ['a', 'b']
    assert clock.waits_ms == [55.0, 55.0]


def test_types_faithfully_refuses_a_date_input() -> None:
    page = FakePage()
    keyboard = keyboard_build(page)
    locator = FakeLocator()
    locator.input_type = 'date'

    assert keyboard.types_faithfully(locator.as_locator()) is False


def test_press_flashes_the_key_inside_the_drive_guard() -> None:
    page = FakePage()
    keyboard = keyboard_build(page)
    locator = FakeLocator()

    keyboard.press(locator.as_locator(), 'Enter')

    calls = [
        expression.split('window.__limelight.')[1].split('(')[0]
        for expression, _ in page.evaluations
    ]

    assert locator.pressed_keys == ['Enter']
    assert calls == ['keyFlash', 'inputDriveBegin', 'inputDriveEnd']
