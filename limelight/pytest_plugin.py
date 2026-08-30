from __future__ import annotations

import pytest

from typing import TYPE_CHECKING, Any

from limelight.capture.browser import endpoint_free, launch_arguments_frame_control
from limelight.capture.renderer import FrameRenderer, renderer_register, renderer_unregister
from limelight.config import DemoConfig

if TYPE_CHECKING:
    from collections.abc import Iterator

    from playwright.sync_api import ConsoleMessage, Error, Page


CONSOLE_ERROR_IGNORED_FRAGMENTS: tuple[str, ...] = (
    'TypeError: Failed to fetch',
)

ERROR_MESSAGE_COUNT_MAX = 100

SCREENSHOT_MODE_DEFAULT = 'only-on-failure'
TRACING_MODE_DEFAULT = 'retain-on-failure'

VIEWPORT_HEIGHT = 954
VIEWPORT_WIDTH = 1920

VIEWPORT_HEIGHT_VIDEO = 1080
VIEWPORT_WIDTH_VIDEO = 1920

WINDOW_HEIGHT = 1080
WINDOW_WIDTH = 1920


class JavascriptErrorLog:
    """
    A collector for the JavaScript errors a page reports during a test.

    This class listens for console errors and uncaught exceptions. It holds a
    capped number of each, so a page that errors in a loop cannot exhaust memory
    before the test ends.
    """

    def __init__(self, ignored_fragments: tuple[str, ...]) -> None:
        """
        The constructor for the JavascriptErrorLog class.

        :param ignored_fragments: The text of an error that the test tolerates.
        """

        self._console_messages: list[str] = []
        self._ignored_fragments = ignored_fragments
        self._uncaught_messages: list[str] = []

    def _console_watch(self, message: ConsoleMessage) -> None:
        """
        A method that records a console error unless it is tolerated.

        :param message: The console message the page reported.
        """

        if message.type != 'error':
            return

        location_url = message.location.get('url', '') if message.location else ''
        text = f'{message.text} ({location_url})' if location_url else message.text

        for fragment in self._ignored_fragments:
            if fragment in text:
                return

        self._record(self._console_messages, text)

    def _record(self, messages: list[str], text: str) -> None:
        """
        A method that appends a message until the cap is reached.

        :param messages: The list the message is appended to.
        :param text: The message to record.
        """

        if len(messages) >= ERROR_MESSAGE_COUNT_MAX:
            return

        messages.append(text)

    def _uncaught_watch(self, error: Error) -> None:
        """
        A method that records an uncaught exception.

        :param error: The exception the page reported.
        """

        self._record(self._uncaught_messages, str(error))

    def attach(self, page: Page) -> None:
        """
        A method that subscribes the log to the errors of a page.

        :param page: The page the errors are read from.
        """

        page.on('console', self._console_watch)
        page.on('pageerror', self._uncaught_watch)

    def detach(self, page: Page) -> None:
        """
        A method that unsubscribes the log from the errors of a page.

        :param page: The page the log stops reading.
        """

        page.remove_listener('console', self._console_watch)
        page.remove_listener('pageerror', self._uncaught_watch)

    def report(self) -> str:
        """
        A method that renders the collected errors as one report.

        :return: One line per error, with the uncaught exceptions first.
        """

        lines = [f'uncaught exception: {text}' for text in self._uncaught_messages]
        lines += [f'console.error: {text}' for text in self._console_messages]

        return '\n'.join(lines)


def _artifact_option_chosen(config: pytest.Config, name: str) -> bool:
    """
    A function that reports whether an option was given on the command line.

    :param config: The pytest configuration.
    :param name: The name of the option, without its dashes.
    :return: True if the option was given on the command line or in addopts, False otherwise.
    """

    flag = f'--{name}'
    arguments = [*config.invocation_params.args, *config.getini('addopts')]

    return any(argument == flag or argument.startswith(f'{flag}=') for argument in arguments)


def _artifact_option_default(config: pytest.Config, *, name: str, value: str) -> None:
    """
    A function that raises the default of an artifact option.

    The option is only changed while it still holds the value the plugin ships,
    because a value the user chose has to survive: a default that overrode it would
    turn a deliberate off into an artifact written on every run.

    :param config: The pytest configuration.
    :param name: The name of the option, without its dashes.
    :param value: The value the option takes when it was left alone.
    """

    if getattr(config.option, name, None) != 'off':
        return

    if _artifact_option_chosen(config, name):
        return

    setattr(config.option, name, value)


def _browser_context_args_for(
    context_args: dict[str, Any],
    config: DemoConfig,
    *,
    viewport: dict[str, int],
    viewport_video: dict[str, int],
) -> dict[str, Any]:
    """
    A function that builds the browser context arguments for a run.

    A recorded run is pinned to a fixed viewport, because the frames have to share
    one size for the encoder. A narrated run takes the window instead, so the
    presenter sees the browser at whatever size the screen offers. A silent run
    keeps a fixed viewport with animation reduced, since nothing is being watched.

    :param context_args: The arguments the Playwright plugin supplies.
    :param config: The configuration for the run.
    :param viewport: The viewport a silent run uses.
    :param viewport_video: The viewport a recorded run uses.
    :return: The arguments the browser context is opened with.
    """

    if config.video:
        return {
            **context_args,
            'device_scale_factor': config.video_quality.device_scale_factor,
            'no_viewport': False,
            'viewport': viewport_video,
        }

    if config.narrated:
        return {
            **context_args,
            'no_viewport': True,
            'viewport': None,
        }

    return {
        **context_args,
        'no_viewport': False,
        'reduced_motion': 'reduce',
        'viewport': viewport,
    }


def _browser_type_launch_args_for(
    launch_args: dict[str, Any],
    config: DemoConfig,
    endpoint: str,
    *,
    window_size: dict[str, int],
) -> dict[str, Any]:
    """
    A function that builds the browser launch arguments for a run.

    :param launch_args: The arguments the Playwright plugin supplies.
    :param config: The configuration for the run.
    :param endpoint: The URL of the debugging endpoint a recorded run connects over.
    :param window_size: The window size a run that is watched uses.
    :return: The arguments the browser is launched with.
    """

    if config.video:
        arguments_frame_control = launch_arguments_frame_control(
            endpoint,
            device_scale_factor=config.video_quality.device_scale_factor,
        )

        arguments = [*launch_args.get('args', []), *arguments_frame_control]

        return {**launch_args, 'args': arguments, 'headless': True}

    arguments = [
        *launch_args.get('args', []),
        f'--window-size={window_size["width"]},{window_size["height"]}',
    ]

    return {**launch_args, 'args': arguments}


@pytest.fixture(scope='session')
def browser_context_args(
    browser_context_args: dict[str, Any],
    demo_config: DemoConfig,
    demo_viewport: dict[str, int],
    demo_viewport_video: dict[str, int],
) -> dict[str, Any]:
    """
    A fixture that supplies the browser context arguments for the run.

    :param browser_context_args: The arguments the Playwright plugin supplies.
    :param demo_config: The configuration for the run.
    :param demo_viewport: The viewport a silent run uses.
    :param demo_viewport_video: The viewport a recorded run uses.
    :return: The arguments the browser context is opened with.
    """

    return _browser_context_args_for(
        browser_context_args,
        demo_config,
        viewport=demo_viewport,
        viewport_video=demo_viewport_video,
    )


@pytest.fixture(scope='session')
def browser_type_launch_args(
    browser_type_launch_args: dict[str, Any],
    demo_config: DemoConfig,
    demo_frame_endpoint: str,
    demo_window_size: dict[str, int],
) -> dict[str, Any]:
    """
    A fixture that supplies the browser launch arguments for the run.

    :param browser_type_launch_args: The arguments the Playwright plugin supplies.
    :param demo_config: The configuration for the run.
    :param demo_frame_endpoint: The URL of the debugging endpoint a recorded run connects over.
    :param demo_window_size: The window size a run that is watched uses.
    :return: The arguments the browser is launched with.
    """

    return _browser_type_launch_args_for(
        browser_type_launch_args,
        demo_config,
        demo_frame_endpoint,
        window_size=demo_window_size,
    )


@pytest.fixture(scope='session')
def demo_config() -> DemoConfig:
    """
    A fixture that supplies the configuration for the run.

    :return: The configuration described by the environment.
    """

    return DemoConfig.from_env()


@pytest.fixture(scope='session')
def demo_console_error_ignored_fragments(
    demo_console_error_ignored_fragments_extra: tuple[str, ...],
) -> tuple[str, ...]:
    """
    A fixture that supplies the console errors every test tolerates.

    A project adds its own by overriding the extra fragments rather than this
    fixture, so an error the plugin learns to tolerate later is not lost to a
    project that replaced the whole list.

    :param demo_console_error_ignored_fragments_extra: The fragments the project adds.
    :return: The text of an error that is not a failure.
    """

    return CONSOLE_ERROR_IGNORED_FRAGMENTS + demo_console_error_ignored_fragments_extra


@pytest.fixture(scope='session')
def demo_console_error_ignored_fragments_extra() -> tuple[str, ...]:
    """
    A fixture that supplies the console errors this project tolerates.

    The base implementation supplies none, so a project whose pages log an error
    it cannot fix overrides this rather than the list it is added to.

    :return: The text of an error that is not a failure.
    """

    return ()


@pytest.fixture(scope='session')
def demo_frame_endpoint() -> str:
    """
    A fixture that supplies the debugging endpoint a recorded run connects over.

    :return: The URL of the endpoint.
    """

    return endpoint_free()


@pytest.fixture(scope='session')
def demo_viewport() -> dict[str, int]:
    """
    A fixture that supplies the viewport a silent run uses.

    :return: The width and the height of the viewport.
    """

    return {'width': VIEWPORT_WIDTH, 'height': VIEWPORT_HEIGHT}


@pytest.fixture(scope='session')
def demo_viewport_video() -> dict[str, int]:
    """
    A fixture that supplies the viewport a recorded run uses.

    :return: The width and the height of the viewport.
    """

    return {'width': VIEWPORT_WIDTH_VIDEO, 'height': VIEWPORT_HEIGHT_VIDEO}


@pytest.fixture(scope='session')
def demo_window_size() -> dict[str, int]:
    """
    A fixture that supplies the window size a run that is watched uses.

    :return: The width and the height of the window.
    """

    return {'width': WINDOW_WIDTH, 'height': WINDOW_HEIGHT}


@pytest.fixture(autouse=True)
def frame_renderer(
    request: pytest.FixtureRequest,
    demo_config: DemoConfig,
    demo_frame_endpoint: str,
) -> Iterator[FrameRenderer | None]:
    """
    A fixture that runs the frame renderer for a recorded test.

    The renderer is registered against the page so a demo can find it, and stopped
    when the test ends whether it passed or failed, because an encoder left running
    never closes its file.

    :param request: The fixture request for the test.
    :param demo_config: The configuration for the run.
    :param demo_frame_endpoint: The URL of the debugging endpoint the capture connects over.
    :return: The iterator that yields the renderer, or None for a test that records nothing.
    """

    if not demo_config.video:
        yield None

        return

    if 'page' not in request.fixturenames:
        yield None

        return

    page = request.getfixturevalue('page')
    quality = demo_config.video_quality

    renderer = FrameRenderer(
        page,
        endpoint=demo_frame_endpoint,
        fps=quality.fps,
        screenshot_quality=quality.screenshot_quality,
    )

    renderer_register(page, renderer)

    yield renderer

    renderer_unregister(page)
    renderer.stop()


@pytest.fixture(autouse=True)
def javascript_error_guard(
    request: pytest.FixtureRequest,
    demo_console_error_ignored_fragments: tuple[str, ...],
) -> Iterator[None]:
    """
    A fixture that fails a test whose page reported a JavaScript error.

    :param request: The fixture request for the test.
    :param demo_console_error_ignored_fragments: The text of an error that is not a failure.
    :return: The iterator that wraps the test.
    """

    if 'page' not in request.fixturenames:
        yield

        return

    page = request.getfixturevalue('page')

    expected_marker = request.node.get_closest_marker('console_error_expected')
    expected_fragments = tuple(expected_marker.args) if expected_marker else ()

    error_log = JavascriptErrorLog(demo_console_error_ignored_fragments + expected_fragments)
    error_log.attach(page)

    yield

    error_log.detach(page)

    report = error_log.report()

    if report:
        pytest.fail(f'JavaScript errors during test:\n{report}')


def pytest_configure(config: pytest.Config) -> None:
    """
    A function that registers the plugin marker and its artifact defaults.

    Tracing is left off for a recorded run, because the tracer takes its own
    screenshots through the same compositor the renderer is driving frame by frame.

    :param config: The pytest configuration.
    """

    config.addinivalue_line(
        'markers',
        'console_error_expected(*fragments): console error fragments this test tolerates',
    )

    _artifact_option_default(config, name='screenshot', value=SCREENSHOT_MODE_DEFAULT)

    if not DemoConfig.from_env().video:
        _artifact_option_default(config, name='tracing', value=TRACING_MODE_DEFAULT)
