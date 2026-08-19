from __future__ import annotations

import pytest

from typing_extensions import TYPE_CHECKING, Any

from limelight.config import DemoConfig

if TYPE_CHECKING:
    from collections.abc import Iterator

    from playwright.sync_api import ConsoleMessage, Error, Page


CONSOLE_ERROR_IGNORED_FRAGMENTS: tuple[str, ...] = (
    'TypeError: Failed to fetch',
)

DEVICE_SCALE_FACTOR_VIDEO = 1

ERROR_MESSAGE_COUNT_MAX = 100

VIEWPORT_HEIGHT = 954
VIEWPORT_WIDTH = 1920

VIEWPORT_HEIGHT_VIDEO = 1080
VIEWPORT_WIDTH_VIDEO = 1920


class JavascriptErrorLog:
    def __init__(self, ignored_fragments: tuple[str, ...]) -> None:
        self._console_messages: list[str] = []
        self._ignored_fragments = ignored_fragments
        self._uncaught_messages: list[str] = []

    def _console_watch(self, message: ConsoleMessage) -> None:
        if message.type != 'error':
            return

        location_url = message.location.get('url', '') if message.location else ''
        text = f'{message.text} ({location_url})' if location_url else message.text

        for fragment in self._ignored_fragments:
            if fragment in text:
                return

        self._record(self._console_messages, text)

    def _record(self, messages: list[str], text: str) -> None:
        if len(messages) >= ERROR_MESSAGE_COUNT_MAX:
            return

        messages.append(text)

    def _uncaught_watch(self, error: Error) -> None:
        self._record(self._uncaught_messages, str(error))

    def attach(self, page: Page) -> None:
        page.on('console', self._console_watch)
        page.on('pageerror', self._uncaught_watch)

    def detach(self, page: Page) -> None:
        page.remove_listener('console', self._console_watch)
        page.remove_listener('pageerror', self._uncaught_watch)

    def report(self) -> str:
        lines = [f'uncaught exception: {text}' for text in self._uncaught_messages]
        lines += [f'console.error: {text}' for text in self._console_messages]

        return '\n'.join(lines)


@pytest.fixture(scope='session')
def browser_context_args(
    browser_context_args: dict[str, Any],
    demo_config: DemoConfig,
    demo_viewport: dict[str, int],
    demo_viewport_video: dict[str, int],
) -> dict[str, Any]:
    context_args = {
        **browser_context_args,
        'record_video_size': demo_viewport,
    }

    if demo_config.video:
        record_video_size = {
            'width': demo_viewport_video['width'] * DEVICE_SCALE_FACTOR_VIDEO,
            'height': demo_viewport_video['height'] * DEVICE_SCALE_FACTOR_VIDEO,
        }

        return {**context_args, 'record_video_size': record_video_size}

    if demo_config.narrated:
        return context_args

    return {
        **context_args,
        'no_viewport': False,
        'reduced_motion': 'reduce',
        'viewport': demo_viewport,
    }


@pytest.fixture(scope='session')
def browser_type_launch_args(
    browser_type_launch_args: dict[str, Any],
    demo_config: DemoConfig,
    demo_viewport_video: dict[str, int],
) -> dict[str, Any]:
    if not demo_config.video:
        return browser_type_launch_args

    window_size = f'{demo_viewport_video["width"]},{demo_viewport_video["height"]}'

    launch_args = [
        *browser_type_launch_args.get('args', []),
        f'--force-device-scale-factor={DEVICE_SCALE_FACTOR_VIDEO}',
        f'--window-size={window_size}',
    ]

    return {**browser_type_launch_args, 'args': launch_args}


@pytest.fixture(scope='session')
def demo_config() -> DemoConfig:
    return DemoConfig.from_env()


@pytest.fixture(scope='session')
def demo_console_error_ignored_fragments() -> tuple[str, ...]:
    return CONSOLE_ERROR_IGNORED_FRAGMENTS


@pytest.fixture(scope='session')
def demo_viewport() -> dict[str, int]:
    return {'width': VIEWPORT_WIDTH, 'height': VIEWPORT_HEIGHT}


@pytest.fixture(scope='session')
def demo_viewport_video() -> dict[str, int]:
    return {'width': VIEWPORT_WIDTH_VIDEO, 'height': VIEWPORT_HEIGHT_VIDEO}


@pytest.fixture(autouse=True)
def javascript_error_guard(
    request: pytest.FixtureRequest,
    demo_console_error_ignored_fragments: tuple[str, ...],
) -> Iterator[None]:
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
    config.addinivalue_line(
        'markers',
        'console_error_expected(*fragments): console error fragments this test expects and tolerates',
    )
