from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from django.conf import settings
from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY
from django.db import OperationalError, connection
from django.urls import reverse

if TYPE_CHECKING:
    from collections.abc import Callable
    from playwright._impl._api_structures import SetCookieParam
    from playwright.sync_api import Page
    from typing import Self


AUTH_BACKEND_FALLBACK = 'django.contrib.auth.backends.ModelBackend'


class DjangoApplication:
    def __init__(self, *, live_server: LiveServer, user: SessionUser) -> None:
        if live_server is None:
            message = 'live_server must not be None'
            raise ValueError(message)

        if user is None:
            message = 'user must not be None'
            raise ValueError(message)

        self.live_server = live_server
        self.user = user

    def login(self, page: Page) -> None:
        force_login(page, live_server=self.live_server, user=self.user)

    def url(self, route: str, url_kwargs: dict[str, object]) -> str:
        kwargs = {**self.url_kwargs_defaults(), **url_kwargs}
        path = reverse(route, kwargs=kwargs or None)

        return f'{self.live_server.url}{path}'

    def url_kwargs_defaults(self) -> dict[str, object]:
        return {}

    def with_user(self, user: object) -> Self:
        if not isinstance(user, SessionUser):
            message = f'user must satisfy SessionUser (got {type(user).__name__})'
            raise TypeError(message)

        return type(self)(
            live_server=self.live_server,
            user=user,
        )


@runtime_checkable
class LiveServer(Protocol):
    @property
    def url(self) -> str: ...


@runtime_checkable
class SessionUser(Protocol):
    @property
    def pk(self) -> object: ...

    def get_session_auth_hash(self) -> str: ...


def auth_backend() -> str:
    backends = settings.AUTHENTICATION_BACKENDS

    if backends:
        return backends[0]

    return AUTH_BACKEND_FALLBACK


def force_login(page: Page, *, live_server: LiveServer, user: SessionUser) -> None:
    engine = import_module(settings.SESSION_ENGINE)
    session = engine.SessionStore()

    session[SESSION_KEY] = str(user.pk)
    session[BACKEND_SESSION_KEY] = auth_backend()
    session[HASH_SESSION_KEY] = user.get_session_auth_hash()
    session.save()

    if session.session_key is None:
        message = 'session key is missing after save; is the session engine configured?'
        raise RuntimeError(message)

    cookies: list[SetCookieParam] = [{
        'name': settings.SESSION_COOKIE_NAME,
        'value': session.session_key,
        'url': live_server.url,
    }]

    page.context.add_cookies(cookies)


def sign_in(
    page: Page,
    live_server: LiveServer,
    username: str,
    password: str,
    *,
    username_selector: str = 'input[autocomplete="username"]',
    password_selector: str = 'input[autocomplete="current-password"]',
    submit_name: str = 'Sign in',
) -> None:
    page.context.clear_cookies()

    path = reverse(settings.LOGIN_URL)

    page.goto(f'{live_server.url}{path}')

    page.locator(username_selector).fill(username)
    page.locator(password_selector).fill(password)

    page.get_by_role('button', name=submit_name).click()
    page.wait_for_load_state('networkidle')


def visit(page: Page, *, live_server: LiveServer, user: SessionUser, url_name: str, **url_kwargs: object) -> None:
    force_login(page, live_server=live_server, user=user)

    path = reverse(url_name, kwargs=url_kwargs or None)

    page.goto(f'{live_server.url}{path}')


def wait_until(
    page: Page,
    predicate: Callable[[], bool],
    *,
    attempts_max: int = 40,
    interval_ms: int = 250,
) -> None:
    for _ in range(attempts_max):
        try:
            satisfied = predicate()
        except OperationalError:
            connection.close()

            satisfied = False

        if satisfied:
            return

        page.wait_for_timeout(interval_ms)

    message = f'condition not met after {attempts_max * interval_ms}ms'
    raise AssertionError(message)
