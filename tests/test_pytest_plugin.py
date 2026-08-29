from __future__ import annotations

import pytest

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

from limelight import pytest_plugin
from limelight.capture.renderer import renderer_for
from limelight.config import DEMO_MODE_NARRATE, DemoConfig

from fakes import FakePage, fixture_function

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


def config_build(
    *,
    addopts: tuple[str, ...] = (),
    arguments: tuple[str, ...] = (),
    **options: str,
) -> Any:
    return SimpleNamespace(
        addinivalue_line=lambda name, line: None,
        getini=lambda name: list(addopts),
        invocation_params=SimpleNamespace(args=list(arguments)),
        option=SimpleNamespace(**options),
    )


def test_artifact_option_default_fills_in_an_unset_option() -> None:
    config = config_build(screenshot='off')

    pytest_plugin._artifact_option_default(config, name='screenshot', value='only-on-failure')

    assert config.option.screenshot == 'only-on-failure'


def test_artifact_option_default_keeps_a_chosen_option() -> None:
    config = config_build(screenshot='on')

    pytest_plugin._artifact_option_default(config, name='screenshot', value='only-on-failure')

    assert config.option.screenshot == 'on'


def test_artifact_option_default_keeps_an_off_chosen_on_the_command_line() -> None:
    config = config_build(arguments=('--tracing=off',), tracing='off')

    pytest_plugin._artifact_option_default(config, name='tracing', value='retain-on-failure')

    assert config.option.tracing == 'off'


def test_artifact_option_default_keeps_an_off_chosen_in_addopts() -> None:
    config = config_build(addopts=('--tracing', 'off'), tracing='off')

    pytest_plugin._artifact_option_default(config, name='tracing', value='retain-on-failure')

    assert config.option.tracing == 'off'


def test_artifact_option_default_ignores_an_absent_option() -> None:
    config = config_build()

    pytest_plugin._artifact_option_default(config, name='tracing', value='retain-on-failure')

    assert not hasattr(config.option, 'tracing')


def test_configure_defaults_the_failure_artifacts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv('DEMO_MODE', raising=False)
    monkeypatch.delenv('DEMO_VIDEO', raising=False)

    config = config_build(screenshot='off', tracing='off')

    pytest_plugin.pytest_configure(config)

    assert config.option.screenshot == 'only-on-failure'
    assert config.option.tracing == 'retain-on-failure'


def test_configure_leaves_tracing_off_for_video(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('DEMO_MODE', DEMO_MODE_NARRATE)
    monkeypatch.setenv('DEMO_VIDEO', '1')

    config = config_build(screenshot='off', tracing='off')

    pytest_plugin.pytest_configure(config)

    assert config.option.screenshot == 'only-on-failure'
    assert config.option.tracing == 'off'


class FakeConsoleMessage:
    def __init__(self, text: str, *, kind: str = 'error', url: str = '') -> None:
        self.location = {'url': url} if url else {}
        self.text = text
        self.type = kind


class FakeNode:
    def __init__(self, marker: object = None) -> None:
        self._marker = marker

    def get_closest_marker(self, name: str) -> object:
        _ = name

        return self._marker


class FakeRequest:
    def __init__(self, page: FakePage | None = None, *, marker: object = None) -> None:
        self._page = page
        self.fixturenames = ['page'] if page is not None else []
        self.node = FakeNode(marker)

    def getfixturevalue(self, name: str) -> object:
        _ = name

        return None if self._page is None else self._page.as_page()


def error_log_build(*ignored: str) -> pytest_plugin.JavascriptErrorLog:
    return pytest_plugin.JavascriptErrorLog(ignored)


def test_console_error_is_recorded_with_its_location() -> None:
    page = FakePage()
    error_log = error_log_build()

    error_log.attach(page.as_page())
    page.emit('console', FakeConsoleMessage('boom', url='http://stage.test/app.js'))

    assert error_log.report() == 'console.error: boom (http://stage.test/app.js)'


def test_console_error_without_a_location_reads_plainly() -> None:
    page = FakePage()
    error_log = error_log_build()

    error_log.attach(page.as_page())
    page.emit('console', FakeConsoleMessage('boom'))

    assert error_log.report() == 'console.error: boom'


def test_console_message_that_is_not_an_error_is_ignored() -> None:
    page = FakePage()
    error_log = error_log_build()

    error_log.attach(page.as_page())
    page.emit('console', FakeConsoleMessage('chatter', kind='log'))

    assert error_log.report() == ''


def test_ignored_fragment_drops_a_console_error() -> None:
    page = FakePage()
    error_log = error_log_build('Failed to fetch')

    error_log.attach(page.as_page())
    page.emit('console', FakeConsoleMessage('TypeError: Failed to fetch'))

    assert error_log.report() == ''


def test_uncaught_error_is_reported_before_console_errors() -> None:
    page = FakePage()
    error_log = error_log_build()

    error_log.attach(page.as_page())
    page.emit('console', FakeConsoleMessage('second'))
    page.emit('pageerror', 'first')

    assert error_log.report() == 'uncaught exception: first\nconsole.error: second'


def test_error_messages_stop_accumulating_at_the_cap() -> None:
    page = FakePage()
    error_log = error_log_build()

    error_log.attach(page.as_page())

    for index in range(pytest_plugin.ERROR_MESSAGE_COUNT_MAX + 10):
        page.emit('console', FakeConsoleMessage(f'boom {index}'))

    assert len(error_log.report().splitlines()) == pytest_plugin.ERROR_MESSAGE_COUNT_MAX


def test_detach_stops_the_recording() -> None:
    page = FakePage()
    error_log = error_log_build()

    error_log.attach(page.as_page())
    error_log.detach(page.as_page())
    page.emit('console', FakeConsoleMessage('boom'))

    assert error_log.report() == ''
    assert page.listeners == {'console': [], 'pageerror': []}


def test_error_guard_fails_a_test_that_logged_an_error() -> None:
    page = FakePage()
    error_guard = fixture_function(pytest_plugin.javascript_error_guard)
    guard = error_guard(cast('Any', FakeRequest(page)), ())

    next(guard)

    page.emit('console', FakeConsoleMessage('boom'))

    with pytest.raises(pytest.fail.Exception, match='JavaScript errors during test'):
        next(guard, None)


def test_error_guard_tolerates_a_fragment_the_marker_names() -> None:
    page = FakePage()
    marker = SimpleNamespace(args=('boom',))
    request = FakeRequest(page, marker=marker)
    error_guard = fixture_function(pytest_plugin.javascript_error_guard)
    guard = error_guard(cast('Any', request), ())

    next(guard)

    page.emit('console', FakeConsoleMessage('boom'))

    assert next(guard, None) is None


def test_error_guard_stands_aside_without_a_page() -> None:
    error_guard = fixture_function(pytest_plugin.javascript_error_guard)
    guard = error_guard(cast('Any', FakeRequest()), ())

    next(guard)

    assert next(guard, None) is None


def test_frame_renderer_stands_aside_outside_video() -> None:
    fixture = fixture_function(pytest_plugin.frame_renderer)
    renderer = fixture(cast('Any', FakeRequest(FakePage())), DemoConfig(), 'ws://localhost:1')

    assert next(renderer) is None
    assert next(renderer, 'exhausted') == 'exhausted'


def test_frame_renderer_stands_aside_without_a_page() -> None:
    fixture = fixture_function(pytest_plugin.frame_renderer)
    config = DemoConfig(mode=DEMO_MODE_NARRATE, video=True)
    renderer = fixture(cast('Any', FakeRequest()), config, 'ws://localhost:1')

    assert next(renderer) is None
    assert next(renderer, 'exhausted') == 'exhausted'


def test_frame_renderer_registers_then_unregisters_for_the_page() -> None:
    page = FakePage()
    fixture = fixture_function(pytest_plugin.frame_renderer)
    config = DemoConfig(mode=DEMO_MODE_NARRATE, video=True)
    generator = fixture(cast('Any', FakeRequest(page)), config, 'ws://localhost:1')

    renderer = next(generator)

    assert renderer is not None
    assert renderer_for(page.as_page()) is renderer

    assert next(generator, 'exhausted') == 'exhausted'

    with pytest.raises(LookupError):
        renderer_for(page.as_page())


def test_the_session_fixtures_carry_the_defaults() -> None:
    assert fixture_function(pytest_plugin.demo_config)() == DemoConfig.from_env()
    assert fixture_function(pytest_plugin.demo_console_error_ignored_fragments)() == (
        pytest_plugin.CONSOLE_ERROR_IGNORED_FRAGMENTS
    )
    assert fixture_function(pytest_plugin.demo_viewport)() == {'width': 1920, 'height': 954}
    assert fixture_function(pytest_plugin.demo_viewport_video)() == {'width': 1920, 'height': 1080}
    assert fixture_function(pytest_plugin.demo_window_size)() == {'width': 1920, 'height': 1080}


def test_the_frame_endpoint_fixture_offers_a_free_port() -> None:
    endpoint = fixture_function(pytest_plugin.demo_frame_endpoint)()

    assert endpoint.startswith('http://127.0.0.1:')


def test_the_context_fixture_sizes_the_viewport_for_video() -> None:
    context_args = fixture_function(pytest_plugin.browser_context_args)
    config = DemoConfig(mode=DEMO_MODE_NARRATE, quality='high', video=True)

    result = context_args({}, config, {'width': 1, 'height': 2}, {'width': 3, 'height': 4})

    assert result == {
        'device_scale_factor': 2,
        'no_viewport': False,
        'viewport': {'width': 3, 'height': 4},
    }


def test_the_launch_fixture_adds_the_window_size() -> None:
    launch_args = fixture_function(pytest_plugin.browser_type_launch_args)

    result = launch_args({}, DemoConfig(), 'ws://localhost:1', {'width': 800, 'height': 600})

    assert result == {'args': ['--window-size=800,600']}


def test_the_context_scales_the_capture_to_the_quality() -> None:
    config = DemoConfig(mode=DEMO_MODE_NARRATE, quality='low', video=True)

    result = pytest_plugin._browser_context_args_for(
        {},
        config,
        viewport=WINDOW_SIZE,
        viewport_video=WINDOW_SIZE,
    )

    assert result['device_scale_factor'] == 1


def test_the_launch_arguments_scale_the_capture_to_the_quality() -> None:
    config = DemoConfig(mode=DEMO_MODE_NARRATE, quality='low', video=True)

    result = pytest_plugin._browser_type_launch_args_for(
        {},
        config,
        'ws://localhost:1',
        window_size=WINDOW_SIZE,
    )

    assert '--force-device-scale-factor=1' in result['args']


def test_the_frame_renderer_takes_the_quality_settings() -> None:
    page = FakePage()
    fixture = fixture_function(pytest_plugin.frame_renderer)
    config = DemoConfig(mode=DEMO_MODE_NARRATE, quality='low', video=True)
    generator = fixture(cast('Any', FakeRequest(page)), config, 'ws://localhost:1')

    renderer = next(generator)

    assert renderer is not None
    assert renderer.fps == 24
    assert renderer._screenshot == {'format': 'jpeg', 'quality': 75}

    next(generator, None)
