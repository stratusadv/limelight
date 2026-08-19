from __future__ import annotations

import pytest

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from limelight.navigator import NAV_WAIT_TIMEOUT_MS, Navigator
from limelight.session import DemoSession

from fakes import FakeApplication, FakePage, FakePresenter


class SideNavigator(Navigator):
    nav_link_selector = '.side-nav .nav-link'


def navigator_build(
    page: FakePage,
    *,
    navigator_class: type[Navigator] = SideNavigator,
) -> tuple[Navigator, FakePresenter]:
    presenter = FakePresenter()
    session = DemoSession(page.as_page(), FakeApplication(), presenter=presenter)

    return navigator_class(session), presenter


def presenter_calls(presenter: FakePresenter, name: str) -> list[tuple[object, ...]]:
    return [call for call in presenter.calls if call[0] == name]


def test_nav_step_scrolls_spotlights_then_clicks() -> None:
    page = FakePage()
    navigator, presenter = navigator_build(page)

    navigator.to(('nav', 'Sales Orders'))

    assert page.locator_selectors == ['.side-nav .nav-link']
    assert presenter_calls(presenter, 'spotlight')[0][2] == 'Click "Sales Orders"'
    assert len(presenter_calls(presenter, 'click')) == 1
    assert page.load_states == ['domcontentloaded']


def test_nav_step_filters_the_trail_text_to_visible_links() -> None:
    page = FakePage()
    navigator, _ = navigator_build(page)

    navigator.to(('nav', 'Sales Orders'))

    target = page.locator_locators[0]

    assert target.filter_texts == ['Sales Orders', None]
    assert target.filter_visibles == [None, True]


def test_nav_scroll_is_bounded_by_the_navigator_timeout() -> None:
    page = FakePage()
    navigator, _ = navigator_build(page)

    navigator.to(('nav', 'Sales Orders'))

    assert page.locator_locators[0].evaluate_timeouts == [NAV_WAIT_TIMEOUT_MS]


def test_nav_step_survives_a_scroll_timeout_and_still_clicks() -> None:
    page = FakePage()
    navigator, presenter = navigator_build(page)

    page.locator_evaluate_error = PlaywrightTimeoutError('scrollIntoView timeout')

    navigator.to(('nav', 'Sales Orders'))

    assert len(presenter_calls(presenter, 'click')) == 1
    assert page.load_states == ['domcontentloaded']


def test_nav_without_a_selector_raises() -> None:
    page = FakePage()
    navigator, _ = navigator_build(page, navigator_class=Navigator)

    with pytest.raises(ValueError, match='nav_link_selector'):
        navigator.to(('nav', 'Sales Orders'))


def test_unknown_trail_kind_raises() -> None:
    page = FakePage()
    navigator, _ = navigator_build(page)

    with pytest.raises(ValueError, match='kind must be one of'):
        navigator.to(('menu', 'Sales Orders'))


def test_headline_narrates_before_the_trail() -> None:
    page = FakePage()
    navigator, presenter = navigator_build(page)

    navigator.to(('nav', 'Sales Orders'), headline='Find the orders')

    assert presenter.calls[0][0] == 'narrate'
    assert presenter.calls[0][1] == 'Find the orders'


def test_trailing_shot_is_taken_after_the_trail() -> None:
    page = FakePage()
    navigator, presenter = navigator_build(page)

    navigator.to(('nav', 'Sales Orders'), shot='orders')

    assert presenter.calls[-1] == ('shot', 'orders')
