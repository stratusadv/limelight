from __future__ import annotations

import pytest

from typing import TYPE_CHECKING, cast

from limelight.config import DEMO_MODE_NARRATE, DEMO_MODE_PRESENT, DemoConfig
from limelight.overlay import Overlay
from limelight.presenter import presenter_build
from limelight.timing import DemoTiming

from fakes import FakeFrameRenderer, FakePage

if TYPE_CHECKING:
    from pathlib import Path

    from limelight.frames import FrameRenderer


def control_state(*, paused: bool = False, skip: bool = False, speed_factor: float = 1.0) -> dict[str, object]:
    return {'paused': paused, 'skip': skip, 'speedFactor': speed_factor}


def overlay_build(page: FakePage) -> Overlay:
    return Overlay(page.as_page(), DemoTiming(step_ms=1000), controls=True)


def test_controls_disabled_waits_in_one_piece() -> None:
    page = FakePage()
    overlay = Overlay(page.as_page(), DemoTiming(step_ms=1000), controls=False)

    overlay.beat(500)

    assert page.waits_ms == [500.0]


def test_overlay_installs_itself_as_init_script() -> None:
    page = FakePage()

    overlay_build(page)

    assert len(page.init_scripts) == 1
    assert 'DOMContentLoaded' in page.init_scripts[0]
    assert '"controls": true' in page.init_scripts[0]


def test_use_page_installs_init_script_on_new_page() -> None:
    page_first = FakePage()
    page_second = FakePage()
    overlay = overlay_build(page_first)

    overlay.use_page(page_second.as_page())

    assert len(page_second.init_scripts) == 1


def test_wait_installs_control_bar() -> None:
    page = FakePage()
    overlay = overlay_build(page)

    page.control_states = [control_state()]

    overlay.beat(100)

    assert page.evaluations[0][1] == {
        'theme': overlay._theme.payload(),
        'controls': True,
        'speedFactor': 1.0,
        'stepMode': False,
    }


def test_configured_speed_factor_applies_without_a_control_bar() -> None:
    page = FakePage()
    overlay = Overlay(page.as_page(), DemoTiming(step_ms=1000), controls=False, speed_factor=4.0)

    overlay.beat(800)

    assert page.waits_ms == [200.0]


def test_configured_speed_factor_seeds_the_install_payload() -> None:
    page = FakePage()
    overlay = Overlay(page.as_page(), DemoTiming(step_ms=1000), controls=True, speed_factor=1000.0)

    page.control_states = [control_state(speed_factor=1000.0)]

    overlay.beat(100)

    assert page.evaluations[0][1] == {
        'theme': overlay._theme.payload(),
        'controls': True,
        'speedFactor': 1000.0,
        'stepMode': False,
    }


def test_speed_factor_zero_rejected() -> None:
    page = FakePage()

    with pytest.raises(ValueError, match='speed_factor'):
        Overlay(page.as_page(), DemoTiming(step_ms=1000), speed_factor=0)


def test_skip_ends_wait_immediately() -> None:
    page = FakePage()
    overlay = overlay_build(page)

    page.control_states = [control_state(skip=True)]

    overlay.beat(1000)

    assert page.waits_ms == []


def test_pause_holds_without_consuming_time() -> None:
    page = FakePage()
    overlay = overlay_build(page)

    paused = control_state(paused=True)
    running = control_state()

    page.control_states = [paused, paused, running]

    overlay.beat(200)

    assert page.waits_ms == [100, 100, 100.0, 100.0]


def test_speed_factor_consumes_time_faster() -> None:
    page = FakePage()
    overlay = overlay_build(page)

    page.control_states = [control_state(speed_factor=2.0)]

    overlay.beat(1000)

    assert page.waits_ms == [100.0, 100.0, 100.0, 100.0, 100.0]


def test_speed_factor_clamped_to_live_maximum() -> None:
    page = FakePage()
    overlay = overlay_build(page)

    page.control_states = [control_state(speed_factor=20_000.0)]

    overlay.beat(8000)

    assert page.waits_ms == [8.0]


def test_uninstalled_overlay_falls_back_to_plain_wait() -> None:
    page = FakePage()
    overlay = overlay_build(page)

    page.control_states = [None]

    overlay.beat(1000)

    assert page.waits_ms == [1000.0]


def test_pause_beyond_cap_raises() -> None:
    page = FakePage()
    overlay = overlay_build(page)

    page.control_states = [control_state(paused=True)]

    with pytest.raises(TimeoutError, match='paused longer'):
        overlay.beat(100)


def test_step_mode_requires_controls() -> None:
    with pytest.raises(ValueError, match='step_mode'):
        Overlay(FakePage().as_page(), DemoTiming(step_ms=1000), step_mode=True)


def test_step_mode_blocks_until_skip() -> None:
    page = FakePage()
    overlay = Overlay(page.as_page(), DemoTiming(step_ms=1000), controls=True, step_mode=True)

    running = control_state()
    skipping = control_state(skip=True)

    page.control_states = [running, running, skipping]

    overlay.hold()

    assert page.waits_ms == [100, 100]


def test_step_mode_fades_stay_timed() -> None:
    page = FakePage()
    overlay = Overlay(page.as_page(), DemoTiming(step_ms=1000), controls=True, step_mode=True)

    skipping = control_state(skip=True)
    running = control_state()

    page.control_states = [skipping, running]

    overlay.title_card('Chapter')

    assert sum(page.waits_ms) == 450


def test_present_config_installs_step_mode(tmp_path: Path) -> None:
    page = FakePage()
    config = DemoConfig(mode=DEMO_MODE_PRESENT)

    presenter_build(page.as_page(), config, shot_directory=tmp_path / 'shots')

    assert '"stepMode": true' in page.init_scripts[0]


def test_video_mode_disables_controls(tmp_path: Path) -> None:
    page = FakePage()
    config = DemoConfig(mode=DEMO_MODE_NARRATE, video=True)
    renderer = cast('FrameRenderer', FakeFrameRenderer())

    presenter_build(page.as_page(), config, shot_directory=tmp_path / 'shots', renderer=renderer)

    assert '"controls": false' in page.init_scripts[0]


def test_narrated_mode_enables_controls(tmp_path: Path) -> None:
    page = FakePage()
    config = DemoConfig(mode=DEMO_MODE_NARRATE)

    presenter_build(page.as_page(), config, shot_directory=tmp_path / 'shots')

    assert '"controls": true' in page.init_scripts[0]


def test_shot_hides_control_bar_around_screenshot(tmp_path: Path) -> None:
    page = FakePage()
    config = DemoConfig(mode=DEMO_MODE_NARRATE, shots=True)

    presenter = presenter_build(page.as_page(), config, shot_directory=tmp_path / 'shots')
    presenter.shot('welcome')

    expressions = [expression for expression, _ in page.evaluations]

    assert any('controlHide' in expression for expression in expressions)
    assert any('controlShow' in expression for expression in expressions)
    assert len(page.screenshot_paths) == 1
