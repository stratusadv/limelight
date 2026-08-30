from __future__ import annotations

import pytest

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

from limelight.components.dropdown import Dropdown

if TYPE_CHECKING:
    from typing import Self

    from limelight.demo import Demo


class RowMenu(Dropdown):
    item_selector = '.dropdown-item'
    menu_selector = '.dropdown-menu'
    trigger_selector = '.bi-three-dots-vertical'


class FakeNode:
    def __init__(self, name: str) -> None:
        self.filters: list[dict[str, object]] = []
        self.name = name
        self.scroll_count = 0
        self.selectors: list[str] = []

    @property
    def first(self) -> Self:
        return self

    def filter(self, **arguments: object) -> Self:
        self.filters.append(arguments)

        return self

    def locator(self, selector: str) -> Self:
        self.selectors.append(selector)

        return self

    def scroll_into_view_if_needed(self) -> None:
        self.scroll_count += 1


class FakeDemo:
    def __init__(self) -> None:
        self.clicks: list[object] = []
        self.node = FakeNode('page')
        self.pause_count = 0
        self.spotlights: list[str] = []

        self.page = SimpleNamespace(locator=self.node.locator)

    def as_demo(self) -> Demo:
        return cast('Demo', self)

    def click(self, locator: object) -> None:
        self.clicks.append(locator)

    def pause(self, ms: int | None = None) -> None:
        self.pause_count += 1

    def spotlight(self, locator: object, *, label: str = '') -> None:
        self.spotlights.append(label)


def expect_stub(locator: object) -> SimpleNamespace:
    return SimpleNamespace(to_be_visible=lambda timeout: None)


@pytest.fixture(autouse=True)
def _expect_stubbed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('limelight.components.dropdown.expect', expect_stub)


def test_the_trigger_is_scrolled_into_view_before_it_is_clicked() -> None:
    demo = FakeDemo()
    menu = RowMenu(demo.as_demo())

    menu.open()

    assert demo.node.scroll_count == 1
    assert demo.clicks == [demo.node]


def test_the_trigger_is_looked_up_through_the_class_selector() -> None:
    demo = FakeDemo()
    menu = RowMenu(demo.as_demo())

    menu.open()

    assert '.bi-three-dots-vertical' in demo.node.selectors


def test_the_trigger_is_scoped_to_the_root_when_one_is_given() -> None:
    demo = FakeDemo()
    row = FakeNode('row')

    RowMenu(demo.as_demo(), cast('object', row)).open()

    assert row.selectors == ['.bi-three-dots-vertical', '.dropdown-menu']
    assert demo.node.selectors == []


def test_an_action_is_picked_by_its_text() -> None:
    demo = FakeDemo()
    menu = RowMenu(demo.as_demo())

    menu.choose('Delete')

    assert demo.node.filters == [
        {'visible': True},
        {'visible': True},
        {'has_text': 'Delete'},
    ]

    assert demo.clicks == [demo.node, demo.node]


def test_the_menu_and_its_actions_are_scoped_to_the_root() -> None:
    demo = FakeDemo()
    row = FakeNode('row')

    RowMenu(demo.as_demo(), cast('object', row)).choose('Delete')

    assert row.selectors == ['.bi-three-dots-vertical', '.dropdown-menu', '.dropdown-item']
    assert demo.node.selectors == []


def test_an_action_is_spotlighted_only_when_it_is_labelled() -> None:
    demo = FakeDemo()
    menu = RowMenu(demo.as_demo())

    menu.choose('Delete')

    assert demo.spotlights == []

    menu.choose('Rename', label='Rename this row')

    assert demo.spotlights == ['Rename this row']
