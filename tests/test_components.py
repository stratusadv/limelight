from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

from limelight.components import Modal, SearchAndSelect, SlideButton

from fakes import FakeDemo, FakeLocator

if TYPE_CHECKING:
    import pytest

    from collections.abc import Callable
    from playwright.sync_api import Locator

    from limelight.session import DemoSession


def demo_of(demo: FakeDemo) -> DemoSession:
    return cast('DemoSession', demo)


def expect_stub(locator: object) -> SimpleNamespace:
    return SimpleNamespace(
        to_be_hidden=lambda timeout=None: None,
        to_be_visible=lambda timeout=None: None,
        to_contain_text=lambda text, timeout=None: None,
    )


def test_modal_root_is_the_dialog_role() -> None:
    demo = FakeDemo()

    assert Modal(demo_of(demo)).root is not None
    assert demo.owner_page.role_queries == [('dialog', None, False)]


def test_modal_option_scopes_text_to_dialog() -> None:
    demo = FakeDemo()

    Modal(demo_of(demo)).option('Row 3')

    assert demo.owner_page.role_locators[0].text_queries == [('Row 3', True)]


def test_modal_open_with_clicks_trigger_through_the_demo(monkeypatch: pytest.MonkeyPatch) -> None:
    triggers: list[Callable[[], None]] = []

    def trigger_until_visible_stub(
        trigger: Callable[[], None],
        locator: object,
        **kwargs: object,
    ) -> None:
        triggers.append(trigger)

    monkeypatch.setattr('limelight.components.trigger_until_visible', trigger_until_visible_stub)

    demo = FakeDemo()
    trigger = FakeLocator()

    Modal(demo_of(demo)).open_with(trigger.as_locator(), reveals_text='Row 3')

    triggers[0]()

    assert demo.clicked == [(trigger.as_locator(), False)]


def test_modal_choose_clicks_visible_option_through_the_demo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('limelight.components.expect', expect_stub)

    demo = FakeDemo()

    Modal(demo_of(demo)).choose('Row 3')

    assert demo.owner_page.role_locators[0].text_queries == [('Row 3', True)]
    assert len(demo.clicked) == 1


def test_slide_button_locates_alpine_track_and_thumb() -> None:
    demo = FakeDemo()
    slide_button = SlideButton(demo_of(demo))

    handles: list[Locator] = [slide_button.track, slide_button.thumb]

    assert len(handles) == 2
    assert demo.owner_page.locator_selectors == ['[x-ref="track"]', '[x-ref="thumb"]']


def test_slide_button_slides_through_the_demo() -> None:
    demo = FakeDemo()

    SlideButton(demo_of(demo)).slide()

    assert len(demo.slid) == 1


def test_search_and_select_locates_bootstrap_parts() -> None:
    root = FakeLocator()
    widget = SearchAndSelect(demo_of(FakeDemo()), root.as_locator())

    handles: list[Locator] = [widget.toggle, widget.dropdown, widget.choices, widget.search_field]

    assert len(handles) == 4
    assert root.selector_queries == ['button.form-control', 'div.list-group', '.list-group-item']
    assert root.placeholder_queries == ['Search...']


def test_search_and_select_within_takes_the_last_widget_in_the_container() -> None:
    container = FakeLocator()

    SearchAndSelect.within(demo_of(FakeDemo()), container.as_locator())

    assert container.selector_queries == ['div.position-relative']
    assert container.children[0].filter_haves != []


def test_search_and_select_open_clicks_toggle_through_the_demo(monkeypatch: pytest.MonkeyPatch) -> None:
    triggers: list[Callable[[], None]] = []

    def trigger_until_visible_stub(
        trigger: Callable[[], None],
        locator: object,
        **kwargs: object,
    ) -> None:
        triggers.append(trigger)

    monkeypatch.setattr('limelight.components.trigger_until_visible', trigger_until_visible_stub)

    demo = FakeDemo()
    root = FakeLocator()

    SearchAndSelect(demo_of(demo), root.as_locator()).open()

    triggers[0]()

    assert len(demo.clicked) == 1


def test_search_and_select_choose_searches_then_clicks_the_choice(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('limelight.components.expect', expect_stub)

    demo = FakeDemo()
    root = FakeLocator()

    SearchAndSelect(demo_of(demo), root.as_locator()).choose('Bin 2 - Row 1')

    choices = root.children[1]

    assert demo.filled == [(root.children[0].as_locator(), 'Bin 2 - Row 1')]
    assert choices.filter_texts == ['Bin 2 - Row 1']
    assert demo.clicked[0][1] is True


def test_search_and_select_choose_uses_the_search_term_when_given(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('limelight.components.expect', expect_stub)

    demo = FakeDemo()
    root = FakeLocator()

    SearchAndSelect(demo_of(demo), root.as_locator()).choose('Bin 2 - Row 1', search='Row 1')

    assert demo.filled == [(root.children[0].as_locator(), 'Row 1')]


def test_search_and_select_choice_matches_exact_text_when_asked() -> None:
    root = FakeLocator()

    SearchAndSelect(demo_of(FakeDemo()), root.as_locator()).choice('Row 1', exact=True)

    assert root.owner_page.role_queries == []
    assert root.owner_page.text_queries == [('Row 1', True)]


def test_modal_subclass_root_uses_its_selector() -> None:
    class OffcanvasModal(Modal):
        root_selector = '.offcanvas.show'

    demo = FakeDemo()

    assert OffcanvasModal(demo_of(demo)).root is not None
    assert demo.owner_page.role_queries == []
    assert demo.owner_page.locator_selectors == ['.offcanvas.show']


def test_search_and_select_subclass_locates_its_own_parts() -> None:
    class ChoicesWidget(SearchAndSelect):
        choice_selector = 'li.choice'
        dropdown_selector = 'div.choices'
        search_placeholder = 'Filter...'
        toggle_selector = 'button.choices-toggle'

    root = FakeLocator()
    widget = ChoicesWidget(demo_of(FakeDemo()), root.as_locator())

    handles: list[Locator] = [widget.toggle, widget.dropdown, widget.choices, widget.search_field]

    assert len(handles) == 4
    assert root.selector_queries == ['button.choices-toggle', 'div.choices', 'li.choice']
    assert root.placeholder_queries == ['Filter...']


def test_search_and_select_within_filters_on_the_subclass_toggle() -> None:
    class ChoicesWidget(SearchAndSelect):
        toggle_selector = 'button.choices-toggle'

    container = FakeLocator()

    ChoicesWidget.within(demo_of(FakeDemo()), container.as_locator())

    assert container.owner_page.locator_selectors == ['button.choices-toggle']
