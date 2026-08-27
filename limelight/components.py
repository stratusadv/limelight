from __future__ import annotations

from typing import TYPE_CHECKING

from playwright.sync_api import expect

from limelight.barriers import trigger_until_visible

if TYPE_CHECKING:
    from playwright.sync_api import Locator
    from typing import Self

    from limelight.session import DemoSession


class Modal:
    root_selector = ''

    def __init__(self, demo: DemoSession) -> None:
        self._demo = demo

    def choose(self, option_text: str) -> None:
        option = self.option(option_text)

        expect(option).to_be_visible()

        self._demo.click(option)

    def open_with(self, trigger: Locator, *, reveals_text: str) -> None:
        def opened() -> None:
            self._demo.click(trigger)

        trigger_until_visible(opened, self.option(reveals_text))

    def option(self, text: str) -> Locator:
        return self.root.get_by_text(text, exact=True)

    @property
    def root(self) -> Locator:
        if self.root_selector:
            return self._demo.page.locator(self.root_selector)

        return self._demo.page.get_by_role('dialog')


class SearchAndSelect:
    choice_selector = '.list-group-item'
    dropdown_selector = 'div.list-group'
    search_placeholder = 'Search...'
    toggle_selector = 'button.form-control'

    def __init__(self, demo: DemoSession, root: Locator) -> None:
        self._demo = demo
        self._root = root

    @classmethod
    def within(cls, demo: DemoSession, container: Locator) -> Self:
        root = (
            container
            .locator('div.position-relative')
            .filter(has=container.page.locator(cls.toggle_selector))
            .last
        )

        return cls(demo, root)

    @property
    def choices(self) -> Locator:
        return self._root.locator(self.choice_selector)

    @property
    def dropdown(self) -> Locator:
        return self._root.locator(self.dropdown_selector)

    @property
    def search_field(self) -> Locator:
        return self._root.get_by_placeholder(self.search_placeholder)

    @property
    def toggle(self) -> Locator:
        return self._root.locator(self.toggle_selector)

    def choice(self, label: str, *, exact: bool = False) -> Locator:
        if exact:
            return self.choices.filter(has=self._root.page.get_by_text(label, exact=True)).first

        return self.choices.filter(has_text=label).first

    def choose(self, label: str, *, search: str = '', exact: bool = False) -> None:
        self._demo.fill(self.search_field, search or label)
        self._demo.click(self.choice(label, exact=exact), force=True)

        expect(self.dropdown).to_be_hidden()
        expect(self.toggle).to_contain_text(label)

    def open(self) -> None:
        def opened() -> None:
            self._demo.click(self.toggle)

        trigger_until_visible(opened, self.dropdown)


class SlideButton:
    def __init__(self, demo: DemoSession) -> None:
        self._demo = demo

    def slide(self) -> None:
        self._demo.slide(track=self.track, thumb=self.thumb)

    @property
    def thumb(self) -> Locator:
        return self._demo.page.locator('[x-ref="thumb"]')

    @property
    def track(self) -> Locator:
        return self._demo.page.locator('[x-ref="track"]')
