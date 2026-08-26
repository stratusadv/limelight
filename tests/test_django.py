from __future__ import annotations

import pytest

from types import SimpleNamespace
from typing import cast, override

from django.db import OperationalError

from limelight.application import Application
from limelight.django import (
    AUTH_BACKEND_FALLBACK,
    DjangoApplication,
    LiveServer,
    SessionUser,
    auth_backend,
    sign_in,
    wait_until,
)

from fakes import FakePage


class FakeLiveServer:
    url = 'http://localhost:9999'


class FakeUser:
    pk = 7

    def get_session_auth_hash(self) -> str:
        return 'hash'


def test_auth_backend_uses_first_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    settings_stub = SimpleNamespace(AUTHENTICATION_BACKENDS=['app.auth.PortalBackend'])

    monkeypatch.setattr('limelight.django.settings', settings_stub)

    assert auth_backend() == 'app.auth.PortalBackend'


def test_auth_backend_falls_back_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    settings_stub = SimpleNamespace(AUTHENTICATION_BACKENDS=[])

    monkeypatch.setattr('limelight.django.settings', settings_stub)

    assert auth_backend() == AUTH_BACKEND_FALLBACK


def test_django_application_satisfies_protocol() -> None:
    application = DjangoApplication(live_server=FakeLiveServer(), user=FakeUser())

    assert isinstance(application, Application)


def test_fakes_satisfy_their_protocols() -> None:
    assert isinstance(FakeLiveServer(), LiveServer)
    assert isinstance(FakeUser(), SessionUser)


def test_with_user_builds_new_application() -> None:
    application = DjangoApplication(live_server=FakeLiveServer(), user=FakeUser())
    user_new = FakeUser()

    application_new = application.with_user(user_new)

    assert application_new is not application
    assert application_new.user is user_new
    assert application_new.live_server is application.live_server


def test_with_user_rejects_non_session_user() -> None:
    application = DjangoApplication(live_server=FakeLiveServer(), user=FakeUser())

    with pytest.raises(TypeError, match='SessionUser'):
        application.with_user(object())


def test_live_server_required() -> None:
    with pytest.raises(ValueError, match='live_server'):
        DjangoApplication(live_server=cast('LiveServer', None), user=FakeUser())


def test_user_required() -> None:
    with pytest.raises(ValueError, match='user'):
        DjangoApplication(live_server=FakeLiveServer(), user=cast('SessionUser', None))


class TenancyApplication(DjangoApplication):
    def __init__(self, *, live_server: LiveServer, user: SessionUser, tenant: str = 'acme') -> None:
        super().__init__(live_server=live_server, user=user)

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

    application = DjangoApplication(live_server=FakeLiveServer(), user=FakeUser())

    assert application.url('home:dashboard', {}) == 'http://localhost:9999/home:dashboard/'
    assert calls == [('home:dashboard', None)]


def test_url_merges_subclass_defaults_under_call_kwargs(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, object]] = []
    reverse_stub_install(monkeypatch, calls)

    application = TenancyApplication(live_server=FakeLiveServer(), user=FakeUser())
    url_kwargs: dict[str, object] = {'pk': 3}

    application.url('order:detail', url_kwargs)

    assert calls == [('order:detail', {'tenant_slug': 'acme', 'pk': 3})]


def test_url_lets_call_kwargs_win_over_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, object]] = []
    reverse_stub_install(monkeypatch, calls)

    application = TenancyApplication(live_server=FakeLiveServer(), user=FakeUser())
    url_kwargs: dict[str, object] = {'tenant_slug': 'other'}

    application.url('order:list', url_kwargs)

    assert calls == [('order:list', {'tenant_slug': 'other'})]


def test_with_user_keeps_the_subclass() -> None:
    application = TenancyApplication(live_server=FakeLiveServer(), user=FakeUser())

    application_new = application.with_user(FakeUser())

    assert isinstance(application_new, TenancyApplication)


def test_sign_in_fills_the_default_selectors(monkeypatch: pytest.MonkeyPatch) -> None:
    settings_stub = SimpleNamespace(LOGIN_URL='auth:sign-in')
    calls: list[tuple[str, object]] = []

    monkeypatch.setattr('limelight.django.settings', settings_stub)
    reverse_stub_install(monkeypatch, calls)

    page = FakePage()

    sign_in(page.as_page(), cast('LiveServer', FakeLiveServer()), 'operator', 'secret')

    assert page.context.clear_count == 1
    assert page.goto_urls == ['http://localhost:9999/auth:sign-in/']
    assert page.locator_selectors == ['input[autocomplete="username"]', 'input[autocomplete="current-password"]']
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
        cast('LiveServer', FakeLiveServer()),
        'operator',
        'secret',
        username_selector='#id_username',
        password_selector='#id_password',  # noqa: S106
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
        wait_until(page.as_page(), lambda: False, attempts_max=3, interval_ms=250)

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

    wait_until(page.as_page(), predicate, attempts_max=3)

    assert connection_stub.close_count == 1
    assert page.waits_ms == [250]
