from __future__ import annotations

import pytest

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

from limelight.django.modal import FIELD_FILL_ATTEMPT_COUNT_MAX, Modal

if TYPE_CHECKING:
    from playwright.sync_api import Locator

    from limelight.demo import Demo


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


class FakeDemo:
    def __init__(self, *, invalid_report: str = '') -> None:
        self.clicks: list[object] = []
        self.fills: list[tuple[object, str]] = []
        self.invalid_report = invalid_report
        self.narrations: list[tuple[str, str]] = []
        self.shots: list[str] = []
        self.spotlights: list[str] = []
        self.page = SimpleNamespace(
            locator=self._locator,
            wait_for_load_state=lambda state: None,
            wait_for_timeout=lambda milliseconds: None,
        )

    def _locator(self, selector: str) -> object:
        return SimpleNamespace(
            evaluate=lambda expression: self.invalid_report,
            filter=lambda **arguments: self._locator(''),
            first=SimpleNamespace(evaluate=lambda expression: self.invalid_report),
            get_by_role=lambda role, name: SimpleNamespace(first=object()),
            locator=self._locator,
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
    monkeypatch.setattr('limelight.django.modal.expect', expect_stub)

    demo = FakeDemo()
    field = FakeField([])
    modal = Modal(demo.as_demo())

    modal._value_settle(field.as_locator(), 'typed')

    assert len(demo.fills) + len(field.fill_values) == FIELD_FILL_ATTEMPT_COUNT_MAX


def test_an_invalid_control_refuses_the_submit_and_names_itself(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr('limelight.django.modal.expect', expect_stub)

    demo = FakeDemo(invalid_report='acres (Enter a number.)')
    modal = Modal(demo.as_demo())

    with pytest.raises(AssertionError, match='acres'):
        modal.submit()

    assert demo.clicks == []
    assert demo.shots == []


def test_a_valid_form_is_shot_before_it_is_submitted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('limelight.django.modal.expect', expect_stub)

    demo = FakeDemo()
    modal = Modal(demo.as_demo())

    modal.submit(shot='field-form')

    assert demo.shots == ['field-form']
    assert demo.spotlights == ['Click "Submit"']
    assert len(demo.clicks) == 1


def test_a_button_locator_opens_the_modal_without_a_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('limelight.django.modal.expect', expect_stub)

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


def test_a_card_header_needs_a_button_name() -> None:
    demo = FakeDemo()
    opener = FakeField([])
    modal = Modal(demo.as_demo())

    with pytest.raises(ValueError, match='button name'):
        modal.open(opener.as_locator(), headline='Editing', body='', within='Payments')
