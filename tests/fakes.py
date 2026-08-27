from __future__ import annotations

from typing import TYPE_CHECKING, Self, cast

from playwright.sync_api import Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from playwright.sync_api import FloatRect, Locator, Page

    from limelight.frames import VideoSink
    from limelight.ledger import LedgerRow


class FakeApplication:
    def __init__(self, user: object = None) -> None:
        self.login_pages: list[object] = []
        self.url_requests: list[tuple[str, dict[str, object]]] = []
        self.user = user

    def login(self, page: object) -> None:
        self.login_pages.append(page)

    def url(self, route: str, url_kwargs: dict[str, object]) -> str:
        request = (route, url_kwargs)
        self.url_requests.append(request)

        return f'http://stage.test/{route}'

    def with_user(self, user: object) -> FakeApplication:
        return FakeApplication(user)


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
        self.children: list[FakeLocator] = []
        self.click_count = 0
        self.click_forces: list[bool] = []
        self.checked: bool | None = None
        self.evaluate_error: Exception | None = None
        self.evaluate_timeouts: list[float | None] = []
        self.fill_values: list[str] = []
        self.filter_haves: list[object] = []
        self.filter_texts: list[str | None] = []
        self.filter_visibles: list[bool | None] = []
        self.hover_count = 0
        self.input_type = 'text'
        self.label = ''
        self.option_labels: list[str] = []
        self.owner_page = FakePage()
        self.placeholder_queries: list[str] = []
        self.point_hits = True
        self.pressed_keys: list[str] = []
        self.scroll_timeouts: list[int] = []
        self.select_labels: list[str] = []
        self.selector_queries: list[str] = []
        self.text_queries: list[tuple[str, bool]] = []
        self.typed_sequences: list[tuple[str, float]] = []
        self.uncheck_count = 0

    def _child(self) -> FakeLocator:
        child = FakeLocator()
        self.children.append(child)

        return child

    @property
    def first(self) -> FakeLocator:
        return self

    @property
    def last(self) -> FakeLocator:
        return self

    @property
    def page(self) -> Page:
        return self.owner_page.as_page()

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
        self.click_forces.append(force)

    def evaluate(
        self,
        expression: str,
        argument: object = None,
        *,
        timeout: float | None = None,
    ) -> object:
        self.evaluate_timeouts.append(timeout)

        if self.evaluate_error is not None:
            raise self.evaluate_error

        if 'elementFromPoint' in expression:
            return self.point_hits

        if 'options' in expression:
            return self.option_labels

        if 'tagName' in expression:
            return self.input_type

        return self.label

    def fill(self, value: str) -> None:
        self.fill_values.append(value)

    def filter(
        self,
        *,
        has: object = None,
        has_text: str | None = None,
        visible: bool | None = None,
    ) -> FakeLocator:
        self.filter_haves.append(has)
        self.filter_texts.append(has_text)
        self.filter_visibles.append(visible)

        return self

    def get_by_placeholder(self, text: str) -> FakeLocator:
        self.placeholder_queries.append(text)

        return self._child()

    def get_by_text(self, text: str, *, exact: bool = False) -> FakeLocator:
        query = (text, exact)
        self.text_queries.append(query)

        return FakeLocator()

    def hover(self) -> None:
        self.hover_count += 1

    def is_checked(self) -> bool:
        if self.checked is None:
            message = 'not a checkbox'
            raise PlaywrightError(message)

        return self.checked

    def locator(self, selector: str) -> FakeLocator:
        self.selector_queries.append(selector)

        return self._child()

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


class FakeDemo:
    def __init__(self, page: FakePage | None = None) -> None:
        self.clicked: list[tuple[object, bool]] = []
        self.filled: list[tuple[object, str]] = []
        self.owner_page = page if page is not None else FakePage()
        self.slid: list[tuple[object, object]] = []

    @property
    def page(self) -> Page:
        return self.owner_page.as_page()

    def as_session(self) -> object:
        return self

    def click(self, locator: object, *, force: bool = False) -> None:
        click = (locator, force)
        self.clicked.append(click)

    def fill(self, locator: object, value: str) -> None:
        fill = (locator, value)
        self.filled.append(fill)

    def slide(self, *, track: object, thumb: object) -> None:
        slide = (track, thumb)
        self.slid.append(slide)


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
        self.load_states: list[str] = []
        self.locator_box: Mapping[str, float] = {'x': 0, 'y': 0, 'width': 100, 'height': 20}
        self.locator_evaluate_error: Exception | None = None
        self.locator_locators: list[FakeLocator] = []
        self.locator_selectors: list[str] = []
        self.mouse = FakeMouse()
        self.navigation_outcomes: list[bool] = []
        self.response_outcomes: list[bool] = []
        self.role_locators: list[FakeLocator] = []
        self.role_queries: list[tuple[str, str | None, bool]] = []
        self.screenshot_paths: list[str] = []
        self.selector_waits: list[tuple[str, str]] = []
        self.text_queries: list[tuple[str, bool]] = []
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

    def add_init_script(self, script: str) -> None:
        self.init_scripts.append(script)

    def as_page(self) -> Page:
        return cast('Page', self)

    def evaluate(self, expression: str, argument: object = None) -> object:
        evaluation = (expression, argument)
        self.evaluations.append(evaluation)

        if 'selectShow(' in expression:
            return {'x': 30.0, 'y': 60.0}

        if 'controlPeek()' in expression:
            return self._control_peek_next()

        if 'controlRead()' in expression:
            return self._control_state_next()

        return None

    def expect_navigation(self, *, url: object = None, timeout: int | None = None) -> FakeBarrier:
        succeeds = self.navigation_outcomes.pop(0) if self.navigation_outcomes else True

        return FakeBarrier(succeeds=succeeds)

    def expect_response(self, predicate: object, *, timeout: int | None = None) -> FakeBarrier:
        succeeds = self.response_outcomes.pop(0) if self.response_outcomes else True

        return FakeBarrier(succeeds=succeeds)

    def get_by_role(self, role: str, *, name: str | None = None, exact: bool = False) -> FakeLocator:
        query = (role, name, exact)
        self.role_queries.append(query)

        locator = FakeLocator()
        self.role_locators.append(locator)

        return locator

    def get_by_text(self, text: str, *, exact: bool = False) -> FakeLocator:
        query = (text, exact)
        self.text_queries.append(query)

        return FakeLocator()

    def goto(self, url: str) -> None:
        self.goto_urls.append(url)

    def locator(self, selector: str) -> FakeLocator:
        self.locator_selectors.append(selector)

        boxes = [self.locator_box]
        locator = FakeLocator(boxes=boxes)
        locator.evaluate_error = self.locator_evaluate_error

        self.locator_locators.append(locator)

        return locator

    def screenshot(self, *, path: str) -> None:
        self.screenshot_paths.append(path)

    def wait_for_load_state(self, state: str) -> None:
        self.load_states.append(state)

    def wait_for_selector(self, selector: str, *, state: str = '') -> None:
        wait = (selector, state)
        self.selector_waits.append(wait)

    def wait_for_timeout(self, ms: float) -> None:
        self.waits_ms.append(ms)

    def wait_for_url(self, url: object, *, timeout: float | None = None) -> None:
        succeeds = self.navigation_outcomes.pop(0) if self.navigation_outcomes else True

        if not succeeds:
            message = 'wait_for_url timeout'
            raise PlaywrightTimeoutError(message)


class FakePresenter:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def beat(self, ms: int = 1100) -> None:
        self.calls.append(('beat', ms))

    def check(self, locator: Locator) -> None:
        self.calls.append(('check', locator))

    def clear(self) -> None:
        self.calls.append(('clear',))

    def clear_spotlight(self) -> None:
        self.calls.append(('clear_spotlight',))

    def click(self, locator: Locator, *, force: bool = False) -> None:
        self.calls.append(('click', locator, force))

    def delta_card(
        self,
        title: str,
        rows: list[LedgerRow],
        *,
        kicker: str = '',
        subtitle: str = '',
        ms: int | None = None,
    ) -> None:
        self.calls.append(('delta_card', title, rows, kicker, subtitle, ms))

    def fill(self, locator: Locator, value: str) -> None:
        self.calls.append(('fill', locator, value))

    def hold(self) -> None:
        self.calls.append(('hold',))

    def hover(self, locator: Locator) -> None:
        self.calls.append(('hover', locator))

    def narrate(
        self,
        title: str,
        *,
        body: str = '',
        step: str = '',
        tag: str = '',
        kind: str = '',
        ms: int | None = None,
    ) -> None:
        self.calls.append(('narrate', title, body, step, tag, kind, ms))

    def press(self, locator: Locator, key: str) -> None:
        self.calls.append(('press', locator, key))

    def select(self, locator: Locator, option_label: str) -> None:
        self.calls.append(('select', locator, option_label))

    def shot(self, name: str) -> None:
        self.calls.append(('shot', name))

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

    def title_card(
        self,
        title: str,
        *,
        kicker: str = '',
        subtitle: str = '',
        ms: int | None = None,
    ) -> None:
        self.calls.append(('title_card', title, kicker, subtitle, ms))

    def uncheck(self, locator: Locator) -> None:
        self.calls.append(('uncheck', locator))

    def use_page(self, page: Page) -> None:
        self.calls.append(('use_page', page))


class FakeClock:
    def __init__(self) -> None:
        self.waits_ms: list[float] = []

    def wait_ms(self, ms: float) -> None:
        self.waits_ms.append(ms)


class FakeFrameRenderer:
    def __init__(self, *, fps: int = 60) -> None:
        self.fps = fps
        self.retargets: list[object] = []
        self.sinks: list[VideoSink] = []
        self.stop_count = 0
        self.waits_ms: list[float] = []

    def retarget(self, page: object) -> None:
        self.retargets.append(page)

    def start(self, sink: VideoSink) -> None:
        self.sinks.append(sink)

    def stop(self) -> None:
        self.stop_count += 1

    def wait_ms(self, ms: float) -> None:
        self.waits_ms.append(ms)
