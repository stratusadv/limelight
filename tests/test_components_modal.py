from __future__ import annotations

import pytest

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

from limelight.components.modal import FIELD_FILL_ATTEMPT_COUNT_MAX, Modal

if TYPE_CHECKING:
    from typing import Self

    from playwright.sync_api import Locator

    from limelight.demo import Demo


class DispatchModal(Modal):
    content_selector = '#dispatch-modal-content'
    opener_selector = 'a.btn'
    scope_selector = '.panel'


class FakeField:
    def __init__(self, values: list[str]) -> None:
        self.fill_values: list[str] = []
        self.page = SimpleNamespace(wait_for_timeout=lambda milliseconds: None)
        self.values = values

    def as_locator(self) -> Locator:
        return cast('Locator', self)

    def fill(self, value: str) -> None:
        self.fill_values.append(value)

    def input_value(self) -> str:
        return self.values.pop(0) if self.values else ''


class FakeNode:
    def __init__(self, invalid_report: str = '') -> None:
        self.click_count = 0
        self.invalid_report = invalid_report
        self.role_queries: list[tuple[str, str | None]] = []
        self.selectors: list[str] = []
        self.texts: list[tuple[str, bool]] = []

    @property
    def first(self) -> Self:
        return self

    @property
    def last(self) -> Self:
        return self

    def click(self) -> None:
        self.click_count += 1

    def evaluate(self, expression: str) -> str:
        return self.invalid_report

    def filter(self, **arguments: object) -> Self:
        return self

    def get_by_role(self, role: str, *, name: str | None = None) -> Self:
        query = (role, name)
        self.role_queries.append(query)

        return self

    def get_by_text(self, text: str, *, exact: bool = False) -> Self:
        query = (text, exact)
        self.texts.append(query)

        return self

    def locator(self, selector: str) -> Self:
        self.selectors.append(selector)

        return self


class FakeDemo:
    def __init__(self, *, invalid_report: str = '') -> None:
        self.clicks: list[object] = []
        self.fills: list[tuple[object, str]] = []
        self.narrations: list[tuple[str, str]] = []
        self.node = FakeNode(invalid_report)
        self.shots: list[str] = []
        self.spotlights: list[str] = []
        self.page = SimpleNamespace(
            get_by_role=self.node.get_by_role,
            get_by_text=self.node.get_by_text,
            locator=self.node.locator,
            wait_for_load_state=lambda state: None,
            wait_for_timeout=lambda milliseconds: None,
        )

    def as_demo(self) -> Demo:
        return cast('Demo', self)

    def click(self, locator: object) -> None:
        self.clicks.append(locator)

    def fill(self, locator: object, value: str) -> None:
        pair = (locator, value)
        self.fills.append(pair)

    def narrate(self, title: str, *, body: str = '', step: str = '') -> None:
        narration = (title, step)
        self.narrations.append(narration)

    def pause(self) -> None:
        return

    def screenshot(self, name: str) -> None:
        self.shots.append(name)

    def spotlight(self, locator: object, *, label: str = '') -> None:
        self.spotlights.append(label)


def expect_stub(locator: object) -> SimpleNamespace:
    return SimpleNamespace(
        to_be_enabled=lambda timeout: None,
        to_be_hidden=lambda timeout: None,
        to_be_visible=lambda timeout: None,
        to_have_value=lambda value, timeout: None,
    )


def test_a_field_that_takes_the_value_is_filled_once() -> None:
    demo = FakeDemo()
    field = FakeField(['typed'])
    modal = Modal(demo.as_demo())

    modal._value_settle(field.as_locator(), 'typed')

    assert demo.fills == [(field, 'typed')]
    assert field.fill_values == []


def test_a_field_that_drops_the_value_is_refilled_until_it_holds() -> None:
    demo = FakeDemo()
    field = FakeField(['', '', 'typed'])
    modal = Modal(demo.as_demo())

    modal._value_settle(field.as_locator(), 'typed')

    assert demo.fills == [(field, 'typed')]
    assert field.fill_values == ['typed', 'typed']


def test_a_field_that_never_holds_the_value_stops_at_the_attempt_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr('limelight.components.modal.expect', expect_stub)

    demo = FakeDemo()
    field = FakeField([])
    modal = Modal(demo.as_demo())

    modal._value_settle(field.as_locator(), 'typed')

    assert len(demo.fills) + len(field.fill_values) == FIELD_FILL_ATTEMPT_COUNT_MAX


def test_an_invalid_control_refuses_the_submit_and_names_itself(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr('limelight.components.modal.expect', expect_stub)

    demo = FakeDemo(invalid_report='acres (Enter a number.)')
    modal = Modal(demo.as_demo())

    with pytest.raises(AssertionError, match='acres'):
        modal.submit()

    assert demo.clicks == []
    assert demo.shots == []


def test_a_valid_form_is_shot_before_it_is_submitted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('limelight.components.modal.expect', expect_stub)

    demo = FakeDemo()
    modal = Modal(demo.as_demo())

    modal.submit(shot='field-form')

    assert demo.shots == ['field-form']
    assert demo.spotlights == ['Click "Submit"']
    assert len(demo.clicks) == 1


def test_a_button_locator_opens_the_modal_without_a_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('limelight.components.modal.expect', expect_stub)

    demo = FakeDemo()
    opener = FakeField([])
    modal = Modal(demo.as_demo())

    modal.open(
        opener.as_locator(),
        headline='Editing the row',
        body='The row carries an icon button.',
        label='Edit "North Quarter"',
    )

    assert demo.clicks == [opener]
    assert demo.spotlights == ['Edit "North Quarter"']
    assert demo.narrations == [('Editing the row', 'Create')]


def test_a_region_needs_a_control_name() -> None:
    demo = FakeDemo()
    opener = FakeField([])
    modal = Modal(demo.as_demo())

    with pytest.raises(ValueError, match='control name'):
        modal.open(opener.as_locator(), headline='Editing', body='', within='Payments')


def test_the_dialog_role_finds_the_modal_when_no_selector_names_it() -> None:
    demo = FakeDemo()
    modal = Modal(demo.as_demo())

    content = modal.content

    assert content is demo.node
    assert demo.node.role_queries == [('dialog', None)]
    assert demo.node.selectors == []


def test_a_named_selector_finds_the_modal_instead_of_the_role() -> None:
    demo = FakeDemo()
    modal = DispatchModal(demo.as_demo())

    content = modal.content

    assert content is demo.node
    assert demo.node.selectors == ['#dispatch-modal-content']
    assert demo.node.role_queries == []


def test_a_subclass_scopes_the_opener_with_its_own_selectors() -> None:
    demo = FakeDemo()
    modal = DispatchModal(demo.as_demo())

    modal._opener('Add', within='Payments')

    assert demo.node.selectors == ['a.btn', '.panel', 'a.btn']


def test_the_default_opener_matches_links_and_buttons() -> None:
    demo = FakeDemo()
    modal = Modal(demo.as_demo())

    modal._opener('Add', within='')

    assert demo.node.selectors == ['a, button']


def test_choosing_an_option_clicks_it(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('limelight.components.modal.expect', expect_stub)

    demo = FakeDemo()
    modal = Modal(demo.as_demo())

    modal.choose('Row 20')

    assert demo.node.texts == [('Row 20', True)]
    assert demo.clicks == [demo.node]
    assert demo.spotlights == []


def test_choosing_an_option_spotlights_it_when_it_carries_a_label(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr('limelight.components.modal.expect', expect_stub)

    demo = FakeDemo()
    modal = Modal(demo.as_demo())

    modal.choose('Row 20', label='Pick the row')

    assert demo.spotlights == ['Pick the row']


def test_open_with_retries_the_trigger_until_the_option_shows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[object] = []

    monkeypatch.setattr(
        'limelight.components.modal.trigger_until_visible',
        lambda trigger, locator: calls.append(locator),
    )

    demo = FakeDemo()
    trigger = FakeNode()
    modal = Modal(demo.as_demo())

    modal.open_with(cast('Locator', trigger), reveals_text='Row 20')

    assert calls == [demo.node]
    assert demo.node.texts == [('Row 20', True)]
