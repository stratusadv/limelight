from __future__ import annotations

import time

from contextlib import contextmanager
from typing import TYPE_CHECKING

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, expect

if TYPE_CHECKING:
    import re

    from collections.abc import Callable, Iterator
    from playwright.sync_api import Locator, Page, Request, Response


ATTEMPT_COUNT_DEFAULT = 3
BARRIER_TIMEOUT_MS_DEFAULT = 5000
SETTLE_INTERVAL_MS_DEFAULT = 100
SETTLE_TIMEOUT_MS_DEFAULT = 15_000
WAIT_ATTEMPT_COUNT_MAX = 40
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

        self.count = 0
        self.url_fragment = url_fragment

    @property
    def is_quiet(self) -> bool:
        """
        A property that reports whether every tallied request has been answered.

        :return: True if nothing is in flight, False otherwise.
        """

        return self.count <= 0

    def settled(self, request: Request) -> None:
        """
        A method that drops a request from the tally.

        :param request: The request that finished or failed.
        """

        if self.url_fragment in request.url:
            self.count -= 1

    def started(self, request: Request) -> None:
        """
        A method that adds a request to the tally.

        :param request: The request that started.
        """

        if self.url_fragment in request.url:
            self.count += 1


def _attempt_count_validate(attempt_count: int) -> None:
    """
    A function that rejects an attempt count below one.

    :param attempt_count: The number of times a barrier retries its trigger.
    :raises ValueError: If the attempt count is not positive.
    """

    if attempt_count < 1:
        message = f'attempt_count must be positive: {attempt_count}'
        raise ValueError(message)


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


@contextmanager
def requests_settled(
    page: Page,
    *,
    url_fragment: str,
    timeout_ms: int = SETTLE_TIMEOUT_MS_DEFAULT,
    interval_ms: int = SETTLE_INTERVAL_MS_DEFAULT,
) -> Iterator[None]:
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
    :raises ValueError: If the fragment is empty, or a duration is not positive.
    :raises AssertionError: If the requests never finish.
    """

    if not url_fragment.strip():
        message = f'url_fragment must not be empty (got "{url_fragment}")'
        raise ValueError(message)

    if timeout_ms < 1:
        message = f'timeout_ms must be positive: {timeout_ms}'
        raise ValueError(message)

    if interval_ms < 1:
        message = f'interval_ms must be positive: {interval_ms}'
        raise ValueError(message)

    pending = _RequestTally(url_fragment)

    page.on('request', pending.started)
    page.on('requestfinished', pending.settled)
    page.on('requestfailed', pending.settled)

    try:
        yield

        deadline = time.monotonic() + timeout_ms / 1000

        while not pending.is_quiet:
            if time.monotonic() >= deadline:
                message = (
                    f'the requests to "{url_fragment}" never settled '
                    f'within {timeout_ms}ms'
                )

                raise AssertionError(message)

            page.wait_for_timeout(interval_ms)
    finally:
        page.remove_listener('request', pending.started)
        page.remove_listener('requestfinished', pending.settled)
        page.remove_listener('requestfailed', pending.settled)


def trigger_until_navigation(
    page: Page,
    trigger: Callable[[], None],
    *,
    url_pattern: str | re.Pattern[str] | None = None,
    attempt_count: int = ATTEMPT_COUNT_DEFAULT,
    timeout_ms: int = BARRIER_TIMEOUT_MS_DEFAULT,
) -> None:
    """
    A function that repeats a trigger until the page navigates.

    The trigger is retried because a click can land before the handler that
    listens for it is bound, and a lost click leaves the page where it was with
    no error to catch. The final attempt re-raises, so a page that never
    navigates fails rather than passing silently.

    :param page: The page expected to navigate.
    :param trigger: The action that causes the navigation.
    :param url_pattern: The URL the navigation must match, or None for any.
    :param attempt_count: The number of times the trigger is retried.
    :param timeout_ms: The time each attempt waits for the navigation.
    :raises ValueError: If the attempt count is not positive.
    :raises PlaywrightTimeoutError: If the last attempt sees no navigation.
    """

    _attempt_count_validate(attempt_count)

    for attempt in range(attempt_count):
        try:
            with page.expect_navigation(url=url_pattern, timeout=timeout_ms):
                trigger()
        except PlaywrightTimeoutError:
            if attempt == attempt_count - 1:
                raise
        else:
            return


def trigger_until_response(
    page: Page,
    trigger: Callable[[], None],
    *,
    url_fragment: str = '',
    predicate: Callable[[Response], bool] | None = None,
    attempt_count: int = ATTEMPT_COUNT_DEFAULT,
    timeout_ms: int = BARRIER_TIMEOUT_MS_DEFAULT,
) -> None:
    """
    A function that repeats a trigger until a matching response arrives.

    The response is matched either by a substring of its URL or by a predicate,
    never both, so the two cannot disagree about which response ends the wait.

    :param page: The page expected to receive the response.
    :param trigger: The action that causes the request.
    :param url_fragment: The text the response URL must contain.
    :param predicate: The test a response must pass.
    :param attempt_count: The number of times the trigger is retried.
    :param timeout_ms: The time each attempt waits for the response.
    :raises ValueError: If the attempt count is not positive, or if the fragment and
        the predicate are not given exactly one at a time.
    :raises PlaywrightTimeoutError: If the last attempt sees no matching response.
    """

    _attempt_count_validate(attempt_count)

    if bool(url_fragment) == (predicate is not None):
        message = 'trigger_until_response takes exactly one of url_fragment and predicate'
        raise ValueError(message)

    matches = predicate if predicate is not None else _url_fragment_predicate(url_fragment)

    for attempt in range(attempt_count):
        try:
            with page.expect_response(matches, timeout=timeout_ms):
                trigger()
        except PlaywrightTimeoutError:
            if attempt == attempt_count - 1:
                raise
        else:
            return


def trigger_until_visible(
    trigger: Callable[[], None],
    locator: Locator,
    *,
    attempt_count: int = ATTEMPT_COUNT_DEFAULT,
    timeout_ms: int = BARRIER_TIMEOUT_MS_DEFAULT,
) -> None:
    """
    A function that repeats a trigger until an element becomes visible.

    :param trigger: The action that reveals the element.
    :param locator: The locator for the element that must appear.
    :param attempt_count: The number of times the trigger is retried.
    :param timeout_ms: The time each attempt waits for the element.
    :raises ValueError: If the attempt count is not positive.
    :raises AssertionError: If the element is still hidden after the last attempt.
    """

    _attempt_count_validate(attempt_count)

    for attempt in range(attempt_count):
        trigger()

        try:
            expect(locator).to_be_visible(timeout=timeout_ms)
        except AssertionError:
            if attempt == attempt_count - 1:
                raise
        else:
            return


def wait_until(
    predicate: Callable[[], bool],
    hold: Callable[[int], None],
    *,
    attempt_count_max: int = WAIT_ATTEMPT_COUNT_MAX,
    description: str = '',
    interval_ms: int = WAIT_INTERVAL_MS_DEFAULT,
) -> None:
    """
    A function that polls a condition until it holds or the attempts run out.

    The wait is handed a hold callable rather than sleeping itself, so a demo
    that drives the clock can advance its own timeline between polls instead of
    burning real seconds.

    :param predicate: The condition polled between holds.
    :param hold: The callable that waits for the given number of milliseconds.
    :param attempt_count_max: The number of times the condition is polled.
    :param description: What the condition is waiting for, named in the failure.
    :param interval_ms: The time held between polls.
    :raises ValueError: If the attempt count or the interval is not positive.
    :raises AssertionError: If the condition never holds.
    """

    if attempt_count_max < 1:
        message = f'attempt_count_max must be positive: {attempt_count_max}'
        raise ValueError(message)

    if interval_ms < 1:
        message = f'interval_ms must be positive: {interval_ms}'
        raise ValueError(message)

    for _ in range(attempt_count_max):
        if predicate():
            return

        hold(interval_ms)

    subject = description or 'condition'

    message = f'{subject} did not hold after {attempt_count_max * interval_ms}ms'
    raise AssertionError(message)
