from __future__ import annotations

from importlib import import_module
from typing_extensions import TYPE_CHECKING, Protocol, runtime_checkable

from django.conf import settings
from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY
from django.urls import reverse

if TYPE_CHECKING:
    from playwright._impl._api_structures import SetCookieParam
    from playwright.sync_api import Page


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
        path = reverse(route, kwargs=url_kwargs or None)

        return f'{self.live_server.url}{path}'

    def with_user(self, user: object) -> DjangoApplication:
        if not isinstance(user, SessionUser):
            message = f'user must satisfy SessionUser (got {type(user).__name__})'
            raise TypeError(message)

        return DjangoApplication(
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


def visit(page: Page, *, live_server: LiveServer, user: SessionUser, url_name: str, **url_kwargs: object) -> None:
    force_login(page, live_server=live_server, user=user)

    path = reverse(url_name, kwargs=url_kwargs or None)

    page.goto(f'{live_server.url}{path}')
