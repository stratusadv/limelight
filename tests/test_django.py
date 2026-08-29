from __future__ import annotations

import pytest

from types import SimpleNamespace
from typing_extensions import override

from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY
from django.db import OperationalError

from limelight.application import Application
from limelight.django import (
    AUTH_BACKEND_FALLBACK,
    DjangoApplication,
    auth_backend,
    force_login,
    sign_in,
    wait_until,
)

from fakes import FakePage


class FakeLiveServer:
    url = 'http://localhost:9999'


class FakeSessionStore:
    def __init__(self) -> None:
        self.session_key: str | None = None
        self.values: dict[str, str] = {}

    def __setitem__(self, key: str, value: str) -> None:
        self.values[key] = value

    def save(self) -> None:
        self.session_key = 'session-key'


class KeylessSessionStore(FakeSessionStore):
    @override
    def save(self) -> None:
        pass


class FakeUser:
    pk = 7

    def get_session_auth_hash(self) -> str:
        return 'hash'


def session_engine_install(monkeypatch: pytest.MonkeyPatch, store: FakeSessionStore) -> None:
    engine_stub = SimpleNamespace(SessionStore=lambda: store)
    settings_stub = SimpleNamespace(
        AUTHENTICATION_BACKENDS=[],
        SESSION_COOKIE_NAME='sessionid',
        SESSION_ENGINE='django.contrib.sessions.backends.db',
    )

    monkeypatch.setattr('limelight.django.import_module', lambda name: engine_stub)
    monkeypatch.setattr('limelight.django.settings', settings_stub)


def test_auth_backend_uses_first_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    settings_stub = SimpleNamespace(AUTHENTICATION_BACKENDS=['app.auth.PortalBackend'])

    monkeypatch.setattr('limelight.django.settings', settings_stub)

    assert auth_backend() == 'app.auth.PortalBackend'


def test_auth_backend_falls_back_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    settings_stub = SimpleNamespace(AUTHENTICATION_BACKENDS=[])

    monkeypatch.setattr('limelight.django.settings', settings_stub)

    assert auth_backend() == AUTH_BACKEND_FALLBACK


def test_django_application_satisfies_protocol() -> None:
    application = DjangoApplication(live_server=FakeLiveServer())

    assert isinstance(application, Application)


class TenancyApplication(DjangoApplication):
    def __init__(self, *, live_server: FakeLiveServer, tenant: str = 'acme') -> None:
        super().__init__(live_server=live_server)

        self.tenant = tenant

    @override
    def url_kwargs_defaults(self) -> dict[str, object]:
        return {'tenant_slug': self.tenant}


def reverse_stub_install(monkeypatch: pytest.MonkeyPatch, calls: list[tuple[str, object]]) -> None:
    def reverse_stub(route: str, kwargs: object = None) -> str:
        call = (route, kwargs)
        calls.append(call)

        return f'/{route}/'

    monkeypatch.setattr('limelight.django.reverse', reverse_stub)


def test_url_passes_no_kwargs_when_none_are_given(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, object]] = []
    reverse_stub_install(monkeypatch, calls)

    application = DjangoApplication(live_server=FakeLiveServer())

    assert application.url('home:dashboard') == 'http://localhost:9999/home:dashboard/'
    assert calls == [('home:dashboard', None)]


def test_url_merges_subclass_defaults_under_call_kwargs(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, object]] = []
    reverse_stub_install(monkeypatch, calls)

    application = TenancyApplication(live_server=FakeLiveServer())

    application.url('order:detail', pk=3)

    assert calls == [('order:detail', {'tenant_slug': 'acme', 'pk': 3})]


def test_url_lets_call_kwargs_win_over_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, object]] = []
    reverse_stub_install(monkeypatch, calls)

    application = TenancyApplication(live_server=FakeLiveServer())

    application.url('order:list', tenant_slug='other')

    assert calls == [('order:list', {'tenant_slug': 'other'})]


def test_force_login_writes_the_session_cookie(monkeypatch: pytest.MonkeyPatch) -> None:
    store = FakeSessionStore()
    session_engine_install(monkeypatch, store)

    page = FakePage()

    force_login(page.as_page(), live_server=FakeLiveServer(), user=FakeUser())

    assert store.values == {
        SESSION_KEY: '7',
        BACKEND_SESSION_KEY: AUTH_BACKEND_FALLBACK,
        HASH_SESSION_KEY: 'hash',
    }

    assert page.context.added_cookies == [{
        'name': 'sessionid',
        'value': 'session-key',
        'url': 'http://localhost:9999',
    }]


def test_force_login_raises_when_the_session_has_no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    session_engine_install(monkeypatch, KeylessSessionStore())

    with pytest.raises(RuntimeError, match='session key'):
        force_login(FakePage().as_page(), live_server=FakeLiveServer(), user=FakeUser())


def test_login_writes_the_session_cookie(monkeypatch: pytest.MonkeyPatch) -> None:
    session_engine_install(monkeypatch, FakeSessionStore())

    page = FakePage()
    application = DjangoApplication(live_server=FakeLiveServer())

    application.login(page.as_page(), FakeUser())

    assert page.context.added_cookies[0]['value'] == 'session-key'


def test_login_rejects_a_user_without_a_session() -> None:
    application = DjangoApplication(live_server=FakeLiveServer())

    with pytest.raises(TypeError, match='get_session_auth_hash'):
        application.login(FakePage().as_page(), object())


def test_sign_in_fills_the_default_selectors(monkeypatch: pytest.MonkeyPatch) -> None:
    settings_stub = SimpleNamespace(LOGIN_URL='auth:sign-in')
    calls: list[tuple[str, object]] = []

    monkeypatch.setattr('limelight.django.settings', settings_stub)
    reverse_stub_install(monkeypatch, calls)

    page = FakePage()

    sign_in(page.as_page(), FakeLiveServer(), username='operator', password='secret')

    assert page.context.clear_count == 1
    assert page.goto_urls == ['http://localhost:9999/auth:sign-in/']

    selectors_expected = [
        'input[autocomplete="username"]',
        'input[autocomplete="current-password"]',
    ]

    assert page.locator_selectors == selectors_expected
    assert page.locator_locators[0].fill_values == ['operator']
    assert page.locator_locators[1].fill_values == ['secret']
    assert page.role_queries == [('button', 'Sign in', False)]
    assert page.role_locators[0].click_count == 1
    assert page.load_states == ['networkidle']


def test_sign_in_honors_overridden_selectors(monkeypatch: pytest.MonkeyPatch) -> None:
    settings_stub = SimpleNamespace(LOGIN_URL='auth:sign-in')

    monkeypatch.setattr('limelight.django.settings', settings_stub)
    reverse_stub_install(monkeypatch, [])

    page = FakePage()

    sign_in(
        page.as_page(),
        FakeLiveServer(),
        username='operator',
        password='secret',
        username_selector='#id_username',
        password_selector='#id_password',
        submit_name='Log in',
    )

    assert page.locator_selectors == ['#id_username', '#id_password']
    assert page.role_queries == [('button', 'Log in', False)]


def test_wait_until_returns_as_soon_as_the_predicate_holds() -> None:
    page = FakePage()
    outcomes = [False, True]

    wait_until(page.as_page(), lambda: outcomes.pop(0))

    assert page.waits_ms == [250]


def test_wait_until_raises_once_attempts_are_exhausted() -> None:
    page = FakePage()

    with pytest.raises(AssertionError, match='condition not met after 750ms'):
        wait_until(page.as_page(), lambda: False, attempt_count_max=3, interval_ms=250)

    assert page.waits_ms == [250, 250, 250]


def test_wait_until_reconnects_after_an_operational_error(monkeypatch: pytest.MonkeyPatch) -> None:
    connection_stub = SimpleNamespace(close_count=0)

    def close() -> None:
        connection_stub.close_count += 1

    connection_stub.close = close

    monkeypatch.setattr('limelight.django.connection', connection_stub)

    page = FakePage()
    attempts: list[int] = []

    def predicate() -> bool:
        attempts.append(len(attempts))

        if len(attempts) == 1:
            raise OperationalError

        return True

    wait_until(page.as_page(), predicate, attempt_count_max=3)

    assert connection_stub.close_count == 1
    assert page.waits_ms == [250]
