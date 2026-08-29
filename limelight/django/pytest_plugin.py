from __future__ import annotations

import os

import pytest

from typing import TYPE_CHECKING, Any

from limelight.django.server import SequentialLiveServerThread

if TYPE_CHECKING:
    from collections.abc import Generator, Iterator

    from playwright.sync_api import Page
    from pytest_django.live_server_helper import LiveServer


NAVIGATION_TIMEOUT_MS = 60000


def _database_needs_serial_server() -> bool:
    """
    A function that reports whether the database forces a single-threaded server.

    An in-memory SQLite database lives inside one connection, so a threaded server
    that opens a second connection sees an empty database rather than the fixtures
    the test wrote.

    :return: True if any connection is an in-memory SQLite database, False otherwise.
    """

    from django.db import connections

    return any(
        connection.vendor == 'sqlite' and connection.is_in_memory_db()
        for connection in connections.all()
    )


def _live_server_open() -> Generator[LiveServer]:
    """
    A function that opens the live server and stops it when the session ends.

    The thread class is swapped on the Django module for the duration of the
    construction alone, because the live server reads it at that moment and leaving
    the swap in place would change every other server in the session.

    :return: The generator that yields the running server.
    """

    import django.test.testcases as django_testcases

    from pytest_django.live_server_helper import LiveServer

    testcases: Any = django_testcases
    thread_class_original = testcases.LiveServerThread

    if _database_needs_serial_server():
        testcases.LiveServerThread = SequentialLiveServerThread

    try:
        server = LiveServer('localhost')
    finally:
        testcases.LiveServerThread = thread_class_original

    yield server

    server.stop()


def _page_prepare(page: Page, navigation_timeout_ms: int) -> Page:
    """
    A function that applies the demo timeouts to a page.

    :param page: The page to prepare.
    :param navigation_timeout_ms: The time a navigation is allowed to take.
    :return: The prepared page.
    """

    page.set_default_navigation_timeout(navigation_timeout_ms)

    return page


@pytest.fixture(scope='session')
def demo_navigation_timeout_ms() -> int:
    """
    A fixture that supplies the navigation timeout for a demo.

    :return: The time a navigation is allowed to take.
    """

    return NAVIGATION_TIMEOUT_MS


@pytest.fixture(scope='session')
def live_server() -> Iterator[LiveServer]:
    """
    A fixture that runs a live server for the session.

    :return: The iterator that yields the running server.
    """

    yield from _live_server_open()


@pytest.fixture
def page(page: Page, demo_navigation_timeout_ms: int) -> Page:
    """
    A fixture that supplies a page carrying the demo timeouts.

    :param page: The page supplied by the Playwright plugin.
    :param demo_navigation_timeout_ms: The time a navigation is allowed to take.
    :return: The prepared page.
    """

    return _page_prepare(page, demo_navigation_timeout_ms)


def pytest_configure(config: pytest.Config) -> None:
    """
    A function that prepares the environment before the tests are collected.

    Django refuses a synchronous database call from a thread that carries an event
    loop, which a live server run under Playwright always does, so the check is
    disabled for the session.

    :param config: The pytest configuration.
    """

    os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')
