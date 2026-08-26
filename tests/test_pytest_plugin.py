from __future__ import annotations

from typing import TYPE_CHECKING

from limelight import pytest_plugin
from limelight.config import DEMO_MODE_NARRATE, DemoConfig

if TYPE_CHECKING:
    from typing import Any


WINDOW_SIZE = {'width': 1280, 'height': 720}


def test_launch_args_append_the_window_size_outside_video() -> None:
    launch_args: dict[str, Any] = {}

    result = pytest_plugin._browser_type_launch_args_for(
        launch_args,
        DemoConfig(),
        'ws://localhost:1',
        window_size=WINDOW_SIZE,
    )

    assert result == {'args': ['--window-size=1280,720']}


def test_launch_args_keep_existing_arguments() -> None:
    launch_args: dict[str, Any] = {'args': ['--mute-audio']}

    result = pytest_plugin._browser_type_launch_args_for(
        launch_args,
        DemoConfig(),
        'ws://localhost:1',
        window_size=WINDOW_SIZE,
    )

    assert result['args'] == ['--mute-audio', '--window-size=1280,720']


def test_launch_args_use_frame_control_in_video_mode() -> None:
    launch_args: dict[str, Any] = {}
    config = DemoConfig(mode=DEMO_MODE_NARRATE, video=True)

    result = pytest_plugin._browser_type_launch_args_for(
        launch_args,
        config,
        'ws://localhost:1',
        window_size=WINDOW_SIZE,
    )

    assert result['headless'] is True
    assert '--window-size=1280,720' not in result['args']


def test_window_size_default_is_full_hd() -> None:
    assert pytest_plugin.WINDOW_WIDTH == 1920
    assert pytest_plugin.WINDOW_HEIGHT == 1080


def test_narrated_context_fills_the_window() -> None:
    config = DemoConfig(mode=DEMO_MODE_NARRATE)

    result = pytest_plugin._browser_context_args_for(
        {},
        config,
        viewport=WINDOW_SIZE,
        viewport_video=WINDOW_SIZE,
    )

    assert result == {'no_viewport': True, 'viewport': None}


def test_silent_context_pins_the_viewport() -> None:
    result = pytest_plugin._browser_context_args_for(
        {},
        DemoConfig(),
        viewport=WINDOW_SIZE,
        viewport_video=WINDOW_SIZE,
    )

    assert result['no_viewport'] is False
    assert result['viewport'] == WINDOW_SIZE
    assert result['reduced_motion'] == 'reduce'
