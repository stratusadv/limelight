from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from limelight.config import DemoConfig
from limelight.frames import renderer_for
from limelight.navigator import Navigator
from limelight.overlay import BEAT_MS_DEFAULT
from limelight.presenter import presenter_build

if TYPE_CHECKING:
    from playwright.sync_api import Locator, Page
    from typing import Self

    from limelight.application import Application
    from limelight.ledger import LedgerRow
    from limelight.presenter import Presenter
    from limelight.theme import Theme


SHOT_DIRECTORY_ROOT = 'test-results'


class DemoSession:
    navigator_class = Navigator
    window_print_stubbed = True

    def __init__(self, page: Page, application: Application, *, presenter: Presenter) -> None:
        self.application = application
        self.page = page
        self.presenter = presenter

        self._page_prepare(page)

        self.nav = self.navigator_class(self)

        self.scenes_prepare()

    @classmethod
    def start(
        cls,
        page: Page,
        application: Application,
        *,
        shot_directory_name: str,
        config: DemoConfig | None = None,
        theme: Theme | None = None,
    ) -> Self:
        if config is None:
            config = DemoConfig.from_env()

        shot_directory = Path(SHOT_DIRECTORY_ROOT) / shot_directory_name

        presenter = presenter_build(
            page,
            config,
            shot_directory=shot_directory,
            renderer=renderer_for(page),
            theme=theme,
        )

        return cls(page, application, presenter=presenter)

    def _page_prepare(self, page: Page) -> None:
        if self.window_print_stubbed:
            page.add_init_script('window.print = () => {};')

    def beat(self, ms: int = BEAT_MS_DEFAULT) -> None:
        self.presenter.beat(ms)

    def check(self, locator: Locator) -> None:
        self.presenter.check(locator)

    def clear(self) -> None:
        self.presenter.clear()

    def clear_spotlight(self) -> None:
        self.presenter.clear_spotlight()

    def click(self, locator: Locator, *, force: bool = False) -> None:
        self.presenter.click(locator, force=force)

    def delta_card(
        self,
        title: str,
        rows: list[LedgerRow],
        *,
        kicker: str = '',
        subtitle: str = '',
        ms: int | None = None,
    ) -> None:
        self.presenter.delta_card(title, rows, kicker=kicker, subtitle=subtitle, ms=ms)

    def fill(self, locator: Locator, value: str) -> None:
        self.presenter.fill(locator, value)

    def goto(self, route: str, **url_kwargs: object) -> None:
        self.application.login(self.page)

        url = self.application.url(route, url_kwargs)
        self.page.goto(url)

    def hold(self) -> None:
        self.presenter.hold()

    def hover(self, locator: Locator) -> None:
        self.presenter.hover(locator)

    def login_as(self, user: object) -> None:
        application = self.application.with_user(user)

        self.application = application

        application.login(self.page)

    def narrate(
        self,
        title: str,
        *,
        body: str = '',
        step: str = '',
        tag: str = '',
        kind: str = '',
        ms: int | None = None,
    ) -> None:
        self.presenter.narrate(title, body=body, step=step, tag=tag, kind=kind, ms=ms)

    def press(self, locator: Locator, key: str) -> None:
        self.presenter.press(locator, key)

    def scenes_prepare(self) -> None:
        pass

    def select(self, locator: Locator, option_label: str) -> None:
        self.presenter.select(locator, option_label)

    def shot(self, name: str) -> None:
        self.presenter.shot(name)

    def slide(self, *, track: Locator, thumb: Locator) -> None:
        self.presenter.slide(track=track, thumb=thumb)

    def spotlight(
        self,
        locator: Locator,
        *,
        label: str = '',
        dim: bool = True,
        scroll: bool = True,
        ms: int | None = None,
    ) -> None:
        self.presenter.spotlight(locator, label=label, dim=dim, scroll=scroll, ms=ms)

    def title_card(
        self,
        title: str,
        *,
        kicker: str = '',
        subtitle: str = '',
        ms: int | None = None,
    ) -> None:
        self.presenter.title_card(title, kicker=kicker, subtitle=subtitle, ms=ms)

    def uncheck(self, locator: Locator) -> None:
        self.presenter.uncheck(locator)

    def use_page(self, page: Page) -> None:
        self._page_prepare(page)
        self.presenter.use_page(page)

        self.page = page
