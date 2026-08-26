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
    from django.db import connections

    return any(
        connection.vendor == 'sqlite' and connection.is_in_memory_db()
        for connection in connections.all()
    )


def _live_server_open() -> Generator[LiveServer]:
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
    page.set_default_navigation_timeout(navigation_timeout_ms)

    return page


@pytest.fixture(scope='session')
def demo_navigation_timeout_ms() -> int:
    return NAVIGATION_TIMEOUT_MS


@pytest.fixture(scope='session')
def live_server() -> Iterator[LiveServer]:
    yield from _live_server_open()


@pytest.fixture
def page(page: Page, demo_navigation_timeout_ms: int) -> Page:
    return _page_prepare(page, demo_navigation_timeout_ms)


def pytest_configure(config: pytest.Config) -> None:
    os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')
