from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self, cast

from playwright.sync_api import Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence
    from pathlib import Path

    from playwright.sync_api import FloatRect, Locator, Page

    from limelight.capture.sinks import VideoSink
    from limelight.ffmpeg import Encoder
    from limelight.ledger import LedgerRow
    from limelight.narrator import Narrator


def fixture_function(fixture: object) -> Any:
    return cast('Any', fixture).__wrapped__


class FakeApplication:
    def __init__(self) -> None:
        self.logins: list[tuple[object, object]] = []
        self.url_requests: list[tuple[str, dict[str, object]]] = []

    def login(self, page: object, user: object) -> None:
        login = (page, user)
        self.logins.append(login)

    def url(self, route: str, **url_kwargs: object) -> str:
        request = (route, url_kwargs)
        self.url_requests.append(request)

        return f'http://stage.test/{route}'


class FakeBarrier:
    def __init__(self, *, succeeds: bool) -> None:
        self._succeeds = succeeds

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exception_info: object) -> bool:
        if not self._succeeds:
            message = 'barrier timeout'
            raise PlaywrightTimeoutError(message)

        return False


class FakeBrowserContext:
    def __init__(self) -> None:
        self.added_cookies: list[Mapping[str, object]] = []
        self.clear_count = 0

    def add_cookies(self, cookies: Sequence[Mapping[str, object]]) -> None:
        self.added_cookies.extend(cookies)

    def clear_cookies(self) -> None:
        self.clear_count += 1


class FakeLocator:
    def __init__(self, boxes: Sequence[Mapping[str, float] | None] | None = None) -> None:
        self.boxes: list[Mapping[str, float] | None] = list(boxes or [])
        self.check_count = 0
        self.checked: bool | None = None
        self.click_count = 0
        self.fill_values: list[str] = []
        self.hover_count = 0
        self.input_type = 'text'
        self.label = ''
        self.option_labels: list[str] = []
        self.point_hits = True
        self.pressed_keys: list[str] = []
        self.scroll_timeouts: list[int] = []
        self.select_labels: list[str] = []
        self.typed_sequences: list[tuple[str, float]] = []
        self.uncheck_count = 0

    def as_locator(self) -> Locator:
        return cast('Locator', self)

    def bounding_box(self, *, timeout: float | None = None) -> FloatRect | None:
        if not self.boxes:
            return None

        box = self.boxes[0] if len(self.boxes) == 1 else self.boxes.pop(0)

        return cast('FloatRect | None', box)

    def check(self) -> None:
        self.check_count += 1

    def click(self, *, force: bool = False) -> None:
        self.click_count += 1

    def evaluate(
        self,
        expression: str,
        argument: object = None,
        *,
        timeout: float | None = None,
    ) -> object:
        if 'elementFromPoint' in expression:
            return self.point_hits

        if 'options' in expression:
            return self.option_labels

        if 'tagName' in expression:
            return self.input_type

        return self.label

    def fill(self, value: str) -> None:
        self.fill_values.append(value)

    def hover(self) -> None:
        self.hover_count += 1

    def is_checked(self) -> bool:
        if self.checked is None:
            message = 'not a checkbox'
            raise PlaywrightError(message)

        return self.checked

    def press(self, key: str) -> None:
        self.pressed_keys.append(key)

    def press_sequentially(self, value: str, *, delay: float = 0) -> None:
        sequence = (value, delay)
        self.typed_sequences.append(sequence)

    def scroll_into_view_if_needed(self, timeout: int) -> None:
        self.scroll_timeouts.append(timeout)

    def select_option(self, *, label: str) -> None:
        self.select_labels.append(label)

    def uncheck(self) -> None:
        self.uncheck_count += 1


class FakeMouse:
    def __init__(self) -> None:
        self.actions: list[tuple[object, ...]] = []

    def down(self) -> None:
        self.actions.append(('down',))

    def move(self, x: float, y: float, steps: int = 1) -> None:
        self.actions.append(('move', x, y, steps))

    def up(self) -> None:
        self.actions.append(('up',))


class FakePage:
    def __init__(self) -> None:
        self.context = FakeBrowserContext()
        self.control_peeks: list[Mapping[str, object] | None] = []
        self.control_states: list[Mapping[str, object] | None] = []
        self.evaluations: list[tuple[str, object]] = []
        self.goto_urls: list[str] = []
        self.init_scripts: list[str] = []
        self.installed = True
        self.listeners: dict[str, list[object]] = {}
        self.load_states: list[str] = []
        self.locator_box: Mapping[str, float] = {'x': 0, 'y': 0, 'width': 100, 'height': 20}
        self.locator_locators: list[FakeLocator] = []
        self.locator_selectors: list[str] = []
        self.mouse = FakeMouse()
        self.navigation_error_count = 0
        self.navigation_outcomes: list[bool] = []
        self.response_outcomes: list[bool] = []
        self.response_predicates: list[object] = []
        self.role_locators: list[FakeLocator] = []
        self.role_queries: list[tuple[str, str | None, bool]] = []
        self.screenshot_paths: list[str] = []
        self.selector_waits: list[tuple[str, str]] = []
        self.url = 'http://stage.test/current'
        self.waits_ms: list[float] = []

    def _control_peek_next(self) -> Mapping[str, object] | None:
        if not self.control_peeks:
            return self.control_states[0] if self.control_states else None

        if len(self.control_peeks) == 1:
            return self.control_peeks[0]

        return self.control_peeks.pop(0)

    def _control_state_next(self) -> Mapping[str, object] | None:
        if not self.control_states:
            return None

        if len(self.control_states) == 1:
            return self.control_states[0]

        return self.control_states.pop(0)

    def _function_result(self, expression: str) -> object:
        if 'selectShow(' in expression:
            return {'x': 30.0, 'y': 60.0}

        if 'controlPeek(' in expression:
            return self._control_peek_next()

        if 'controlRead(' in expression:
            return self._control_state_next()

        return None

    def add_init_script(self, script: str) -> None:
        self.init_scripts.append(script)

    def as_page(self) -> Page:
        return cast('Page', self)

    def evaluate(self, expression: str, argument: object = None) -> object:
        evaluation = (expression, argument)
        self.evaluations.append(evaluation)

        if self.navigation_error_count > 0:
            self.navigation_error_count -= 1

            message = 'Execution context was destroyed, most likely because of a navigation'
            raise PlaywrightError(message)

        if expression.startswith('(config) =>'):
            self.installed = True

            return None

        if not self.installed:
            return None

        return {'result': self._function_result(expression)}

    def expect_navigation(self, *, url: object = None, timeout: int | None = None) -> FakeBarrier:
        succeeds = self.navigation_outcomes.pop(0) if self.navigation_outcomes else True

        return FakeBarrier(succeeds=succeeds)

    def expect_response(self, predicate: object, *, timeout: int | None = None) -> FakeBarrier:
        self.response_predicates.append(predicate)

        succeeds = self.response_outcomes.pop(0) if self.response_outcomes else True

        return FakeBarrier(succeeds=succeeds)

    def get_by_role(
        self,
        role: str,
        *,
        name: str | None = None,
        exact: bool = False,
    ) -> FakeLocator:
        query = (role, name, exact)
        self.role_queries.append(query)

        locator = FakeLocator()
        self.role_locators.append(locator)

        return locator

    def goto(self, url: str) -> None:
        self.goto_urls.append(url)

    def locator(self, selector: str) -> FakeLocator:
        self.locator_selectors.append(selector)

        boxes = [self.locator_box]
        locator = FakeLocator(boxes=boxes)

        self.locator_locators.append(locator)

        return locator

    def screenshot(self, *, path: str) -> None:
        self.screenshot_paths.append(path)

    def emit(self, event: str, payload: object) -> None:
        for handler in self.listeners.get(event, []):
            cast('Callable[[object], None]', handler)(payload)

    def on(self, event: str, handler: object) -> None:
        self.listeners.setdefault(event, []).append(handler)

    def remove_listener(self, event: str, handler: object) -> None:
        self.listeners.get(event, []).remove(handler)

    def wait_for_load_state(self, state: str, *, timeout: float | None = None) -> None:
        self.load_states.append(state)

    def wait_for_selector(self, selector: str, *, state: str = '') -> None:
        wait = (selector, state)
        self.selector_waits.append(wait)

    def wait_for_timeout(self, ms: float) -> None:
        self.waits_ms.append(ms)



class FakeNarrator:
    def __init__(self, screenshot_path: Path | None = None) -> None:
        self.calls: list[tuple[object, ...]] = []
        self.screenshot_path = screenshot_path

    def as_narrator(self) -> Narrator:
        return cast('Narrator', self)

    def check(self, locator: Locator) -> None:
        self.calls.append(('check', locator))

    def click(self, locator: Locator, *, force: bool = False) -> None:
        self.calls.append(('click', locator, force))

    def fill(self, locator: Locator, value: str) -> None:
        self.calls.append(('fill', locator, value))

    def hover(self, locator: Locator) -> None:
        self.calls.append(('hover', locator))

    def metrics(
        self,
        title: str,
        rows: list[LedgerRow],
        *,
        kicker: str = '',
        subtitle: str = '',
        ms: int | None = None,
    ) -> None:
        self.calls.append(('metrics', title, rows, kicker, subtitle, ms))

    def narrate(
        self,
        title: str,
        *,
        body: str = '',
        step: str = '',
        ms: int | None = None,
    ) -> None:
        self.calls.append(('narrate', title, body, step, ms))

    def pause(self, ms: int | None = None) -> None:
        self.calls.append(('pause', ms))

    def press(self, locator: Locator, key: str) -> None:
        self.calls.append(('press', locator, key))

    def screenshot(self, name: str) -> Path | None:
        self.calls.append(('screenshot', name))

        return self.screenshot_path

    def select(self, locator: Locator, option_label: str) -> None:
        self.calls.append(('select', locator, option_label))

    def slide(self, *, track: Locator, thumb: Locator) -> None:
        self.calls.append(('slide', track, thumb))

    def spotlight(
        self,
        locator: Locator,
        *,
        label: str = '',
        dim: bool = True,
        scroll: bool = True,
        ms: int | None = None,
    ) -> None:
        self.calls.append(('spotlight', locator, label, dim, scroll, ms))

    def switch_page(self, page: Page) -> None:
        self.calls.append(('switch_page', page))

    def title(
        self,
        text: str,
        *,
        kicker: str = '',
        subtitle: str = '',
        ms: int | None = None,
    ) -> None:
        self.calls.append(('title', text, kicker, subtitle, ms))

    def uncheck(self, locator: Locator) -> None:
        self.calls.append(('uncheck', locator))

    def wait(self, ms: int) -> None:
        self.calls.append(('wait', ms))


class FakeEncoder:
    def __init__(self) -> None:
        self.pipes: list[list[str]] = []
        self.process = FakeProcess()
        self.runs: list[list[str]] = []

    def as_encoder(self) -> Encoder:
        return cast('Encoder', self)

    def pipe(self, arguments: list[str]) -> FakeProcess:
        self.pipes.append(arguments)

        return self.process

    def run(self, arguments: list[str]) -> None:
        self.runs.append(arguments)


class FakeProcess:
    def __init__(self) -> None:
        self.stdin = FakeStdin()
        self.returncode = 0

    def wait(self, timeout: float | None = None) -> int:
        return self.returncode


class FakeStdin:
    def __init__(self) -> None:
        self.closed = False
        self.written: list[bytes] = []

    def close(self) -> None:
        self.closed = True

    def write(self, data: bytes) -> None:
        self.written.append(data)


class FakeClock:
    def __init__(self) -> None:
        self.waits_ms: list[float] = []

    def wait_ms(self, ms: float) -> None:
        self.waits_ms.append(ms)


class FakeFrameRenderer:
    def __init__(self, *, fps: int = 60) -> None:
        self.fps = fps
        self.page_switches: list[object] = []
        self.sinks: list[VideoSink] = []
        self.stopped = False
        self.waits_ms: list[float] = []

    def start(self, sink: VideoSink) -> None:
        self.sinks.append(sink)

    def stop(self) -> None:
        self.stopped = True

    def switch_page(self, page: object) -> None:
        self.page_switches.append(page)

    def wait_ms(self, ms: float) -> None:
        self.waits_ms.append(ms)
