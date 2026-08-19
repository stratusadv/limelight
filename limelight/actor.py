from __future__ import annotations

from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Locator

    from limelight.session import DemoSession


class Actor:
    def __init__(self, demo: DemoSession) -> None:
        self._demo = demo

    def _check(self, locator: Locator) -> None:
        self._demo.check(locator)
        self._demo.hold()

    def _click(self, locator: Locator, *, force: bool = False) -> None:
        self._demo.click(locator, force=force)
        self._demo.hold()

    def _fill(self, locator: Locator, value: str) -> None:
        self._demo.fill(locator, value)
        self._demo.hold()

    def _hover(self, locator: Locator) -> None:
        self._demo.hover(locator)
        self._demo.hold()

    def _press(self, locator: Locator, key: str) -> None:
        self._demo.press(locator, key)
        self._demo.hold()

    def _select(self, locator: Locator, option_label: str) -> None:
        self._demo.select(locator, option_label)
        self._demo.hold()

    def _slide(self, *, track: Locator, thumb: Locator) -> None:
        self._demo.slide(track=track, thumb=thumb)
        self._demo.hold()

    def _tab(self, name: str) -> None:
        tab = self._demo.page.get_by_role('tab', name=name)

        self._demo.click(tab)
        self._demo.hold()

    def _teach_click(
        self,
        locator: Locator,
        *,
        headline: str,
        label: str,
        body: str = '',
        step: str = '',
    ) -> None:
        self._teach_focus(locator, headline=headline, label=label, body=body, step=step)

        self._click(locator)

    def _teach_focus(
        self,
        locator: Locator,
        *,
        headline: str,
        label: str,
        body: str = '',
        step: str = '',
    ) -> None:
        self._demo.narrate(headline, body=body, step=step)
        self._demo.spotlight(locator, label=label)
        self._demo.clear_spotlight()

    def _teach_select(self, locator: Locator, *, label: str, option_label: str) -> None:
        self._demo.spotlight(locator, label=label)
        self._demo.clear_spotlight()

        self._select(locator, option_label)

    def _uncheck(self, locator: Locator) -> None:
        self._demo.uncheck(locator)
        self._demo.hold()
