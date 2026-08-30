from __future__ import annotations

from typing import TYPE_CHECKING

from playwright.sync_api import expect

from limelight.components.modal import ELEMENT_WAIT_TIMEOUT_MS

if TYPE_CHECKING:
    from playwright.sync_api import Locator, Page

    from limelight.demo import Demo


class Dropdown:
    """
    A driver for a menu that opens from a trigger and lists its actions.

    This class opens the menu, reads the actions it offers, and picks one by the
    text a viewer reads. The trigger is brought into view before it is clicked,
    because a menu opened offscreen draws its spotlight over nothing, and the
    actions are filtered to the visible ones, because a page holding one menu per
    row keeps every closed menu in the markup.

    The trigger, the menu, and its actions are all scoped to the region that owns
    them. Handing a row or a card as the root is what separates one row's menu
    from the fifty others on the page, and it is what keeps a menu left open
    elsewhere from answering for this one.

    The defaults describe the Bootstrap markup this menu is usually built from.
    A project whose menu is drawn differently subclasses this and overrides the
    selectors it needs.

    ::

        class RowMenu(Dropdown):
            trigger_selector = '.bi-three-dots-vertical'
    """

    item_selector = '.dropdown-item'
    menu_selector = '.dropdown-menu'
    trigger_selector = '.dropdown-toggle'

    def __init__(self, demo: Demo, root: Locator | None = None) -> None:
        """
        The constructor for the Dropdown class.

        :param demo: The demo driving the browser.
        :param root: The region holding the trigger, or None for the whole page.
        """

        self.demo = demo
        self.root = root

    @property
    def _scope(self) -> Locator | Page:
        """
        A property that gets the region the menu is looked up inside.

        :return: The root the menu was built with, or the whole page.
        """

        return self.root if self.root is not None else self.demo.page

    @property
    def items(self) -> Locator:
        """
        A property that gets the actions the open menu offers.

        :return: The locator for the visible menu items.
        """

        return self._scope.locator(self.item_selector).filter(visible=True)

    @property
    def menu(self) -> Locator:
        """
        A property that gets the open menu.

        :return: The locator for the visible menu.
        """

        return self._scope.locator(self.menu_selector).filter(visible=True).first

    @property
    def trigger(self) -> Locator:
        """
        A property that gets the control the menu opens from.

        :return: The locator for the trigger.
        """

        return self._scope.locator(self.trigger_selector).first

    def choose(self, text: str, *, label: str = '') -> None:
        """
        A method that opens the menu and picks one of its actions.

        :param text: The text shown on the action.
        :param label: The spotlight caption for the action, or an empty string
            to highlight nothing.
        :raises AssertionError: If the trigger or the action never appears.
        """

        self.open()

        item = self.item(text)

        expect(item).to_be_visible(timeout=ELEMENT_WAIT_TIMEOUT_MS)

        if label:
            self.demo.spotlight(item, label=label)

        self.demo.click(item)
        self.demo.pause()

    def item(self, text: str) -> Locator:
        """
        A method that gets the action a text names.

        :param text: The text shown on the action.
        :return: The locator for the menu item.
        """

        return self.items.filter(has_text=text).first

    def open(self, *, label: str = '') -> None:
        """
        A method that opens the menu.

        :param label: The spotlight caption for the trigger, or an empty string
            to highlight nothing.
        :raises AssertionError: If the trigger never appears.
        """

        trigger = self.trigger

        expect(trigger).to_be_visible(timeout=ELEMENT_WAIT_TIMEOUT_MS)

        trigger.scroll_into_view_if_needed()

        if label:
            self.demo.spotlight(trigger, label=label)

        self.demo.click(trigger)

        expect(self.menu).to_be_visible(timeout=ELEMENT_WAIT_TIMEOUT_MS)
