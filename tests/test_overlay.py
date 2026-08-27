from __future__ import annotations

import pytest

from typing import TYPE_CHECKING

from limelight.overlay import OVERLAY_JAVASCRIPT, SPOT_BOX_POLL_MS, Overlay
from limelight.theme import Theme
from limelight.timing import DemoTiming

from fakes import FakeClock, FakeLocator, FakePage

if TYPE_CHECKING:
    from collections.abc import Mapping


def overlay_build(page: FakePage, *, theme: Theme | None = None) -> Overlay:
    return Overlay(page.as_page(), DemoTiming(step_ms=1000), theme=theme)


def test_javascript_asset_installs_namespace() -> None:
    assert 'window.__limelight' in OVERLAY_JAVASCRIPT


def test_narrate_installs_overlay_then_draws_caption() -> None:
    page = FakePage()
    overlay = overlay_build(page)

    overlay.narrate('Welcome', body='The tour begins.', step='Intro')

    install_argument = {'theme': Theme().payload(), 'controls': False, 'speedFactor': 1.0, 'stepMode': False}

    assert page.selector_waits == [('body', 'attached')]
    assert page.evaluations[0] == (OVERLAY_JAVASCRIPT, install_argument)

    caption_arguments = [
        argument
        for expression, argument in page.evaluations
        if 'window.__limelight.caption(' in expression
    ]

    assert caption_arguments == [{
        'title': 'Welcome',
        'body': 'The tour begins.',
        'step': 'Intro',
        'tag': '',
        'kind': '',
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

    overlay.narrate('Welcome')

    install_argument = page.evaluations[0][1]

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
    timing = DemoTiming(step_ms=1000, scale_factor=0.5)
    overlay = Overlay(page.as_page(), timing)
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
    assert 'controlPeek' in OVERLAY_JAVASCRIPT
    assert 'sentiment-' in OVERLAY_JAVASCRIPT
    assert 'getAnimations' in OVERLAY_JAVASCRIPT


def test_control_bar_is_fixed_and_scrollbar_stable() -> None:
    block = OVERLAY_JAVASCRIPT.split('#limelight-control {')[1].split('}')[0]

    assert 'position: fixed;' in block
    assert 'left: calc(100vw - 18px);' in block
    assert 'bottom: 18px;' in block
    assert 'pointer-events: none;' in block


def test_control_buttons_act_on_press_not_click() -> None:
    assert "addEventListener('pointerdown', () => {" in OVERLAY_JAVASCRIPT
    assert 'CONTROL_PRESS_WINDOW_MS' in OVERLAY_JAVASCRIPT


def test_clear_is_guarded_against_uninstalled_overlay() -> None:
    page = FakePage()
    overlay = overlay_build(page)

    overlay.clear()

    for expression, _ in page.evaluations:
        assert 'window.__limelight &&' in expression


def test_title_card_hides_then_removes() -> None:
    page = FakePage()
    overlay = overlay_build(page)

    overlay.title_card('Chapter One')

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
    overlay = Overlay(page.as_page(), DemoTiming(step_ms=1000), clock=clock)

    overlay.beat(400)
    overlay.hold()

    assert clock.waits_ms == [400, 1000]
    assert page.waits_ms == []


def test_clock_types_one_character_per_wait() -> None:
    page = FakePage()
    clock = FakeClock()
    overlay = Overlay(page.as_page(), DemoTiming(step_ms=1000), clock=clock)
    locator = FakeLocator(boxes=[page.locator_box])

    overlay.fill(locator.as_locator(), 'ab')

    assert [value for value, _delay in locator.typed_sequences] == ['a', 'b']
    assert len(clock.waits_ms) >= 2
    assert set(page.waits_ms) <= {SPOT_BOX_POLL_MS}
