from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Callable
    from playwright.sync_api import Page


@runtime_checkable
class Application(Protocol):
    """
    A protocol for the application a demo records.

    This protocol covers the two things a demo needs from the project under
    test: a way to sign a user in, and a way to turn a route into a URL.
    """

    def login(self, page: Page, user: object) -> None:
        """
        A method that signs a user into the application.

        :param page: The page the demo drives.
        :param user: The user to sign in as.
        """

        ...

    def url(self, route: str, **url_kwargs: object) -> str:
        """
        A method that resolves a route into an absolute URL.

        :param route: The route to resolve.
        :param url_kwargs: The arguments filled into the route.
        :return: The absolute URL to navigate to.
        """

        ...


class StaticApplication:
    """
    An application backed by a fixed base URL.

    This class serves any site that is already running, so a demo can record
    against a deployed environment without a Django project behind it.
    """

    def __init__(
        self,
        *,
        base_url: str,
        login: Callable[[Page, object], None] | None = None,
    ) -> None:
        """
        The constructor for the StaticApplication class.

        :param base_url: The origin every route is resolved against.
        :param login: The callable that signs a user in, or None for a site that needs no login.
        :raises ValueError: If the base URL is empty.
        """

        base_url_clean = base_url.strip().rstrip('/')

        if not base_url_clean:
            message = f'base_url must not be empty (got "{base_url}")'
            raise ValueError(message)

        self.base_url = base_url_clean
        self._login = login

    def login(self, page: Page, user: object) -> None:
        """
        A method that signs a user in through the configured callable.

        :param page: The page the demo drives.
        :param user: The user to sign in as.
        """

        if self._login is not None:
            self._login(page, user)

    def url(self, route: str, **url_kwargs: object) -> str:
        """
        A method that joins a route onto the base URL.

        :param route: The route to resolve, with or without a leading slash.
        :param url_kwargs: The arguments filled into the route.
        :return: The absolute URL to navigate to.
        :raises ValueError: If the route is empty.
        """

        if not route.strip():
            message = f'route must not be empty (got "{route}")'
            raise ValueError(message)

        path = route.format(**url_kwargs)

        if not path.startswith('/'):
            path = f'/{path}'

        return f'{self.base_url}{path}'
