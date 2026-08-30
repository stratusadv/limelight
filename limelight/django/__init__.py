from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from django.conf import settings
from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY
from django.db import OperationalError, connection
from django.urls import reverse

from limelight import barriers

if TYPE_CHECKING:
    from collections.abc import Callable
    from playwright._impl._api_structures import SetCookieParam
    from playwright.sync_api import Page


AUTH_BACKEND_FALLBACK = 'django.contrib.auth.backends.ModelBackend'


class DjangoApplication:
    """
    An application backed by a Django live server.

    This class resolves a route through the URL configuration and signs a user in
    by writing a session, so a demo needs neither a hard-coded path nor a trip
    through the login form.
    """

    def __init__(self, *, live_server: LiveServer) -> None:
        """
        The constructor for the DjangoApplication class.

        :param live_server: The live server the demo runs against.
        """

        self.live_server = live_server

    def login(self, page: Page, user: object) -> None:
        """
        A method that signs a user in by planting a session cookie.

        :param page: The page the demo drives.
        :param user: The user to sign in as.
        :raises TypeError: If the user carries no primary key or session hash.
        """

        if not isinstance(user, SessionUser):
            message = f'user must carry pk and get_session_auth_hash() (got {user!r})'
            raise TypeError(message)

        force_login(page, live_server=self.live_server, user=user)

    def url(self, route: str, **url_kwargs: object) -> str:
        """
        A method that reverses a route name into an absolute URL.

        :param route: The name of the route to reverse.
        :param url_kwargs: The arguments for the route, layered over the defaults.
        :return: The absolute URL to navigate to.
        """

        kwargs = {**self.url_kwargs_defaults(), **url_kwargs}
        path = reverse(route, kwargs=kwargs or None)

        return f'{self.live_server.url}{path}'

    def url_kwargs_defaults(self) -> dict[str, object]:
        """
        A method that supplies the arguments every route in the project takes.

        The base implementation supplies none, so a project whose URLs carry a tenant
        or a locale prefix overrides this rather than repeating the argument at each
        call.

        :return: The arguments layered under the ones a caller passes.
        """

        return {}


class LiveServer(Protocol):
    """A protocol for the server a demo records against."""

    @property
    def url(self) -> str:
        """
        A property that exposes the origin the server listens on.

        :return: The origin of the server.
        """

        ...


@runtime_checkable
class SessionUser(Protocol):
    """
    A protocol for the user a demo signs in as.

    This protocol covers what a session needs: the primary key stored in it, and
    the hash that invalidates it when the password changes.
    """

    @property
    def pk(self) -> object:
        """
        A property that exposes the primary key of the user.

        :return: The primary key of the user.
        """

        ...

    def get_session_auth_hash(self) -> str:
        """
        A method that computes the session hash for the user.

        :return: The hash the session is validated against.
        """

        ...


def auth_backend() -> str:
    """
    A function that names the backend a planted session is attributed to.

    :return: The first configured backend, or the model backend if there are none.
    """

    backends = settings.AUTHENTICATION_BACKENDS

    if backends:
        return backends[0]

    return AUTH_BACKEND_FALLBACK


def database_resilient(predicate: Callable[[], bool]) -> Callable[[], bool]:
    """
    A function that wraps a predicate so a dropped connection reads as not yet.

    A live server thread can close the connection under the test while a query is
    in flight, which raises rather than returning False, and a poll that treats
    that as a failure gives up on a condition that was only a reconnect away.

    :param predicate: The condition to poll.
    :return: The predicate, with a dropped connection closed and reported as False.
    """

    def satisfied() -> bool:
        """
        A function that polls the condition and treats a dropped connection as not yet.

        :return: The result of the condition, or False if the connection was dropped.
        """

        try:
            outcome = predicate()
        except OperationalError:
            connection.close()

            return False
        else:
            return outcome

    return satisfied


def force_login(page: Page, *, live_server: LiveServer, user: SessionUser) -> None:
    """
    A function that signs a user in by writing a session and its cookie.

    :param page: The page the cookie is added to.
    :param live_server: The server the cookie is scoped to.
    :param user: The user to sign in as.
    :raises RuntimeError: If the session carries no key after being saved.
    """

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
    *,
    username: str,
    password: str,
    username_selector: str = 'input[autocomplete="username"]',
    password_selector: str = 'input[autocomplete="current-password"]',
    submit_name: str = 'Sign in',
) -> None:
    """
    A function that signs a user in through the login form.

    The cookies are cleared first, so a session left by an earlier sign-in cannot
    redirect the login page away before the form is filled.

    :param page: The page the form is filled on.
    :param live_server: The server the form is served from.
    :param username: The username to sign in with.
    :param password: The password to sign in with.
    :param username_selector: The selector for the username field.
    :param password_selector: The selector for the password field.
    :param submit_name: The accessible name of the submit button.
    """

    page.context.clear_cookies()

    path = reverse(settings.LOGIN_URL)

    page.goto(f'{live_server.url}{path}')

    page.locator(username_selector).fill(username)
    page.locator(password_selector).fill(password)

    page.get_by_role('button', name=submit_name).click()
    page.wait_for_load_state('networkidle')


def visit(
    page: Page,
    *,
    live_server: LiveServer,
    user: SessionUser,
    route: str,
    **url_kwargs: object,
) -> None:
    """
    A function that signs a user in and opens a route in one step.

    This is the plain-page counterpart to a demo: a test that drives the app
    without narrating it needs the same session and the same route reversal, but
    none of the overlay a Demo carries.

    :param page: The page the route is opened in.
    :param live_server: The server the route is served from.
    :param user: The user to sign in as.
    :param route: The name of the route to reverse.
    :param url_kwargs: The arguments the route takes.
    """

    force_login(page, live_server=live_server, user=user)

    path = reverse(route, kwargs=url_kwargs or None)

    page.goto(f'{live_server.url}{path}')


def wait_until(
    page: Page,
    predicate: Callable[[], bool],
    *,
    attempt_count_max: int = barriers.WAIT_ATTEMPT_COUNT_MAX,
    description: str = '',
    interval_ms: int = barriers.WAIT_INTERVAL_MS_DEFAULT,
) -> None:
    """
    A function that polls a condition against the database until it holds.

    :param page: The page whose timer paces the polling.
    :param predicate: The condition polled between waits.
    :param attempt_count_max: The number of times the condition is polled.
    :param description: What the condition is waiting for, named in the failure.
    :param interval_ms: The time waited between polls.
    :raises AssertionError: If the condition never holds.
    """

    barriers.wait_until(
        database_resilient(predicate),
        page.wait_for_timeout,
        attempt_count_max=attempt_count_max,
        description=description,
        interval_ms=interval_ms,
    )
