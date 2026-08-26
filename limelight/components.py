from __future__ import annotations

from typing import TYPE_CHECKING

from playwright.sync_api import expect

from limelight.barriers import trigger_until_visible
from limelight.gestures import slide_to_end

if TYPE_CHECKING:
    from playwright.sync_api import Locator, Page
    from typing import Self


class Modal:
    root_selector = ''

    def __init__(self, page: Page) -> None:
        self._page = page

    def choose(self, option_text: str) -> None:
        option = self.option(option_text)

        expect(option).to_be_visible()

        option.click()

    def open_with(self, trigger: Locator, *, reveals_text: str) -> None:
        trigger_until_visible(trigger.click, self.option(reveals_text))

    def option(self, text: str) -> Locator:
        return self.root.get_by_text(text, exact=True)

    @property
    def root(self) -> Locator:
        if self.root_selector:
            return self._page.locator(self.root_selector)

        return self._page.get_by_role('dialog')


class SearchAndSelect:
    choice_selector = '.list-group-item'
    dropdown_selector = 'div.list-group'
    search_placeholder = 'Search...'
    toggle_selector = 'button.form-control'

    def __init__(self, root: Locator) -> None:
        self._root = root

    @classmethod
    def within(cls, container: Locator) -> Self:
        root = (
            container
            .locator('div.position-relative')
            .filter(has=container.page.locator(cls.toggle_selector))
            .last
        )

        return cls(root)

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
        self.search_field.fill(search or label)
        self.choice(label, exact=exact).click(force=True)

        expect(self.dropdown).to_be_hidden()
        expect(self.toggle).to_contain_text(label)

    def open(self) -> None:
        trigger_until_visible(self.toggle.click, self.dropdown)


class SlideButton:
    def __init__(self, page: Page) -> None:
        self._page = page

    def slide(self) -> None:
        slide_to_end(self._page, track=self.track, thumb=self.thumb)

    @property
    def thumb(self) -> Locator:
        return self._page.locator('[x-ref="thumb"]')

    @property
    def track(self) -> Locator:
        return self._page.locator('[x-ref="track"]')
