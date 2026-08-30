from __future__ import annotations

import pytest

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from limelight.components.navigator import SCROLL_INTO_VIEW_SCRIPT, Navigator

if TYPE_CHECKING:
    from typing import Self

    from limelight.demo import Demo


NAVIGATION_TIMEOUT_MESSAGE = 'no navigation'
SCROLL_TIMEOUT_MESSAGE = 'offscreen'


class SideNavigator(Navigator):
    body = 'The side menu opens every part of the portal.'
    link_selector = 'a.nav-side-link'
    step = 'Navigate'


class FakeNode:
    def __init__(self, *, scroll_times_out: bool = False) -> None:
        self.click_count = 0
        self.evaluations: list[str] = []
        self.filters: list[dict[str, object]] = []
        self.scroll_times_out = scroll_times_out
        self.selectors: list[str] = []

    @property
    def first(self) -> Self:
        return self

    def as_locator(self) -> object:
        return self

    def evaluate(self, expression: str, *, timeout: int = 0) -> None:
        if self.scroll_times_out:
            raise PlaywrightTimeoutError(SCROLL_TIMEOUT_MESSAGE)

        self.evaluations.append(expression)

    def filter(self, **arguments: object) -> Self:
        self.filters.append(arguments)

        return self

    def locator(self, selector: str) -> Self:
        self.selectors.append(selector)

        return self


class FakeDemo:
    def __init__(self, *, scroll_times_out: bool = False, url_holds: bool = False) -> None:
        self.clicks: list[object] = []
        self.narrations: list[tuple[str, str, str]] = []
        self.node = FakeNode(scroll_times_out=scroll_times_out)
        self.shots: list[str] = []
        self.spotlights: list[tuple[str, bool]] = []
        self.url_holds = url_holds
        self.url_waits = 0
        self.load_states: list[str] = []

        self.page = SimpleNamespace(
            locator=self.node.locator,
            url='http://stage.test/before',
            wait_for_load_state=self.load_states.append,
            wait_for_url=self._wait_for_url,
        )

    def _wait_for_url(self, predicate: object, *, timeout: int = 0) -> None:
        self.url_waits += 1

        if self.url_holds:
            raise PlaywrightTimeoutError(NAVIGATION_TIMEOUT_MESSAGE)

    def as_demo(self) -> Demo:
        return cast('Demo', self)

    def click(self, locator: object) -> None:
        self.clicks.append(locator)

    def narrate(self, title: str, *, body: str = '', step: str = '') -> None:
        narration = (title, step, body)
        self.narrations.append(narration)

    def screenshot(self, name: str) -> None:
        self.shots.append(name)

    def spotlight(self, locator: object, *, label: str = '', scroll: bool = True) -> None:
        spotlight = (label, scroll)
        self.spotlights.append(spotlight)


def expect_stub(locator: object) -> SimpleNamespace:
    return SimpleNamespace(to_be_visible=lambda timeout: None)


@pytest.fixture(autouse=True)
def _expect_stubbed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('limelight.components.navigator.expect', expect_stub)


def test_a_destination_is_narrated_spotlighted_and_clicked() -> None:
    demo = FakeDemo()
    navigator = SideNavigator(demo.as_demo())

    navigator.to('Work Orders', headline='Open the work orders')

    assert demo.narrations == [
        ('Open the work orders', 'Navigate', SideNavigator.body),
    ]

    assert demo.spotlights == [('Click "Work Orders"', False)]
    assert demo.clicks == [demo.node]


def test_a_destination_is_looked_up_through_the_class_selector() -> None:
    demo = FakeDemo()
    navigator = SideNavigator(demo.as_demo())

    navigator.to('Fields')

    assert demo.node.selectors == ['a.nav-side-link']

    assert demo.node.filters == [
        {'has_text': 'Fields'},
        {'visible': True},
    ]


def test_a_screenshot_is_named_after_the_destination() -> None:
    demo = FakeDemo()
    navigator = SideNavigator(demo.as_demo())

    navigator.to('All Daily Reports')

    assert demo.shots == ['nav-all-daily-reports']


def test_a_screenshot_is_skipped_when_it_is_not_asked_for() -> None:
    demo = FakeDemo()
    navigator = SideNavigator(demo.as_demo())

    navigator.to('Fields', shot=False)

    assert demo.shots == []


def test_a_destination_without_a_headline_is_silent() -> None:
    demo = FakeDemo()
    navigator = SideNavigator(demo.as_demo())

    navigator.to('Fields')

    assert demo.narrations == []


def test_a_body_given_at_the_call_wins_over_the_class_body() -> None:
    demo = FakeDemo()
    navigator = SideNavigator(demo.as_demo())

    navigator.to('Fields', headline='Open the fields', body='Every field is here.')

    assert demo.narrations == [('Open the fields', 'Navigate', 'Every field is here.')]


def test_a_link_is_scrolled_into_view_before_it_is_spotlighted() -> None:
    demo = FakeDemo()
    navigator = SideNavigator(demo.as_demo())

    navigator.to('Fields')

    assert demo.node.evaluations == [SCROLL_INTO_VIEW_SCRIPT]


def test_a_menu_that_cannot_scroll_is_still_navigated() -> None:
    demo = FakeDemo(scroll_times_out=True)
    navigator = SideNavigator(demo.as_demo())

    navigator.to('Fields')

    assert demo.node.evaluations == []
    assert demo.clicks == [demo.node]


def test_a_destination_that_never_changes_the_url_still_settles() -> None:
    demo = FakeDemo(url_holds=True)
    navigator = SideNavigator(demo.as_demo())

    navigator.to('Fields')

    assert demo.url_waits == 1
    assert demo.load_states == ['domcontentloaded']


def test_the_default_selector_describes_a_plain_anchor() -> None:
    demo = FakeDemo()
    navigator = Navigator(demo.as_demo())

    navigator.to('Fields')

    assert demo.node.selectors == ['a']
