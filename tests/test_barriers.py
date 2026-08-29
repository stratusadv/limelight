from __future__ import annotations

import pytest

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from limelight.barriers import (
    trigger_until_navigation,
    trigger_until_response,
    trigger_until_visible,
    wait_until,
)

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
        trigger_until_response(
            page.as_page(),
            trigger,
            url_fragment='orders/approve/',
            attempt_count=2,
        )

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


def test_wait_until_returns_before_holding_when_the_predicate_holds() -> None:
    holds: list[int] = []

    wait_until(lambda: True, holds.append)

    assert holds == []


def test_wait_until_holds_for_the_interval_between_attempts() -> None:
    holds: list[int] = []
    outcomes = [False, False, True]

    wait_until(lambda: outcomes.pop(0), holds.append, interval_ms=100)

    assert holds == [100, 100]


def test_wait_until_raises_once_attempts_are_exhausted() -> None:
    holds: list[int] = []

    with pytest.raises(AssertionError, match='condition not met after 750ms'):
        wait_until(lambda: False, holds.append, attempt_count_max=3, interval_ms=250)

    assert holds == [250, 250, 250]


def test_wait_until_rejects_a_non_positive_attempt_count_max() -> None:
    with pytest.raises(ValueError, match='attempt_count_max must be positive: 0'):
        wait_until(lambda: True, lambda ms: None, attempt_count_max=0)


def test_wait_until_rejects_a_non_positive_interval() -> None:
    with pytest.raises(ValueError, match='interval_ms must be positive: 0'):
        wait_until(lambda: True, lambda ms: None, interval_ms=0)


def test_trigger_until_response_matches_on_a_url_fragment() -> None:
    page = FakePage()

    page.response_outcomes = [True]

    trigger_until_response(page.as_page(), lambda: None, url_fragment='/orders/')

    predicate = cast('Callable[[object], bool]', page.response_predicates[0])

    assert predicate(SimpleNamespace(url='http://stage.test/orders/1')) is True
    assert predicate(SimpleNamespace(url='http://stage.test/customers/1')) is False
