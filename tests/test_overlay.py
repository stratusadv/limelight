from __future__ import annotations

import pytest

from typing import TYPE_CHECKING, cast

from typing_extensions import override

from limelight.capture.camera import Camera
from limelight.config import DemoConfig
from limelight.overlay import Overlay
from limelight.overlay.assets import OVERLAY_CSS, OVERLAY_JAVASCRIPT
from limelight.overlay.bridge import Bridge
from limelight.overlay.cursor import BOX_POLL_MS, Cursor
from limelight.overlay.keyboard import Keyboard
from limelight.overlay.playback import Playback
from limelight.theme import Theme

from fakes import FakeClock, FakeLocator, FakePage

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from limelight.capture.renderer import FrameClock


CONFIG = DemoConfig(mode='narrate', step_ms=1000, video=True)


class CheckingLocator(FakeLocator):
    @override
    def evaluate(
        self,
        expression: str,
        argument: object = None,
        *,
        timeout: float | None = None,
    ) -> object:
        if 'elementFromPoint' in expression:
            self.checked = True

        return super().evaluate(expression, argument, timeout=timeout)


def card_argument(page: FakePage, name: str) -> Mapping[str, object]:
    arguments = [
        argument
        for expression, argument in page.evaluations
        if f'window.__limelight.{name}(' in expression
    ]

    return cast('Mapping[str, object]', arguments[0])


def overlay_build(
    page: FakePage,
    *,
    camera: Camera | None = None,
    clock: FrameClock | None = None,
    config: DemoConfig = CONFIG,
    theme: Theme | None = None,
) -> Overlay:
    bridge = Bridge(page.as_page(), config, theme)
    playback = Playback(bridge, config, clock=clock)

    return Overlay(
        bridge,
        playback,
        Cursor(bridge, playback),
        Keyboard(bridge, playback),
        camera=camera,
    )


def test_javascript_asset_installs_namespace() -> None:
    assert 'window.__limelight' in OVERLAY_JAVASCRIPT


def test_narrate_installs_a_missing_overlay_then_draws_caption() -> None:
    page = FakePage()
    page.installed = False
    overlay = overlay_build(page)

    overlay.narrate('Welcome', body='The tour begins.', step='Intro')

    install_argument = {
        'css': OVERLAY_CSS,
        'theme': Theme().payload(),
        'controls': False,
        'speedFactor': 1.0,
        'stepMode': False,
    }

    assert page.selector_waits == [('body', 'attached')]
    assert page.evaluations[1] == (OVERLAY_JAVASCRIPT, install_argument)
    assert page.evaluations[0][0] == page.evaluations[2][0]

    caption_arguments = [
        argument
        for expression, argument in page.evaluations
        if 'window.__limelight.caption(' in expression
    ]

    assert caption_arguments == [{
        'title': 'Welcome',
        'body': 'The tour begins.',
        'step': 'Intro',
    }]
    assert page.waits_ms == [1000]


def test_narrate_ms_override_wins() -> None:
    page = FakePage()
    overlay = overlay_build(page)

    overlay.narrate('Welcome', ms=250)

    assert page.waits_ms == [250]


def test_custom_theme_reaches_installer() -> None:
    page = FakePage()
    theme = Theme(color_accent='#123456')
    overlay = overlay_build(page, theme=theme)

    page.installed = False

    overlay.narrate('Welcome')

    install_argument = page.evaluations[1][1]

    assert isinstance(install_argument, dict)

    theme_payload = install_argument['theme']

    assert isinstance(theme_payload, dict)
    assert theme_payload['colorAccent'] == '#123456'


def test_spotlight_draws_settled_box() -> None:
    page = FakePage()
    overlay = overlay_build(page)

    box: Mapping[str, float] = {'x': 10, 'y': 20, 'width': 30, 'height': 40}
    boxes = [box, box]
    locator = FakeLocator(boxes=boxes)

    overlay.spotlight(locator.as_locator(), label='Click here', scroll=False)

    spot_arguments = [
        argument
        for expression, argument in page.evaluations
        if 'window.__limelight.spot(' in expression
    ]

    assert spot_arguments == [{'box': box, 'label': 'Click here', 'dim': True}]


def test_spotlight_without_box_skips_drawing() -> None:
    page = FakePage()
    overlay = overlay_build(page)

    overlay.spotlight(FakeLocator().as_locator(), scroll=False)

    spot_expressions = [
        expression
        for expression, argument in page.evaluations
        if 'window.__limelight.spot(' in expression
    ]

    assert spot_expressions == []


def test_click_glides_cursor_then_clicks() -> None:
    page = FakePage()
    overlay = overlay_build(page)

    box: Mapping[str, float] = {'x': 100, 'y': 200, 'width': 40, 'height': 20}
    boxes = [box]
    locator = FakeLocator(boxes=boxes)

    overlay.click(locator.as_locator())

    move_arguments = [
        argument
        for expression, argument in page.evaluations
        if 'window.__limelight.cursorMove(' in expression
    ]
    pulse_expressions = [
        expression
        for expression, _ in page.evaluations
        if 'window.__limelight.cursorPulse(' in expression
    ]

    assert move_arguments == [{'x': 120.0, 'y': 210.0, 'ms': 500}]
    assert len(pulse_expressions) == 1
    assert locator.click_count == 0
    assert page.mouse.actions == [('move', 120.0, 210.0, 1), ('down',), ('up',)]


def test_actions_hold_for_a_step_once_they_finish() -> None:
    page = FakePage()
    overlay = overlay_build(page)
    locator = FakeLocator(boxes=[page.locator_box])

    overlay.click(locator.as_locator())
    overlay.hover(locator.as_locator())
    overlay.press(locator.as_locator(), 'Enter')

    holds = [wait for wait in page.waits_ms if wait == 1000]

    assert len(holds) == 3
    assert page.waits_ms[-1] == 1000


def test_fill_holds_once_not_per_click() -> None:
    page = FakePage()
    overlay = overlay_build(page)
    locator = FakeLocator(boxes=[page.locator_box])

    overlay.fill(locator.as_locator(), 'hi')

    holds = [wait for wait in page.waits_ms if wait == 1000]

    assert len(holds) == 1


def test_click_falls_back_to_the_locator_when_the_point_misses() -> None:
    page = FakePage()
    overlay = overlay_build(page)

    box: Mapping[str, float] = {'x': 100, 'y': 200, 'width': 40, 'height': 20}
    boxes = [box]
    locator = FakeLocator(boxes=boxes)
    locator.point_hits = False

    overlay.click(locator.as_locator())

    assert locator.click_count == 1
    assert page.mouse.actions == []


def test_click_forced_presses_the_mouse_without_a_hit_test() -> None:
    page = FakePage()
    overlay = overlay_build(page)

    box: Mapping[str, float] = {'x': 100, 'y': 200, 'width': 40, 'height': 20}
    boxes = [box]
    locator = FakeLocator(boxes=boxes)
    locator.point_hits = False

    overlay.click(locator.as_locator(), force=True)

    assert locator.click_count == 0
    assert page.mouse.actions == [('move', 120.0, 210.0, 1), ('down',), ('up',)]


def test_click_hides_the_control_bar_while_it_covers_the_point() -> None:
    page = FakePage()
    page.control_covers = True
    overlay = overlay_build(page)

    box: Mapping[str, float] = {'x': 100, 'y': 200, 'width': 40, 'height': 20}
    boxes = [box]
    locator = FakeLocator(boxes=boxes)

    overlay.click(locator.as_locator())

    control_expressions = [
        expression
        for expression, _ in page.evaluations
        if 'controlHide(' in expression or 'controlShow(' in expression
    ]

    assert len(control_expressions) == 2
    assert 'controlHide(' in control_expressions[0]
    assert 'controlShow(' in control_expressions[1]
    assert page.mouse.actions == [('move', 120.0, 210.0, 1), ('down',), ('up',)]


def test_click_leaves_the_control_bar_alone_when_it_is_clear_of_the_point() -> None:
    page = FakePage()
    overlay = overlay_build(page)

    box: Mapping[str, float] = {'x': 100, 'y': 200, 'width': 40, 'height': 20}
    boxes = [box]
    locator = FakeLocator(boxes=boxes)

    overlay.click(locator.as_locator())

    control_expressions = [
        expression
        for expression, _ in page.evaluations
        if 'controlHide(' in expression or 'controlShow(' in expression
    ]

    assert control_expressions == []


def test_click_scrolls_target_into_view_first() -> None:
    page = FakePage()
    overlay = overlay_build(page)

    box: Mapping[str, float] = {'x': 0, 'y': 0, 'width': 10, 'height': 10}
    boxes = [box]
    locator = FakeLocator(boxes=boxes)

    overlay.click(locator.as_locator())

    assert locator.scroll_timeouts == [4000]


def test_check_glides_then_checks() -> None:
    page = FakePage()
    overlay = overlay_build(page)

    box: Mapping[str, float] = {'x': 0, 'y': 0, 'width': 10, 'height': 10}
    boxes = [box]
    locator = FakeLocator(boxes=boxes)

    overlay.check(locator.as_locator())

    pulse_expressions = [
        expression
        for expression, _ in page.evaluations
        if 'window.__limelight.cursorPulse(' in expression
    ]

    assert len(pulse_expressions) == 1
    assert locator.check_count == 1
    assert locator.click_count == 0


def test_check_presses_the_mouse_on_an_unchecked_box() -> None:
    page = FakePage()
    overlay = overlay_build(page)

    box: Mapping[str, float] = {'x': 0, 'y': 0, 'width': 10, 'height': 10}
    boxes = [box]
    locator = FakeLocator(boxes=boxes)
    locator.checked = False

    overlay.check(locator.as_locator())

    assert page.mouse.actions == [('move', 5.0, 5.0, 1), ('down',), ('up',)]
    assert locator.check_count == 1


def test_check_skips_a_box_already_checked() -> None:
    page = FakePage()
    overlay = overlay_build(page)

    box: Mapping[str, float] = {'x': 0, 'y': 0, 'width': 10, 'height': 10}
    boxes = [box]
    locator = FakeLocator(boxes=boxes)
    locator.checked = True

    overlay.check(locator.as_locator())

    assert page.mouse.actions == []
    assert locator.check_count == 0


def test_uncheck_glides_then_unchecks() -> None:
    page = FakePage()
    overlay = overlay_build(page)
    locator = FakeLocator()

    overlay.uncheck(locator.as_locator())

    assert locator.uncheck_count == 1


def test_hover_glides_without_pulse() -> None:
    page = FakePage()
    overlay = overlay_build(page)

    box: Mapping[str, float] = {'x': 0, 'y': 0, 'width': 10, 'height': 10}
    boxes = [box]
    locator = FakeLocator(boxes=boxes)

    overlay.hover(locator.as_locator())

    pulse_expressions = [
        expression
        for expression, _ in page.evaluations
        if 'window.__limelight.cursorPulse(' in expression
    ]

    assert pulse_expressions == []
    assert locator.hover_count == 0
    assert page.mouse.actions == [('move', 5.0, 5.0, 1)]


def test_hover_falls_back_to_the_locator_when_the_point_misses() -> None:
    page = FakePage()
    overlay = overlay_build(page)

    box: Mapping[str, float] = {'x': 0, 'y': 0, 'width': 10, 'height': 10}
    boxes = [box]
    locator = FakeLocator(boxes=boxes)
    locator.point_hits = False

    overlay.hover(locator.as_locator())

    assert locator.hover_count == 1
    assert page.mouse.actions == []


def test_press_flashes_key_then_presses() -> None:
    page = FakePage()
    overlay = overlay_build(page)
    locator = FakeLocator()

    overlay.press(locator.as_locator(), 'Enter')

    flash_arguments = [
        argument
        for expression, argument in page.evaluations
        if 'window.__limelight.keyFlash(' in expression
    ]

    assert flash_arguments == [{'text': 'Enter'}]
    assert locator.pressed_keys == ['Enter']


def test_slide_drags_thumb_with_cursor() -> None:
    page = FakePage()
    overlay = overlay_build(page)

    track_box: Mapping[str, float] = {'x': 0, 'y': 10, 'width': 200, 'height': 20}
    thumb_box: Mapping[str, float] = {'x': 0, 'y': 10, 'width': 20, 'height': 20}

    track_boxes = [track_box]
    thumb_boxes = [thumb_box]

    track = FakeLocator(boxes=track_boxes)
    thumb = FakeLocator(boxes=thumb_boxes)

    overlay.slide(track=track.as_locator(), thumb=thumb.as_locator())

    move_actions = [action for action in page.mouse.actions if action[0] == 'move']

    assert page.mouse.actions[0] == ('move', 10.0, 20.0, 1)
    assert page.mouse.actions[1] == ('down',)
    assert page.mouse.actions[-1] == ('up',)
    assert move_actions[-1] == ('move', 200.0, 20.0, 3)
    assert len(move_actions) == 9


def test_slide_rejects_missing_track_box() -> None:
    page = FakePage()
    overlay = overlay_build(page)

    thumb_box: Mapping[str, float] = {'x': 0, 'y': 10, 'width': 20, 'height': 20}
    thumb_boxes = [thumb_box]
    thumb = FakeLocator(boxes=thumb_boxes)

    with pytest.raises(ValueError, match='track'):
        overlay.slide(track=FakeLocator().as_locator(), thumb=thumb.as_locator())


def test_fill_toggles_key_hud() -> None:
    page = FakePage()
    overlay = overlay_build(page)
    locator = FakeLocator()

    overlay.fill(locator.as_locator(), 'hi')

    expressions = [expression for expression, _ in page.evaluations]

    assert any('window.__limelight.keyHudEnable(' in expression for expression in expressions)
    assert any('window.__limelight.keyHudDisable(' in expression for expression in expressions)


def test_click_without_box_still_clicks() -> None:
    page = FakePage()
    overlay = overlay_build(page)
    locator = FakeLocator()

    overlay.click(locator.as_locator())

    move_expressions = [
        expression
        for expression, _ in page.evaluations
        if 'window.__limelight.cursorMove(' in expression
    ]

    assert move_expressions == []
    assert locator.click_count == 1


def test_fill_clicks_then_clears_then_types() -> None:
    page = FakePage()
    overlay = overlay_build(page)

    box: Mapping[str, float] = {'x': 0, 'y': 0, 'width': 10, 'height': 10}
    boxes = [box]
    locator = FakeLocator(boxes=boxes)

    overlay.fill(locator.as_locator(), 'hello')

    assert page.mouse.actions == [('move', 5.0, 5.0, 1), ('down',), ('up',)]
    assert locator.fill_values == ['']
    assert locator.typed_sequences == [('hello', 55.0)]


def test_fill_sets_untypeable_inputs_directly() -> None:
    page = FakePage()
    overlay = overlay_build(page)

    box: Mapping[str, float] = {'x': 0, 'y': 0, 'width': 10, 'height': 10}
    boxes = [box]
    locator = FakeLocator(boxes=boxes)
    locator.input_type = 'date'

    overlay.fill(locator.as_locator(), '2026-08-02')

    assert page.mouse.actions == [('move', 5.0, 5.0, 1), ('down',), ('up',)]
    assert locator.fill_values == ['2026-08-02']
    assert locator.typed_sequences == []


def test_fill_type_delay_scales_with_speed() -> None:
    page = FakePage()
    config = DemoConfig(mode='narrate', step_ms=1000, speed_factor=2.0, video=True)
    overlay = overlay_build(page, config=config)
    locator = FakeLocator()

    overlay.fill(locator.as_locator(), 'hi')

    assert locator.typed_sequences == [('hi', 27.5)]


def test_select_pulses_then_selects() -> None:
    page = FakePage()
    overlay = overlay_build(page)

    box: Mapping[str, float] = {'x': 0, 'y': 0, 'width': 10, 'height': 10}
    boxes = [box]
    locator = FakeLocator(boxes=boxes)

    overlay.select(locator.as_locator(), 'Approved')

    pulse_expressions = [
        expression
        for expression, _ in page.evaluations
        if 'window.__limelight.cursorPulse(' in expression
    ]

    assert len(pulse_expressions) == 1
    assert locator.select_labels == ['Approved']
    assert locator.click_count == 0


def test_select_walks_a_rendered_dropdown_to_the_option() -> None:
    page = FakePage()
    overlay = overlay_build(page)

    box: Mapping[str, float] = {'x': 0, 'y': 0, 'width': 10, 'height': 10}
    boxes = [box]
    locator = FakeLocator(boxes=boxes)
    locator.option_labels = ['Draft', 'Approved', 'Rejected']

    overlay.select(locator.as_locator(), 'Approved')

    show_arguments = [
        argument
        for expression, argument in page.evaluations
        if 'window.__limelight.selectShow(' in expression
    ]
    move_arguments = [
        argument
        for expression, argument in page.evaluations
        if 'window.__limelight.cursorMove(' in expression
    ]
    hide_expressions = [
        expression
        for expression, _ in page.evaluations
        if 'window.__limelight.selectHide(' in expression
    ]

    assert show_arguments == [
        {'box': box, 'options': ['Draft', 'Approved', 'Rejected'], 'index': 1},
    ]
    assert move_arguments[-1] == {'x': 30.0, 'y': 60.0, 'ms': 500}
    assert len(hide_expressions) == 1
    assert locator.select_labels == ['Approved']


def test_select_without_the_option_label_skips_the_dropdown() -> None:
    page = FakePage()
    overlay = overlay_build(page)

    box: Mapping[str, float] = {'x': 0, 'y': 0, 'width': 10, 'height': 10}
    boxes = [box]
    locator = FakeLocator(boxes=boxes)
    locator.option_labels = ['Draft']

    overlay.select(locator.as_locator(), 'Approved')

    show_expressions = [
        expression
        for expression, _ in page.evaluations
        if 'window.__limelight.selectShow(' in expression
    ]

    assert show_expressions == []
    assert locator.select_labels == ['Approved']


def test_javascript_asset_defines_cursor_and_peek() -> None:
    assert 'cursorMove' in OVERLAY_JAVASCRIPT
    assert 'cursorPulse' in OVERLAY_JAVASCRIPT
    assert 'controlCovers' in OVERLAY_JAVASCRIPT
    assert 'controlPeek' in OVERLAY_JAVASCRIPT
    assert 'sentiment-' in OVERLAY_JAVASCRIPT
    assert 'getAnimations' in OVERLAY_JAVASCRIPT


def test_stylesheet_asset_carries_the_overlay_rules() -> None:
    assert '#limelight-caption' in OVERLAY_CSS
    assert 'var(--limelight-accent)' in OVERLAY_CSS
    assert '${' not in OVERLAY_CSS


def test_control_bar_is_fixed_and_anchored_to_the_window_edge() -> None:
    block = OVERLAY_CSS.split('#limelight-control {')[1].split('}')[0]

    assert 'position: fixed;' in block
    assert 'right: 32px;' in block
    assert 'bottom: 32px;' in block
    assert 'pointer-events: none;' in block
    assert 'vw' not in block
    assert 'opacity' not in block
    assert 'controlAnchor(bar)' in OVERLAY_JAVASCRIPT
    assert 'new ResizeObserver(() => controlAnchor(bar))' in OVERLAY_JAVASCRIPT


def test_control_buttons_act_on_press_not_click() -> None:
    assert "addEventListener('pointerdown', () => handler())" in OVERLAY_JAVASCRIPT
    assert 'event.detail > 0' in OVERLAY_JAVASCRIPT


def test_calls_are_guarded_against_an_uninstalled_overlay() -> None:
    page = FakePage()
    overlay = overlay_build(page)

    overlay.spotlight(FakeLocator(boxes=[page.locator_box]).as_locator())

    for expression, _ in page.evaluations:
        assert 'window.__limelight' in expression


def test_title_hides_then_removes() -> None:
    page = FakePage()
    overlay = overlay_build(page)

    overlay.title('Chapter One')

    expressions = [expression for expression, _ in page.evaluations]

    hide_index = next(
        index
        for index, text in enumerate(expressions)
        if 'window.__limelight.titleHide(' in text
    )
    remove_index = next(
        index
        for index, text in enumerate(expressions)
        if 'window.__limelight.titleRemove(' in text
    )

    assert hide_index < remove_index


def test_clock_measures_holds_in_frames() -> None:
    page = FakePage()
    clock = FakeClock()
    overlay = overlay_build(page, clock=clock)

    overlay.pause(400)
    overlay.pause()

    assert clock.waits_ms == [400, 1000]
    assert page.waits_ms == []


def test_clock_types_one_character_per_wait() -> None:
    page = FakePage()
    clock = FakeClock()
    overlay = overlay_build(page, clock=clock)
    locator = FakeLocator(boxes=[page.locator_box])

    overlay.fill(locator.as_locator(), 'ab')

    assert [value for value, _delay in locator.typed_sequences] == ['a', 'b']
    assert len(clock.waits_ms) >= 2
    assert set(page.waits_ms) <= {BOX_POLL_MS}


def test_wait_holds_for_its_length() -> None:
    page = FakePage()
    overlay = overlay_build(page)

    overlay.wait(300)

    assert page.waits_ms == [300]


def test_check_leaves_a_box_that_is_already_checked() -> None:
    page = FakePage()
    overlay = overlay_build(page)
    locator = FakeLocator([{'x': 0, 'y': 0, 'width': 10, 'height': 10}])

    locator.checked = True

    overlay.check(locator.as_locator())

    assert locator.check_count == 0
    assert locator.uncheck_count == 0


def test_uncheck_drives_a_box_that_is_still_checked() -> None:
    page = FakePage()
    overlay = overlay_build(page)
    locator = FakeLocator([{'x': 0, 'y': 0, 'width': 10, 'height': 10}])

    locator.checked = True
    locator.point_hits = False

    overlay.uncheck(locator.as_locator())

    assert locator.uncheck_count == 1


def test_screenshot_without_a_camera_writes_nothing() -> None:
    page = FakePage()
    overlay = overlay_build(page)

    assert overlay.screenshot('shot') is None
    assert page.screenshot_paths == []


def test_screenshot_hides_the_control_bar_around_the_capture(tmp_path: Path) -> None:
    page = FakePage()
    overlay = overlay_build(page, camera=Camera(page.as_page(), tmp_path))

    path = overlay.screenshot('shot')

    assert path is not None
    assert path.name == '01-shot.png'
    assert len(page.screenshot_paths) == 1


def test_switch_page_moves_the_camera(tmp_path: Path) -> None:
    page_first = FakePage()
    page_second = FakePage()
    overlay = overlay_build(page_first, camera=Camera(page_first.as_page(), tmp_path))

    overlay.switch_page(page_second.as_page())
    overlay.screenshot('shot')

    assert page_first.screenshot_paths == []
    assert len(page_second.screenshot_paths) == 1


def test_metrics_draws_a_card() -> None:
    page = FakePage()
    overlay = overlay_build(page)

    overlay.metrics('Throughput', [], kicker='Before and after', subtitle='One run')

    argument = card_argument(page, 'metrics')

    assert argument['title'] == 'Throughput'
    assert argument['kicker'] == 'Before and after'
    assert argument['subtitle'] == 'One run'
    assert argument['rows'] == []


def test_a_box_that_is_checked_by_the_click_is_left_alone() -> None:
    page = FakePage()
    overlay = overlay_build(page)
    locator = CheckingLocator([{'x': 0, 'y': 0, 'width': 10, 'height': 10}])

    overlay.check(locator.as_locator())

    assert locator.check_count == 0
    assert locator.checked is True


def test_a_dropdown_option_without_a_box_is_skipped() -> None:
    page = FakePage()
    overlay = overlay_build(page)
    box = {'x': 0, 'y': 0, 'width': 100, 'height': 20}
    locator = FakeLocator([box, box, None])

    locator.option_labels = ['Draft', 'Approved']

    overlay.select(locator.as_locator(), 'Approved')

    assert locator.select_labels == ['Approved']
