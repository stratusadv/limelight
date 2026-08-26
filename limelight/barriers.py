from __future__ import annotations

from typing import TYPE_CHECKING

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, expect

if TYPE_CHECKING:
    import re

    from collections.abc import Callable
    from playwright.sync_api import Locator, Page, Response


ATTEMPT_COUNT_DEFAULT = 3
BARRIER_TIMEOUT_MS_DEFAULT = 5000


def _attempt_count_validate(attempt_count: int) -> None:
    if attempt_count < 1:
        message = f'attempt_count must be positive: {attempt_count}'
        raise ValueError(message)


def _url_fragment_predicate(url_fragment: str) -> Callable[[Response], bool]:
    def matches(response: Response) -> bool:
        return url_fragment in response.url

    return matches


def trigger_until_navigation(
    page: Page,
    trigger: Callable[[], None],
    *,
    url_pattern: str | re.Pattern[str] | None = None,
    attempt_count: int = ATTEMPT_COUNT_DEFAULT,
    timeout_ms: int = BARRIER_TIMEOUT_MS_DEFAULT,
) -> None:
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
