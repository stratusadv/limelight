from __future__ import annotations

from types import SimpleNamespace
from typing_extensions import TYPE_CHECKING

from limelight.components import Modal, SearchAndSelect, SlideButton

from fakes import FakeLocator, FakePage

if TYPE_CHECKING:
    import pytest

    from playwright.sync_api import Locator
    from typing_extensions import Callable


def expect_stub(locator: object) -> SimpleNamespace:
    return SimpleNamespace(
        to_be_hidden=lambda timeout=None: None,
        to_be_visible=lambda timeout=None: None,
        to_contain_text=lambda text, timeout=None: None,
    )


def test_modal_root_is_the_dialog_role() -> None:
    page = FakePage()

    assert Modal(page.as_page()).root is not None
    assert page.role_queries == [('dialog', None, False)]


def test_modal_option_scopes_text_to_dialog() -> None:
    page = FakePage()

    Modal(page.as_page()).option('Row 3')

    assert page.role_locators[0].text_queries == [('Row 3', True)]


def test_modal_open_with_retries_trigger_until_option_visible(monkeypatch: pytest.MonkeyPatch) -> None:
    triggers: list[Callable[[], None]] = []

    def trigger_until_visible_stub(
        trigger: Callable[[], None],
        locator: object,
        **kwargs: object,
    ) -> None:
        triggers.append(trigger)

    monkeypatch.setattr('limelight.components.trigger_until_visible', trigger_until_visible_stub)

    page = FakePage()
    trigger = FakeLocator()

    Modal(page.as_page()).open_with(trigger.as_locator(), reveals_text='Row 3')

    triggers[0]()

    assert trigger.click_count == 1


def test_modal_choose_clicks_visible_option(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('limelight.components.expect', expect_stub)

    page = FakePage()

    Modal(page.as_page()).choose('Row 3')

    assert page.role_locators[0].text_queries == [('Row 3', True)]


def test_slide_button_locates_alpine_track_and_thumb() -> None:
    page = FakePage()
    slide_button = SlideButton(page.as_page())

    handles: list[Locator] = [slide_button.track, slide_button.thumb]

    assert len(handles) == 2
    assert page.locator_selectors == ['[x-ref="track"]', '[x-ref="thumb"]']


def test_slide_button_slides_thumb_to_track_end(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('limelight.gestures.expect', expect_stub)

    page = FakePage()

    SlideButton(page.as_page()).slide()

    assert page.mouse.actions[0][0] == 'move'
    assert page.mouse.actions[1] == ('down',)
    assert page.mouse.actions[-1] == ('up',)


def test_search_and_select_locates_bootstrap_parts() -> None:
    root = FakeLocator()
    widget = SearchAndSelect(root.as_locator())

    handles: list[Locator] = [widget.toggle, widget.dropdown, widget.choices, widget.search_field]

    assert len(handles) == 4
    assert root.selector_queries == ['button.form-control', 'div.list-group', '.list-group-item']
    assert root.placeholder_queries == ['Search...']


def test_search_and_select_within_takes_the_last_widget_in_the_container() -> None:
    container = FakeLocator()

    SearchAndSelect.within(container.as_locator())

    assert container.selector_queries == ['div.position-relative']
    assert container.children[0].filter_haves != []


def test_search_and_select_open_retries_toggle_until_dropdown_visible(monkeypatch: pytest.MonkeyPatch) -> None:
    triggers: list[Callable[[], None]] = []

    def trigger_until_visible_stub(
        trigger: Callable[[], None],
        locator: object,
        **kwargs: object,
    ) -> None:
        triggers.append(trigger)

    monkeypatch.setattr('limelight.components.trigger_until_visible', trigger_until_visible_stub)

    root = FakeLocator()

    SearchAndSelect(root.as_locator()).open()

    triggers[0]()

    assert root.children[0].click_count == 1


def test_search_and_select_choose_searches_then_clicks_the_choice(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('limelight.components.expect', expect_stub)

    root = FakeLocator()

    SearchAndSelect(root.as_locator()).choose('Bin 2 - Row 1')

    search_field = root.children[0]
    choices = root.children[1]

    assert search_field.fill_values == ['Bin 2 - Row 1']
    assert choices.filter_texts == ['Bin 2 - Row 1']
    assert choices.click_forces == [True]


def test_search_and_select_choose_uses_the_search_term_when_given(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('limelight.components.expect', expect_stub)

    root = FakeLocator()

    SearchAndSelect(root.as_locator()).choose('Bin 2 - Row 1', search='Row 1')

    assert root.children[0].fill_values == ['Row 1']


def test_search_and_select_choice_matches_exact_text_when_asked() -> None:
    root = FakeLocator()

    SearchAndSelect(root.as_locator()).choice('Row 1', exact=True)

    assert root.owner_page.role_queries == []
    assert root.owner_page.text_queries == [('Row 1', True)]
