from __future__ import annotations

import pytest

from types import SimpleNamespace
from typing import TYPE_CHECKING

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from limelight.barriers import trigger_until_navigation, trigger_until_response, trigger_until_visible

from fakes import FakeLocator, FakePage

if TYPE_CHECKING:
    from collections.abc import Callable


def expect_outcomes_stub(outcomes: list[bool]) -> Callable[[object], SimpleNamespace]:
    def expect_fake(locator: object) -> SimpleNamespace:
        def to_be_visible(timeout: int | None = None) -> None:
            succeeds = outcomes.pop(0) if outcomes else True

            if not succeeds:
                message = 'locator expected to be visible'
                raise AssertionError(message)

        return SimpleNamespace(to_be_visible=to_be_visible)

    return expect_fake


def trigger_counter() -> tuple[list[int], Callable[[], None]]:
    calls: list[int] = []

    def trigger() -> None:
        calls.append(1)

    return calls, trigger


def test_navigation_success_first_attempt() -> None:
    page = FakePage()
    calls, trigger = trigger_counter()

    trigger_until_navigation(page.as_page(), trigger, url_pattern='**/done/')

    assert calls == [1]


def test_navigation_retries_after_timeout() -> None:
    page = FakePage()
    page.navigation_outcomes = [False, True]

    calls, trigger = trigger_counter()

    trigger_until_navigation(page.as_page(), trigger, url_pattern='**/done/')

    assert calls == [1, 1]


def test_navigation_raises_when_attempts_exhausted() -> None:
    page = FakePage()
    page.navigation_outcomes = [False, False, False]

    calls, trigger = trigger_counter()

    with pytest.raises(PlaywrightTimeoutError):
        trigger_until_navigation(page.as_page(), trigger, url_pattern='**/done/')

    assert calls == [1, 1, 1]


def test_response_success_first_attempt() -> None:
    page = FakePage()
    calls, trigger = trigger_counter()

    trigger_until_response(page.as_page(), trigger, url_fragment='orders/approve/')

    assert calls == [1]


def test_response_raises_when_attempts_exhausted() -> None:
    page = FakePage()
    page.response_outcomes = [False, False]

    calls, trigger = trigger_counter()

    with pytest.raises(PlaywrightTimeoutError):
        trigger_until_response(page.as_page(), trigger, url_fragment='orders/approve/', attempt_count=2)

    assert calls == [1, 1]


def test_attempt_count_must_be_positive() -> None:
    page = FakePage()
    _, trigger = trigger_counter()

    with pytest.raises(ValueError, match='attempt_count'):
        trigger_until_navigation(page.as_page(), trigger, url_pattern='**/done/', attempt_count=0)


def test_response_needs_a_url_fragment_or_a_predicate() -> None:
    page = FakePage()
    _, trigger = trigger_counter()

    with pytest.raises(ValueError, match='exactly one'):
        trigger_until_response(page.as_page(), trigger)


def test_response_rejects_both_a_url_fragment_and_a_predicate() -> None:
    page = FakePage()
    _, trigger = trigger_counter()

    with pytest.raises(ValueError, match='exactly one'):
        trigger_until_response(
            page.as_page(),
            trigger,
            url_fragment='orders/',
            predicate=lambda response: True,
        )


def test_response_accepts_a_predicate() -> None:
    page = FakePage()
    calls, trigger = trigger_counter()

    trigger_until_response(page.as_page(), trigger, predicate=lambda response: True)

    assert calls == [1]


def test_visible_success_first_attempt(monkeypatch: pytest.MonkeyPatch) -> None:
    outcomes = [True]

    monkeypatch.setattr('limelight.barriers.expect', expect_outcomes_stub(outcomes))

    calls, trigger = trigger_counter()

    trigger_until_visible(trigger, FakeLocator().as_locator())

    assert calls == [1]


def test_visible_retries_trigger_after_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    outcomes = [False, True]

    monkeypatch.setattr('limelight.barriers.expect', expect_outcomes_stub(outcomes))

    calls, trigger = trigger_counter()

    trigger_until_visible(trigger, FakeLocator().as_locator())

    assert calls == [1, 1]


def test_visible_raises_when_attempts_exhausted(monkeypatch: pytest.MonkeyPatch) -> None:
    outcomes = [False, False]

    monkeypatch.setattr('limelight.barriers.expect', expect_outcomes_stub(outcomes))

    calls, trigger = trigger_counter()

    with pytest.raises(AssertionError):
        trigger_until_visible(trigger, FakeLocator().as_locator(), attempt_count=2)

    assert calls == [1, 1]


def test_navigation_accepts_any_url_when_no_pattern_is_given() -> None:
    page = FakePage()
    calls, trigger = trigger_counter()

    trigger_until_navigation(page.as_page(), trigger)

    assert calls == [1]
