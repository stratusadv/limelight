from __future__ import annotations

import pytest

from limelight.config import DemoConfig
from limelight.overlay import Overlay
from limelight.overlay.assets import OVERLAY_CSS
from limelight.overlay.bridge import Bridge
from limelight.overlay.cursor import Cursor
from limelight.overlay.keyboard import Keyboard
from limelight.overlay.playback import Playback
from limelight.theme import Theme

from fakes import FakePage


CONFIG = DemoConfig(mode='narrate', step_ms=1000)
CONFIG_PRESENT = DemoConfig(mode='present', step_ms=1000)
CONFIG_VIDEO = DemoConfig(mode='narrate', step_ms=1000, video=True)


def control_state(
    *,
    paused: bool = False,
    skip: bool = False,
    speed_factor: float = 1.0,
) -> dict[str, object]:
    return {'paused': paused, 'skip': skip, 'speedFactor': speed_factor}


def overlay_build(page: FakePage, config: DemoConfig = CONFIG) -> Overlay:
    bridge = Bridge(page.as_page(), config)
    playback = Playback(bridge, config)

    return Overlay(bridge, playback, Cursor(bridge, playback), Keyboard(bridge, playback))


def playback_build(page: FakePage, config: DemoConfig = CONFIG) -> Playback:
    return Playback(Bridge(page.as_page(), config), config)


def test_control_state_without_a_speed_factor_raises() -> None:
    page = FakePage()
    playback = playback_build(page)

    page.control_states = [{'paused': False, 'skip': False}]

    with pytest.raises(TypeError, match='speed factor'):
        playback.wait(100)


def test_controls_disabled_waits_in_one_piece() -> None:
    page = FakePage()
    playback = playback_build(page, CONFIG_VIDEO)

    playback.wait(500)

    assert page.waits_ms == [500.0]


def test_overlay_installs_itself_as_init_script() -> None:
    page = FakePage()

    overlay_build(page)

    assert len(page.init_scripts) == 1
    assert 'DOMContentLoaded' in page.init_scripts[0]
    assert '"controls": true' in page.init_scripts[0]


def test_switch_page_installs_init_script_on_new_page() -> None:
    page_first = FakePage()
    page_second = FakePage()
    overlay = overlay_build(page_first)

    overlay.switch_page(page_second.as_page())

    assert len(page_second.init_scripts) == 1


def test_wait_installs_a_missing_control_bar() -> None:
    page = FakePage()
    page.installed = False
    playback = playback_build(page)

    page.control_states = [control_state()]

    playback.wait(100)

    assert page.evaluations[1][1] == {
        'css': OVERLAY_CSS,
        'theme': Theme().payload(),
        'controls': True,
        'speedFactor': 1.0,
        'stepMode': False,
    }


def test_configured_speed_factor_applies_without_a_control_bar() -> None:
    page = FakePage()
    config = DemoConfig(mode='narrate', step_ms=1000, speed_factor=4.0, video=True)
    playback = playback_build(page, config)

    playback.wait(800)

    assert page.waits_ms == [200.0]


def test_configured_speed_factor_seeds_the_install_payload() -> None:
    page = FakePage()
    config = DemoConfig(mode='narrate', step_ms=1000, speed_factor=1000.0)
    playback = playback_build(page, config)

    page.control_states = [control_state(speed_factor=1000.0)]
    page.installed = False

    playback.wait(100)

    assert page.evaluations[1][1] == {
        'css': OVERLAY_CSS,
        'theme': Theme().payload(),
        'controls': True,
        'speedFactor': 1000.0,
        'stepMode': False,
    }


def test_skip_ends_wait_immediately() -> None:
    page = FakePage()
    playback = playback_build(page)

    page.control_states = [control_state(skip=True)]

    playback.wait(1000)

    assert page.waits_ms == []


def test_pause_holds_without_consuming_time() -> None:
    page = FakePage()
    playback = playback_build(page)

    paused = control_state(paused=True)
    running = control_state()

    page.control_states = [paused, paused, running]

    playback.wait(200)

    assert page.waits_ms == [100, 100, 100.0, 100.0]


def test_speed_factor_consumes_time_faster() -> None:
    page = FakePage()
    playback = playback_build(page)

    page.control_states = [control_state(speed_factor=2.0)]

    playback.wait(1000)

    assert page.waits_ms == [100.0, 100.0, 100.0, 100.0, 100.0]


def test_speed_factor_clamped_to_live_maximum() -> None:
    page = FakePage()
    playback = playback_build(page)

    page.control_states = [control_state(speed_factor=20_000.0)]

    playback.wait(8000)

    assert page.waits_ms == [8.0]


def test_missing_control_state_falls_back_to_plain_wait() -> None:
    page = FakePage()
    playback = playback_build(page)

    page.control_states = [None]

    playback.wait(1000)

    assert page.waits_ms == [1000.0]


def test_pause_beyond_cap_raises() -> None:
    page = FakePage()
    playback = playback_build(page)

    page.control_states = [control_state(paused=True)]

    with pytest.raises(TimeoutError, match='paused longer'):
        playback.wait(100)


def test_step_mode_blocks_until_skip() -> None:
    page = FakePage()
    playback = playback_build(page, CONFIG_PRESENT)

    running = control_state()
    skipping = control_state(skip=True)

    page.control_states = [running, running, skipping]

    playback.wait(playback.step_ms_of(None))

    assert page.waits_ms == [100, 100]


def test_step_mode_fades_stay_timed() -> None:
    page = FakePage()
    overlay = overlay_build(page, CONFIG_PRESENT)

    skipping = control_state(skip=True)
    running = control_state()

    page.control_states = [skipping, running]

    overlay.title('Chapter')

    assert sum(page.waits_ms) == 450


def test_paused_control_holds_then_continues() -> None:
    page = FakePage()
    playback = playback_build(page)

    page.control_states = [control_state(paused=True), control_state()]

    playback.wait(100)

    assert page.waits_ms[0] == 100.0
    assert len(page.waits_ms) > 1


def test_skip_ends_the_wait_at_once() -> None:
    page = FakePage()
    playback = playback_build(page)

    page.control_states = [control_state(skip=True)]

    playback.wait(5000)

    assert page.waits_ms == []


def test_a_pause_that_never_lifts_aborts() -> None:
    page = FakePage()
    playback = playback_build(page)

    page.control_states = [control_state(paused=True)]

    with pytest.raises(TimeoutError, match='demo paused longer than'):
        playback.wait(100)


def test_a_step_that_never_advances_aborts() -> None:
    page = FakePage()
    playback = playback_build(page, CONFIG_PRESENT)

    page.control_states = [control_state()]

    with pytest.raises(TimeoutError, match='step wait exceeded'):
        playback.wait(100)


def test_a_step_ends_on_skip() -> None:
    page = FakePage()
    playback = playback_build(page, CONFIG_PRESENT)

    page.control_states = [control_state(skip=True)]

    playback.wait(100)

    assert page.waits_ms == []


def test_a_step_without_a_control_bar_returns() -> None:
    page = FakePage()
    playback = playback_build(page, CONFIG_PRESENT)

    page.control_states = []

    playback.wait(100)

    assert page.waits_ms == []


def test_live_speed_factor_clamps_a_control_bar_extreme() -> None:
    page = FakePage()
    playback = playback_build(page)

    page.control_peeks = [control_state(speed_factor=100000.0)]

    assert playback.speed_factor_live == 1000.0

    page.control_peeks = [control_state(speed_factor=0.0001)]

    assert playback.speed_factor_live == 0.1


def test_live_speed_factor_falls_back_without_a_control_bar() -> None:
    page = FakePage()
    config = DemoConfig(mode='narrate', step_ms=1000, speed_factor=2.0, video=True)
    playback = playback_build(page, config)

    assert playback.speed_factor_live == 2.0
