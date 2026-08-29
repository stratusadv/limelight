from __future__ import annotations

import os
import sys

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import django.test.testcases as django_testcases

from limelight.django import pytest_plugin
from limelight.django.server import SequentialLiveServerThread

from fakes import fixture_function

if TYPE_CHECKING:
    import pytest

    from collections.abc import Generator

    from playwright.sync_api import Page
    from pytest_django.live_server_helper import LiveServer


class FakeConnection:
    def __init__(self, *, vendor: str, in_memory: bool) -> None:
        self.vendor = vendor
        self._in_memory = in_memory

    def is_in_memory_db(self) -> bool:
        return self._in_memory


class FakePlaywrightPage:
    def __init__(self) -> None:
        self.navigation_timeouts: list[int] = []

    def as_page(self) -> Page:
        return cast('Page', self)

    def set_default_navigation_timeout(self, timeout_ms: int) -> None:
        self.navigation_timeouts.append(timeout_ms)


def connections_stub_install(
    monkeypatch: pytest.MonkeyPatch,
    connections: list[FakeConnection],
) -> None:
    monkeypatch.setattr('django.db.connections', SimpleNamespace(all=lambda: connections))


def live_server_open(
    monkeypatch: pytest.MonkeyPatch,
    observed: list[object],
) -> Generator[LiveServer]:
    class LiveServerStub:
        def __init__(self, host: str) -> None:
            self.host = host

            observed.append(django_testcases.LiveServerThread)

        def stop(self) -> None:
            pass

    helper = SimpleNamespace(LiveServer=LiveServerStub)

    monkeypatch.setitem(sys.modules, 'pytest_django.live_server_helper', helper)

    return pytest_plugin._live_server_open()


def test_in_memory_sqlite_selects_the_sequential_thread(monkeypatch: pytest.MonkeyPatch) -> None:
    connections = [FakeConnection(vendor='sqlite', in_memory=True)]
    observed: list[object] = []

    connections_stub_install(monkeypatch, connections)

    thread_class_original = django_testcases.LiveServerThread
    servers = live_server_open(monkeypatch, observed)

    next(servers)

    assert observed == [SequentialLiveServerThread]
    assert django_testcases.LiveServerThread is thread_class_original

    servers.close()


def test_other_databases_keep_the_stock_thread(monkeypatch: pytest.MonkeyPatch) -> None:
    connections = [FakeConnection(vendor='postgresql', in_memory=False)]
    observed: list[object] = []

    connections_stub_install(monkeypatch, connections)

    thread_class_original = django_testcases.LiveServerThread
    servers = live_server_open(monkeypatch, observed)

    next(servers)

    assert observed == [thread_class_original]
    assert django_testcases.LiveServerThread is thread_class_original

    servers.close()


def test_file_backed_sqlite_keeps_the_stock_thread(monkeypatch: pytest.MonkeyPatch) -> None:
    connections = [FakeConnection(vendor='sqlite', in_memory=False)]

    connections_stub_install(monkeypatch, connections)

    assert pytest_plugin._database_needs_serial_server() is False


def test_page_applies_the_navigation_timeout() -> None:
    page = FakePlaywrightPage()

    prepared = pytest_plugin._page_prepare(page.as_page(), pytest_plugin.NAVIGATION_TIMEOUT_MS)

    assert prepared is page
    assert page.navigation_timeouts == [pytest_plugin.NAVIGATION_TIMEOUT_MS]


def test_configure_allows_async_unsafe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv('DJANGO_ALLOW_ASYNC_UNSAFE', raising=False)

    pytest_plugin.pytest_configure(cast('pytest.Config', None))

    assert os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] == 'true'


def test_the_navigation_timeout_fixture_carries_the_default() -> None:
    timeout_ms = fixture_function(pytest_plugin.demo_navigation_timeout_ms)()

    assert timeout_ms == pytest_plugin.NAVIGATION_TIMEOUT_MS


def test_the_page_fixture_applies_the_navigation_timeout() -> None:
    page = FakePlaywrightPage()

    prepared = fixture_function(pytest_plugin.page)(page.as_page(), 4321)

    assert prepared is page
    assert page.navigation_timeouts == [4321]


def test_the_live_server_fixture_stops_the_server_it_opened(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stops: list[str] = []

    class LiveServerStub:
        def __init__(self, host: str) -> None:
            self.host = host

        def stop(self) -> None:
            stops.append(self.host)

    helper = SimpleNamespace(LiveServer=LiveServerStub)

    connections_stub_install(monkeypatch, [FakeConnection(vendor='postgresql', in_memory=False)])
    monkeypatch.setitem(sys.modules, 'pytest_django.live_server_helper', helper)

    servers = fixture_function(pytest_plugin.live_server)()
    server = next(servers)

    assert isinstance(server, LiveServerStub)
    assert stops == []
    assert next(servers, 'exhausted') == 'exhausted'
    assert stops == ['localhost']
