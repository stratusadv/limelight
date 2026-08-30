from __future__ import annotations

from typing import TYPE_CHECKING

from playwright.sync_api import expect

from limelight.barriers import trigger_until_visible

if TYPE_CHECKING:
    from typing import Self

    from playwright.sync_api import Locator, Page


class SearchAndSelect:
    """
    A driver for a dropdown field that picks one choice.

    This class opens the field and picks a choice by the label a viewer reads,
    waiting for the dropdown to close and the toggle to carry the choice rather
    than assuming the click landed.

    A search box is used when the field offers one, because the same widget is
    commonly drawn twice: once with a filter over a long list, and once without
    for a short one. A field with no box is picked from directly.

    The defaults describe the Bootstrap markup this widget is usually built from.
    A project whose field is drawn differently subclasses this and overrides the
    selectors it needs.

    ::

        class TypeaheadSelect(SearchAndSelect):
            choice_selector = 'li[role="option"]'
            dropdown_selector = 'ul[role="listbox"]'
            toggle_selector = 'button[aria-haspopup="listbox"]'
    """

    choice_selector = '.list-group-item'
    dropdown_selector = 'div.list-group'
    field_selector = 'input[name="{name}"]'
    root_selector = 'div.position-relative'
    search_placeholder = 'Search...'
    sibling_selector = 'xpath=following-sibling::div[1]'
    toggle_selector = 'button.form-control'

    def __init__(self, root: Locator) -> None:
        """
        The constructor for the SearchAndSelect class.

        :param root: The locator for the element wrapping the toggle and its dropdown.
        """

        self.root = root

    @classmethod
    def named(cls, scope: Locator | Page, name: str) -> Self:
        """
        A method that finds the field a form field name identifies.

        The widget is drawn beside the hidden input that carries its value, so the
        field is found by name and the widget is taken as the sibling next to it.
        This is how a form holding several of these fields addresses one of them.

        :param scope: The page, form, or modal the field is searched in.
        :param name: The name of the form field the widget writes to.
        :return: The driver for the field.
        :raises ValueError: If the name is empty.
        """

        if not name.strip():
            message = f'name must not be empty (got "{name}")'
            raise ValueError(message)

        field = scope.locator(cls.field_selector.format(name=name)).first
        root = field.locator(cls.sibling_selector)

        return cls(root)

    @classmethod
    def within(cls, container: Locator) -> Self:
        """
        A method that finds the search-and-select field inside a container.

        The last match is taken, because a form that stacks several of these fields
        opens the one nearest the bottom of the markup last.

        :param container: The locator for the form or modal holding the field.
        :return: The driver for the field.
        """

        root = (
            container
            .locator(cls.root_selector)
            .filter(has=container.page.locator(cls.toggle_selector))
            .last
        )

        return cls(root)

    @property
    def choices(self) -> Locator:
        """
        A property that gets every choice the open dropdown offers.

        :return: The locator for the choices.
        """

        return self.root.locator(self.choice_selector)

    @property
    def dropdown(self) -> Locator:
        """
        A property that gets the dropdown the toggle opens.

        :return: The locator for the dropdown.
        """

        return self.root.locator(self.dropdown_selector)

    @property
    def is_searchable(self) -> bool:
        """
        A property that reports whether the open dropdown offers a search box.

        :return: True if the field can be filtered, False otherwise.
        """

        return self.search_field.count() > 0

    @property
    def search_field(self) -> Locator:
        """
        A property that gets the search box inside the open dropdown.

        :return: The locator for the search box.
        """

        return self.root.get_by_placeholder(self.search_placeholder)

    @property
    def toggle(self) -> Locator:
        """
        A property that gets the control that opens the dropdown.

        :return: The locator for the toggle.
        """

        return self.root.locator(self.toggle_selector)

    def choice(self, label: str, *, exact: bool = False) -> Locator:
        """
        A method that gets the choice a label names.

        :param label: The label shown on the choice.
        :param exact: Whether the label must match the choice text in full.
        :return: The locator for the choice.
        """

        if exact:
            return self.choices.filter(has=self.root.page.get_by_text(label, exact=True)).first

        return self.choices.filter(has_text=label).first

    def choose(self, label: str, *, search: str = '', exact: bool = False) -> None:
        """
        A method that searches for a choice and picks it.

        A field drawn without a search box is picked from directly, so the same
        call reads the same whether the list is long enough to filter or not.

        :param label: The label shown on the choice.
        :param search: The text typed into the search box, defaulting to the label.
        :param exact: Whether the label must match the choice text in full.
        :raises ValueError: If a search is asked for on a field that offers none.
        :raises AssertionError: If the dropdown never closes onto the choice.
        """

        if self.is_searchable:
            self.search_field.fill(search or label)
        elif search:
            message = f'the field offers no search box, so "{search}" cannot be typed'
            raise ValueError(message)

        self.choice(label, exact=exact).click(force=True)

        expect(self.dropdown).to_be_hidden()
        expect(self.toggle).to_contain_text(label)

    def open(self) -> None:
        """
        A method that clicks the toggle until the dropdown is showing.

        :raises AssertionError: If the dropdown never opens.
        """

        trigger_until_visible(self.toggle.click, self.dropdown)
