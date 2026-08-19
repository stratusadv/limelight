from __future__ import annotations

from typing_extensions import TYPE_CHECKING

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, expect

if TYPE_CHECKING:
    import re

    from playwright.sync_api import Locator, Page
    from typing_extensions import Callable


ATTEMPT_COUNT_DEFAULT = 3
BARRIER_TIMEOUT_MS_DEFAULT = 5000


def _attempt_count_validate(attempt_count: int) -> None:
    if attempt_count < 1:
        message = f'attempt_count must be positive: {attempt_count}'
        raise ValueError(message)


def trigger_until_navigation(
    page: Page,
    trigger: Callable[[], None],
    *,
    url_pattern: str | re.Pattern[str],
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
    url_fragment: str,
    attempt_count: int = ATTEMPT_COUNT_DEFAULT,
    timeout_ms: int = BARRIER_TIMEOUT_MS_DEFAULT,
) -> None:
    _attempt_count_validate(attempt_count)

    if not url_fragment:
        message = 'url_fragment must not be empty'
        raise ValueError(message)

    for attempt in range(attempt_count):
        try:
            with page.expect_response(
                lambda response: url_fragment in response.url,
                timeout=timeout_ms,
            ):
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
