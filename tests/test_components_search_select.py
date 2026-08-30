from __future__ import annotations

import pytest

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

from limelight.components.search_select import SearchAndSelect

if TYPE_CHECKING:
    from typing import Self

    from playwright.sync_api import Locator


class TypeaheadSelect(SearchAndSelect):
    choice_selector = 'li[role="option"]'
    dropdown_selector = 'ul[role="listbox"]'
    root_selector = 'div.typeahead'
    search_placeholder = 'Type to filter'
    toggle_selector = 'button[aria-haspopup="listbox"]'


class FakeNode:
    def __init__(self, *, search_field_count: int = 1) -> None:
        self.click_count = 0
        self.search_field_count = search_field_count
        self.fill_values: list[str] = []
        self.filters: list[dict[str, object]] = []
        self.page: FakeNode = self
        self.placeholders: list[str] = []
        self.selectors: list[str] = []
        self.texts: list[tuple[str, bool]] = []

    @property
    def first(self) -> Self:
        return self

    @property
    def last(self) -> Self:
        return self

    def as_locator(self) -> Locator:
        return cast('Locator', self)

    def click(self, *, force: bool = False) -> None:
        self.click_count += 1

    def count(self) -> int:
        return self.search_field_count

    def fill(self, value: str) -> None:
        self.fill_values.append(value)

    def filter(self, **arguments: object) -> Self:
        self.filters.append(arguments)

        return self

    def get_by_placeholder(self, placeholder: str) -> Self:
        self.placeholders.append(placeholder)

        return self

    def get_by_text(self, text: str, *, exact: bool = False) -> Self:
        query = (text, exact)
        self.texts.append(query)

        return self

    def locator(self, selector: str) -> Self:
        self.selectors.append(selector)

        return self


def expect_stub(locator: object) -> SimpleNamespace:
    return SimpleNamespace(
        to_be_hidden=lambda: None,
        to_contain_text=lambda text: None,
    )


def test_within_finds_the_last_field_that_carries_a_toggle() -> None:
    container = FakeNode()

    field = SearchAndSelect.within(container.as_locator())

    assert container.selectors == ['div.position-relative', 'button.form-control']
    assert field.root is container


def test_a_subclass_finds_its_own_markup() -> None:
    container = FakeNode()

    TypeaheadSelect.within(container.as_locator())

    assert container.selectors == ['div.typeahead', 'button[aria-haspopup="listbox"]']


def test_the_parts_read_through_the_configured_selectors() -> None:
    root = FakeNode()
    field = TypeaheadSelect(root.as_locator())

    parts = (field.choices, field.dropdown, field.search_field, field.toggle)

    assert all(part is root for part in parts)

    assert root.selectors == [
        'li[role="option"]',
        'ul[role="listbox"]',
        'button[aria-haspopup="listbox"]',
    ]

    assert root.placeholders == ['Type to filter']


def test_choosing_fills_the_search_box_then_clicks_the_choice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr('limelight.components.search_select.expect', expect_stub)

    root = FakeNode()
    field = SearchAndSelect(root.as_locator())

    field.choose('Row 20')

    assert root.fill_values == ['Row 20']
    assert root.click_count == 1


def test_choosing_searches_for_the_text_it_is_given(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('limelight.components.search_select.expect', expect_stub)

    root = FakeNode()
    field = SearchAndSelect(root.as_locator())

    field.choose('Row 20', search='20')

    assert root.fill_values == ['20']


def test_an_exact_choice_matches_the_whole_label() -> None:
    root = FakeNode()
    field = SearchAndSelect(root.as_locator())

    field.choice('Row 2', exact=True)

    assert root.texts == [('Row 2', True)]


def test_a_loose_choice_matches_a_fragment() -> None:
    root = FakeNode()
    field = SearchAndSelect(root.as_locator())

    field.choice('Row 2')

    assert root.texts == []
    assert root.filters[-1] == {'has_text': 'Row 2'}


def test_open_retries_the_toggle_until_the_dropdown_shows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[object] = []

    monkeypatch.setattr(
        'limelight.components.search_select.trigger_until_visible',
        lambda trigger, locator: calls.append(locator),
    )

    root = FakeNode()
    field = SearchAndSelect(root.as_locator())

    field.open()

    assert calls == [root]


def test_named_finds_the_widget_beside_the_form_field_it_writes_to() -> None:
    scope = FakeNode()

    field = SearchAndSelect.named(scope.as_locator(), 'delivery_location')

    assert scope.selectors == [
        'input[name="delivery_location"]',
        'xpath=following-sibling::div[1]',
    ]

    assert field.root is scope


def test_named_uses_the_selectors_the_subclass_carries() -> None:
    scope = FakeNode()

    TypeaheadSelect.named(scope.as_locator(), 'category')

    assert scope.selectors[0] == 'input[name="category"]'


def test_named_rejects_an_empty_field_name() -> None:
    scope = FakeNode()

    with pytest.raises(ValueError, match='name must not be empty'):
        SearchAndSelect.named(scope.as_locator(), ' ')


def test_a_field_without_a_search_box_is_picked_from_directly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr('limelight.components.search_select.expect', expect_stub)

    root = FakeNode(search_field_count=0)
    field = SearchAndSelect(root.as_locator())

    field.choose('Commodity')

    assert root.fill_values == []
    assert root.click_count == 1


def test_a_field_with_a_search_box_is_filtered_before_the_pick(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr('limelight.components.search_select.expect', expect_stub)

    root = FakeNode()
    field = SearchAndSelect(root.as_locator())

    field.choose('Commodity')

    assert root.fill_values == ['Commodity']


def test_a_search_asked_for_on_a_field_without_a_box_is_refused() -> None:
    root = FakeNode(search_field_count=0)
    field = SearchAndSelect(root.as_locator())

    with pytest.raises(ValueError, match='the field offers no search box'):
        field.choose('Commodity', search='comm')
