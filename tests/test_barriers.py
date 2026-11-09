from __future__ import annotations

import pytest

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from limelight import BarrierError
from limelight.barriers import (
    requests_settled,
    trigger_until_navigation,
    trigger_until_response,
    trigger_until_visible,
    wait_until,
)

from fakes import FakeLocator, FakePage

if TYPE_CHECKING:
    from collections.abc import Callable


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

    with pytest.raises(BarrierError, match='never navigated within 3 attempts of 5000ms') as raised:
        trigger_until_navigation(page.as_page(), trigger, url_pattern='**/done/')

    assert isinstance(raised.value.__cause__, PlaywrightTimeoutError)
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

    with pytest.raises(BarrierError, match='no response matched within 2 attempts') as raised:
        trigger_until_response(
            page.as_page(),
            trigger,
            url_fragment='orders/approve/',
            attempt_count_max=2,
        )

    assert isinstance(raised.value.__cause__, PlaywrightTimeoutError)
    assert calls == [1, 1]


def test_attempt_count_max_must_be_positive() -> None:
    page = FakePage()
    calls, trigger = trigger_counter()

    with pytest.raises(ValueError, match='attempt_count_max must be positive: 0'):
        trigger_until_navigation(
            page.as_page(),
            trigger,
            url_pattern='**/done/',
            attempt_count_max=0,
        )

    assert calls == []


def test_navigation_timeout_must_be_positive() -> None:
    page = FakePage()
    calls, trigger = trigger_counter()

    with pytest.raises(ValueError, match='timeout_ms must be positive: 0'):
        trigger_until_navigation(page.as_page(), trigger, timeout_ms=0)

    assert calls == []


def test_response_timeout_must_be_positive() -> None:
    page = FakePage()
    calls, trigger = trigger_counter()

    with pytest.raises(ValueError, match='timeout_ms must be positive: 0'):
        trigger_until_response(page.as_page(), trigger, method='POST', timeout_ms=0)

    assert calls == []


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
            predicate=lambda _: True,
        )


def test_response_accepts_a_predicate() -> None:
    page = FakePage()
    calls, trigger = trigger_counter()

    trigger_until_response(page.as_page(), trigger, predicate=lambda _: True)

    assert calls == [1]


def test_response_accepts_a_method() -> None:
    page = FakePage()
    calls, trigger = trigger_counter()

    trigger_until_response(page.as_page(), trigger, method='POST')

    assert calls == [1]


def test_response_matches_the_method_case_insensitively() -> None:
    page = FakePage()
    _, trigger = trigger_counter()

    trigger_until_response(page.as_page(), trigger, method='post')

    matches = cast('Callable[[object], bool]', page.response_predicates[0])

    assert matches(SimpleNamespace(request=SimpleNamespace(method='POST'))) is True
    assert matches(SimpleNamespace(request=SimpleNamespace(method='GET'))) is False


def test_response_rejects_a_method_beside_a_url_fragment() -> None:
    page = FakePage()
    _, trigger = trigger_counter()

    with pytest.raises(ValueError, match='exactly one'):
        trigger_until_response(page.as_page(), trigger, url_fragment='orders/', method='POST')


def test_visible_success_first_attempt() -> None:
    locator = FakeLocator()
    calls, trigger = trigger_counter()

    trigger_until_visible(locator.as_locator(), trigger)

    assert calls == [1]
    assert locator.waits == [('visible', 5000)]


def test_visible_retries_trigger_after_timeout() -> None:
    locator = FakeLocator()
    locator.wait_outcomes = [False, True]

    calls, trigger = trigger_counter()

    trigger_until_visible(locator.as_locator(), trigger, timeout_ms=300)

    assert calls == [1, 1]
    assert locator.waits == [('visible', 300), ('visible', 300)]


def test_visible_raises_when_attempts_exhausted() -> None:
    locator = FakeLocator()
    locator.wait_outcomes = [False, False]

    calls, trigger = trigger_counter()

    with pytest.raises(BarrierError, match='stayed hidden through 2 attempts') as raised:
        trigger_until_visible(locator.as_locator(), trigger, attempt_count_max=2)

    assert isinstance(raised.value.__cause__, PlaywrightTimeoutError)
    assert calls == [1, 1]


def test_visible_timeout_must_be_positive() -> None:
    locator = FakeLocator()
    calls, trigger = trigger_counter()

    with pytest.raises(ValueError, match='timeout_ms must be positive: 0'):
        trigger_until_visible(locator.as_locator(), trigger, timeout_ms=0)

    assert calls == []
    assert locator.waits == []


def test_navigation_accepts_any_url_when_no_pattern_is_given() -> None:
    page = FakePage()
    calls, trigger = trigger_counter()

    trigger_until_navigation(page.as_page(), trigger)

    assert calls == [1]


def test_wait_until_returns_before_holding_when_the_predicate_holds() -> None:
    holds: list[int] = []

    wait_until(holds.append, lambda: True)

    assert holds == []


def test_wait_until_holds_for_the_interval_between_attempts() -> None:
    holds: list[int] = []
    outcomes = [False, False, True]

    wait_until(holds.append, lambda: outcomes.pop(0), interval_ms=100)

    assert holds == [100, 100]


def test_wait_until_raises_once_attempts_are_exhausted() -> None:
    holds: list[int] = []
    polls: list[int] = []

    def predicate() -> bool:
        polls.append(1)

        return False

    with pytest.raises(BarrierError, match='condition did not hold across 3 polls 250ms apart'):
        wait_until(holds.append, predicate, attempt_count_max=3, interval_ms=250)

    assert polls == [1, 1, 1]
    assert holds == [250, 250]


def test_wait_until_polls_once_without_holding_when_one_attempt_is_allowed() -> None:
    holds: list[int] = []

    with pytest.raises(BarrierError, match='across 1 polls'):
        wait_until(holds.append, lambda: False, attempt_count_max=1)

    assert holds == []


def test_wait_until_rejects_a_non_positive_attempt_count_max() -> None:
    with pytest.raises(ValueError, match='attempt_count_max must be positive: 0'):
        wait_until(lambda _: None, lambda: True, attempt_count_max=0)


def test_wait_until_rejects_a_non_positive_interval() -> None:
    with pytest.raises(ValueError, match='interval_ms must be positive: 0'):
        wait_until(lambda _: None, lambda: True, interval_ms=0)


def test_trigger_until_response_matches_on_a_url_fragment() -> None:
    page = FakePage()

    page.response_outcomes = [True]

    trigger_until_response(page.as_page(), lambda: None, url_fragment='/orders/')

    predicate = cast('Callable[[object], bool]', page.response_predicates[0])

    assert predicate(SimpleNamespace(url='http://stage.test/orders/1')) is True
    assert predicate(SimpleNamespace(url='http://stage.test/customers/1')) is False


def test_wait_until_names_the_condition_it_was_given() -> None:
    description = 'the sync bridge hook for the renamed species'

    with pytest.raises(BarrierError, match=f'{description} did not hold across 3 polls'):
        wait_until(
            lambda _: None,
            lambda: False,
            attempt_count_max=3,
            description=description,
            interval_ms=250,
        )


def request_of(url: str) -> object:
    return SimpleNamespace(url=url)


def requests_overlap(page: FakePage) -> None:
    page.emit('requestfinished', request_of('http://stage.test/dg/earlier/'))
    page.emit('request', request_of('http://stage.test/dg/later/'))


def test_requests_settled_returns_once_the_tallied_request_finishes() -> None:
    page = FakePage()

    with requests_settled(page.as_page(), url_fragment='/dg/'):
        page.emit('request', request_of('http://stage.test/dg/field/'))
        page.emit('requestfinished', request_of('http://stage.test/dg/field/'))

    assert page.waits_ms == []


def test_requests_settled_ignores_a_request_the_fragment_does_not_name() -> None:
    page = FakePage()

    with requests_settled(page.as_page(), url_fragment='/dg/'):
        page.emit('request', request_of('http://stage.test/static/app.css'))

    assert page.waits_ms == []


def test_requests_settled_counts_a_failed_request_as_answered() -> None:
    page = FakePage()

    with requests_settled(page.as_page(), url_fragment='/dg/'):
        page.emit('request', request_of('http://stage.test/dg/field/'))
        page.emit('requestfailed', request_of('http://stage.test/dg/field/'))

    assert page.waits_ms == []


def test_requests_settled_waits_for_every_request_of_a_burst() -> None:
    page = FakePage()

    with requests_settled(page.as_page(), url_fragment='/dg/', timeout_ms=50):
        page.emit('request', request_of('http://stage.test/dg/one/'))
        page.emit('request', request_of('http://stage.test/dg/two/'))
        page.emit('requestfinished', request_of('http://stage.test/dg/one/'))
        page.emit('requestfinished', request_of('http://stage.test/dg/two/'))

    assert page.waits_ms == []


def test_requests_settled_raises_when_a_request_never_finishes() -> None:
    page = FakePage()

    with (
        pytest.raises(BarrierError, match='the requests to "/dg/" never settled'),
        requests_settled(page.as_page(), url_fragment='/dg/', timeout_ms=20),
    ):
        page.emit('request', request_of('http://stage.test/dg/field/'))


def test_requests_settled_waits_no_longer_than_its_timeout() -> None:
    page = FakePage()

    with (
        pytest.raises(BarrierError),
        requests_settled(page.as_page(), url_fragment='/dg/', timeout_ms=250, interval_ms=100),
    ):
        page.emit('request', request_of('http://stage.test/dg/field/'))

    assert page.waits_ms == [100, 100, 100]


def test_requests_settled_detaches_its_listeners_on_the_way_out() -> None:
    page = FakePage()

    with requests_settled(page.as_page(), url_fragment='/dg/'):
        pass

    assert page.listeners == {'request': [], 'requestfinished': [], 'requestfailed': []}


def test_requests_settled_detaches_its_listeners_after_a_failure() -> None:
    page = FakePage()

    with (
        pytest.raises(BarrierError),
        requests_settled(page.as_page(), url_fragment='/dg/', timeout_ms=20),
    ):
        page.emit('request', request_of('http://stage.test/dg/field/'))

    assert page.listeners == {'request': [], 'requestfinished': [], 'requestfailed': []}


def test_requests_settled_rejects_an_empty_fragment() -> None:
    page = FakePage()

    with (
        pytest.raises(ValueError, match='url_fragment must not be empty'),
        requests_settled(page.as_page(), url_fragment=' '),
    ):
        pass


def test_requests_settled_rejects_a_non_positive_timeout() -> None:
    page = FakePage()

    with (
        pytest.raises(ValueError, match='timeout_ms must be positive: 0'),
        requests_settled(page.as_page(), url_fragment='/dg/', timeout_ms=0),
    ):
        pass


def test_requests_settled_rejects_a_non_positive_interval() -> None:
    page = FakePage()

    with (
        pytest.raises(ValueError, match='interval_ms must be positive: 0'),
        requests_settled(page.as_page(), url_fragment='/dg/', interval_ms=0),
    ):
        pass


def test_requests_settled_waits_for_a_request_after_an_earlier_one_finishes() -> None:
    page = FakePage()

    with (
        pytest.raises(BarrierError, match='the requests to "/dg/" never settled'),
        requests_settled(page.as_page(), url_fragment='/dg/', timeout_ms=20),
    ):
        requests_overlap(page)
