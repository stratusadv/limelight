from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Callable
    from playwright.sync_api import Page


@runtime_checkable
class Application(Protocol):
    def login(self, page: Page) -> None: ...

    def url(self, route: str, url_kwargs: dict[str, object]) -> str: ...

    def with_user(self, user: object) -> Application: ...


class StaticApplication:
    def __init__(
        self,
        *,
        base_url: str,
        login: Callable[[Page, object], None] | None = None,
        user: object = None,
    ) -> None:
        base_url_clean = base_url.strip().rstrip('/')

        if not base_url_clean:
            message = f'base_url must not be empty (got "{base_url}")'
            raise ValueError(message)

        self.base_url = base_url_clean
        self.user = user
        self._login = login

    def login(self, page: Page) -> None:
        if self._login is not None:
            self._login(page, self.user)

    def url(self, route: str, url_kwargs: dict[str, object]) -> str:
        path = route.format(**url_kwargs)

        if not path.startswith('/'):
            path = f'/{path}'

        return f'{self.base_url}{path}'

    def with_user(self, user: object) -> StaticApplication:
        return StaticApplication(
            base_url=self.base_url,
            login=self._login,
            user=user,
        )
