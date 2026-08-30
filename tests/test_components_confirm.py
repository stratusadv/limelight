from __future__ import annotations

import pytest

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

from limelight.components.confirm import Confirm

if TYPE_CHECKING:
    from typing import Self

    from limelight.demo import Demo


class DestructiveConfirm(Confirm):
    button_selector = '.app-btn-destructive'


class FakeNode:
    def __init__(self, name: str) -> None:
        self.filters: list[dict[str, object]] = []
        self.name = name
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


class FakeDemo:
    def __init__(self) -> None:
        self.clicks: list[object] = []
        self.node = FakeNode('page')
        self.spotlights: list[str] = []

        self.page = SimpleNamespace(locator=self.node.locator)

    def as_demo(self) -> Demo:
        return cast('Demo', self)

    def click(self, locator: object) -> None:
        self.clicks.append(locator)

    def spotlight(self, locator: object, *, label: str = '') -> None:
        self.spotlights.append(label)


def expect_stub(locator: object) -> SimpleNamespace:
    return SimpleNamespace(to_be_visible=lambda timeout: None)


@pytest.fixture(autouse=True)
def _expect_stubbed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('limelight.components.confirm.expect', expect_stub)


def test_the_button_is_looked_up_through_the_class_selector() -> None:
    demo = FakeDemo()

    DestructiveConfirm(demo.as_demo()).accept()

    assert demo.node.selectors == ['.app-btn-destructive']
    assert demo.node.filters == [{'visible': True}]
    assert demo.clicks == [demo.node]


def test_the_button_is_narrowed_by_its_text_when_one_is_given() -> None:
    demo = FakeDemo()

    DestructiveConfirm(demo.as_demo()).accept('Delete')

    assert demo.node.filters == [
        {'visible': True},
        {'has_text': 'Delete'},
    ]


def test_the_button_is_scoped_to_the_root_when_one_is_given() -> None:
    demo = FakeDemo()
    card = FakeNode('card')

    DestructiveConfirm(demo.as_demo(), cast('object', card)).accept()

    assert card.selectors == ['.app-btn-destructive']
    assert demo.node.selectors == []


def test_the_button_text_captions_the_spotlight() -> None:
    demo = FakeDemo()

    DestructiveConfirm(demo.as_demo()).accept('Remove')

    assert demo.spotlights == ['Remove']


def test_a_caption_given_at_the_call_wins_over_the_button_text() -> None:
    demo = FakeDemo()

    DestructiveConfirm(demo.as_demo()).accept('Remove', label='Confirm the removal')

    assert demo.spotlights == ['Confirm the removal']


def test_an_unnamed_button_is_clicked_without_a_spotlight() -> None:
    demo = FakeDemo()

    DestructiveConfirm(demo.as_demo()).accept()

    assert demo.spotlights == []
    assert demo.clicks == [demo.node]
