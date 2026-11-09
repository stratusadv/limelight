from __future__ import annotations

import math

from contextlib import contextmanager
from functools import partial
from typing import TYPE_CHECKING

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from limelight.errors import BarrierError

if TYPE_CHECKING:
    import re

    from collections.abc import Callable, Generator
    from playwright.sync_api import Locator, Page, Request, Response


ATTEMPT_COUNT_MAX_DEFAULT = 3
BARRIER_TIMEOUT_MS_DEFAULT = 5000
SETTLE_INTERVAL_MS_DEFAULT = 100
SETTLE_TIMEOUT_MS_DEFAULT = 15_000
WAIT_ATTEMPT_COUNT_MAX_DEFAULT = 40
WAIT_INTERVAL_MS_DEFAULT = 250


class _RequestTally:
    """
    A running count of the requests a URL fragment names.

    The count rises when such a request starts and falls when it finishes or
    fails, so a block that fires several requests is settled only once the last
    of them is answered.
    """

    def __init__(self, url_fragment: str) -> None:
        """
        The constructor for the _RequestTally class.

        :param url_fragment: The text a tallied request URL contains.
        """

        self.pending: list[Request] = []
        self.url_fragment = url_fragment

    def is_quiet(self) -> bool:
        """
        A method that reports whether each tallied request has been answered.

        :return: True if nothing is in flight, False otherwise.
        """

        return not self.pending

    def settled(self, request: Request) -> None:
        """
        A method that drops a request from the tally.

        :param request: The request that finished or failed.
        """

        if request in self.pending:
            self.pending.remove(request)

    def started(self, request: Request) -> None:
        """
        A method that adds a request to the tally.

        :param request: The request that started.
        """

        if self.url_fragment in request.url:
            self.pending.append(request)


def _attempts_run(
    *,
    attempt_count_max: int,
    failure: str,
    attempt: Callable[[], None],
) -> None:
    error_last: PlaywrightTimeoutError | None = None

    for _ in range(attempt_count_max):
        try:
            attempt()
        except PlaywrightTimeoutError as error:
            error_last = error
        else:
            return

    raise BarrierError(failure) from error_last


def _method_predicate(method: str) -> Callable[[Response], bool]:
    """
    A function that builds a response predicate from an HTTP method.

    :param method: The method the request behind the response was made with.
    :return: The predicate that matches such a response.
    """

    wanted = method.upper()

    def matches(response: Response) -> bool:
        """
        A function that reports whether a response answers that method.

        :param response: The response to test.
        :return: True if the request used the method, False otherwise.
        """

        return response.request.method.upper() == wanted

    return matches


def _navigation_attempt(
    page: Page,
    *,
    url_pattern: str | re.Pattern[str] | None,
    timeout_ms: int,
    trigger: Callable[[], None],
) -> None:
    with page.expect_navigation(url=url_pattern, timeout=timeout_ms):
        trigger()


def _positive_validate(name: str, value: int) -> None:
    if value < 1:
        message = f'{name} must be positive: {value}'
        raise ValueError(message)


def _response_attempt(
    page: Page,
    *,
    timeout_ms: int,
    matches: Callable[[Response], bool],
    trigger: Callable[[], None],
) -> None:
    with page.expect_response(matches, timeout=timeout_ms):
        trigger()


def _url_fragment_predicate(url_fragment: str) -> Callable[[Response], bool]:
    """
    A function that builds a response predicate from a substring of a URL.

    :param url_fragment: The text the response URL must contain.
    :return: The predicate that matches such a response.
    """

    def matches(response: Response) -> bool:
        """
        A function that reports whether a response URL carries the fragment.

        :param response: The response to test.
        :return: True if the URL contains the fragment, False otherwise.
        """

        return url_fragment in response.url

    return matches


def _visibility_attempt(locator: Locator, *, timeout_ms: int, trigger: Callable[[], None]) -> None:
    trigger()

    locator.wait_for(state='visible', timeout=timeout_ms)


@contextmanager
def requests_settled(
    page: Page,
    *,
    url_fragment: str,
    timeout_ms: int = SETTLE_TIMEOUT_MS_DEFAULT,
    interval_ms: int = SETTLE_INTERVAL_MS_DEFAULT,
) -> Generator[None]:
    """
    A context manager that holds the block open until its background requests finish.

    The requests a fragment names are tallied while the block runs, and the exit
    waits for the tally to fall back to zero. A page that answers a click with a
    request rather than a navigation settles on the request itself this way,
    rather than on a fixed sleep or on network silence the page never reaches.

    :param page: The page whose requests are tallied.
    :param url_fragment: The text a tallied request URL contains.
    :param timeout_ms: The time the exit waits for the tally to clear.
    :param interval_ms: The time waited between reads of the tally.
    :return: The context manager that wraps the block.
    :raises ValueError: If the fragment is empty, or a duration is not positive.
    :raises BarrierError: If the requests never finish.
    """

    if not url_fragment.strip():
        message = f'url_fragment must not be empty (got "{url_fragment}")'
        raise ValueError(message)

    _positive_validate('timeout_ms', timeout_ms)
    _positive_validate('interval_ms', interval_ms)

    pending = _RequestTally(url_fragment)

    page.on('request', pending.started)
    page.on('requestfinished', pending.settled)
    page.on('requestfailed', pending.settled)

    try:
        yield

        if pending.is_quiet():
            return

        for _ in range(math.ceil(timeout_ms / interval_ms)):
            page.wait_for_timeout(interval_ms)

            if pending.is_quiet():
                return

        message = f'the requests to "{url_fragment}" never settled within {timeout_ms}ms'
        raise BarrierError(message)
    finally:
        page.remove_listener('request', pending.started)
        page.remove_listener('requestfinished', pending.settled)
        page.remove_listener('requestfailed', pending.settled)


def trigger_until_navigation(
    page: Page,
    trigger: Callable[[], None],
    *,
    url_pattern: str | re.Pattern[str] | None = None,
    attempt_count_max: int = ATTEMPT_COUNT_MAX_DEFAULT,
    timeout_ms: int = BARRIER_TIMEOUT_MS_DEFAULT,
) -> None:
    """
    A function that repeats a trigger until the page navigates.

    The trigger is retried because a click can land before the handler that
    listens for it is bound, and a lost click leaves the page where it was with
    no error to catch. The final attempt raises, so a page that never
    navigates fails rather than passing silently.

    :param page: The page expected to navigate.
    :param trigger: The action that causes the navigation.
    :param url_pattern: The URL the navigation must match, or None for any.
    :param attempt_count_max: The number of times the trigger is tried at most.
    :param timeout_ms: The time each attempt waits for the navigation.
    :raises ValueError: If the attempt count or the timeout is not positive.
    :raises BarrierError: If the last attempt sees no navigation.
    """

    _positive_validate('attempt_count_max', attempt_count_max)
    _positive_validate('timeout_ms', timeout_ms)

    attempt = partial(
        _navigation_attempt,
        page,
        url_pattern=url_pattern,
        timeout_ms=timeout_ms,
        trigger=trigger,
    )

    failure = f'the page never navigated within {attempt_count_max} attempts of {timeout_ms}ms'

    _attempts_run(attempt_count_max=attempt_count_max, failure=failure, attempt=attempt)


def trigger_until_response(
    page: Page,
    trigger: Callable[[], None],
    *,
    url_fragment: str = '',
    method: str = '',
    predicate: Callable[[Response], bool] | None = None,
    attempt_count_max: int = ATTEMPT_COUNT_MAX_DEFAULT,
    timeout_ms: int = BARRIER_TIMEOUT_MS_DEFAULT,
) -> None:
    """
    A function that repeats a trigger until a matching response arrives.

    The response is matched by a substring of its URL, by the method its request
    was made with, or by a predicate, exactly one at a time, so no two matchers
    can disagree about which response ends the wait.

    :param page: The page expected to receive the response.
    :param trigger: The action that causes the request.
    :param url_fragment: The text the response URL must contain.
    :param method: The HTTP method the request behind the response was made with.
    :param predicate: The test a response must pass.
    :param attempt_count_max: The number of times the trigger is tried at most.
    :param timeout_ms: The time each attempt waits for the response.
    :raises ValueError: If the attempt count or the timeout is not positive, or if the
        matchers are not given exactly one at a time.
    :raises BarrierError: If the last attempt sees no matching response.
    """

    _positive_validate('attempt_count_max', attempt_count_max)
    _positive_validate('timeout_ms', timeout_ms)

    matcher_count = sum((bool(url_fragment), bool(method), predicate is not None))

    if matcher_count != 1:
        message = 'trigger_until_response takes exactly one of url_fragment, method and predicate'

        raise ValueError(message)

    if predicate is not None:
        matches = predicate
    elif method:
        matches = _method_predicate(method)
    else:
        matches = _url_fragment_predicate(url_fragment)

    attempt = partial(
        _response_attempt,
        page,
        timeout_ms=timeout_ms,
        matches=matches,
        trigger=trigger,
    )

    failure = f'no response matched within {attempt_count_max} attempts of {timeout_ms}ms'

    _attempts_run(attempt_count_max=attempt_count_max, failure=failure, attempt=attempt)


def trigger_until_visible(
    locator: Locator,
    trigger: Callable[[], None],
    *,
    attempt_count_max: int = ATTEMPT_COUNT_MAX_DEFAULT,
    timeout_ms: int = BARRIER_TIMEOUT_MS_DEFAULT,
) -> None:
    """
    A function that repeats a trigger until an element becomes visible.

    :param locator: The locator for the element that must appear.
    :param trigger: The action that reveals the element.
    :param attempt_count_max: The number of times the trigger is tried at most.
    :param timeout_ms: The time each attempt waits for the element.
    :raises ValueError: If the attempt count or the timeout is not positive.
    :raises BarrierError: If the element is still hidden after the last attempt.
    """

    _positive_validate('attempt_count_max', attempt_count_max)
    _positive_validate('timeout_ms', timeout_ms)

    attempt = partial(_visibility_attempt, locator, timeout_ms=timeout_ms, trigger=trigger)
    failure = f'{locator} stayed hidden through {attempt_count_max} attempts of {timeout_ms}ms'

    _attempts_run(attempt_count_max=attempt_count_max, failure=failure, attempt=attempt)


def wait_until(
    hold: Callable[[int], None],
    predicate: Callable[[], bool],
    *,
    attempt_count_max: int = WAIT_ATTEMPT_COUNT_MAX_DEFAULT,
    description: str = '',
    interval_ms: int = WAIT_INTERVAL_MS_DEFAULT,
) -> None:
    """
    A function that polls a condition until it holds or the attempts run out.

    The wait is handed a hold callable rather than sleeping itself, so a demo
    that drives the clock can advance its own timeline between polls instead of
    burning real seconds.

    :param hold: The callable that waits for the given number of milliseconds.
    :param predicate: The condition polled between holds.
    :param attempt_count_max: The number of times the condition is polled.
    :param description: The name of the condition, used in the failure message.
    :param interval_ms: The time held between polls.
    :raises ValueError: If the attempt count or the interval is not positive.
    :raises BarrierError: If the condition never holds.
    """

    _positive_validate('attempt_count_max', attempt_count_max)
    _positive_validate('interval_ms', interval_ms)

    if predicate():
        return

    for _ in range(attempt_count_max - 1):
        hold(interval_ms)

        if predicate():
            return

    subject = description or 'condition'

    message = f'{subject} did not hold across {attempt_count_max} polls {interval_ms}ms apart'
    raise BarrierError(message)
