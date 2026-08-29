from __future__ import annotations

import pytest

from typing_extensions import override

from playwright.sync_api import Error as PlaywrightError

from limelight.config import DemoConfig
from limelight.overlay.assets import OVERLAY_JAVASCRIPT
from limelight.overlay.bridge import EVALUATE_ATTEMPT_COUNT, Bridge

from fakes import FakePage


CONFIG = DemoConfig(mode='narrate')


def test_call_returns_the_function_result() -> None:
    page = FakePage()
    bridge = Bridge(page.as_page(), CONFIG)

    assert bridge.call('selectShow', {'index': 0}) == {'x': 30.0, 'y': 60.0}
    assert bridge.call('spotClear') is None
    assert page.selector_waits == []


def test_call_installs_the_overlay_once_when_it_is_missing() -> None:
    page = FakePage()
    page.installed = False
    bridge = Bridge(page.as_page(), CONFIG)

    bridge.call('spotClear')
    bridge.call('spotClear')

    expressions = [expression for expression, _ in page.evaluations]

    assert page.selector_waits == [('body', 'attached')]
    assert expressions.count(OVERLAY_JAVASCRIPT) == 1
    assert expressions[1] == OVERLAY_JAVASCRIPT


def test_call_raises_when_the_overlay_will_not_install(monkeypatch: pytest.MonkeyPatch) -> None:
    page = FakePage()
    page.installed = False
    bridge = Bridge(page.as_page(), CONFIG)

    monkeypatch.setattr(bridge, 'ensure', lambda: None)

    with pytest.raises(RuntimeError, match='unreachable'):
        bridge.call('spotClear')


def test_call_awaits_the_function_before_wrapping_its_result() -> None:
    page = FakePage()
    bridge = Bridge(page.as_page(), CONFIG)

    bridge.call('settle', {'ms': 2000})

    expression = page.evaluations[0][0]

    assert expression.startswith('async (argument) =>')
    assert '{result: await window.__limelight.settle(argument)}' in expression


def test_call_retries_when_a_navigation_destroys_the_context() -> None:
    page = FakePage()
    bridge = Bridge(page.as_page(), CONFIG)

    page.navigation_error_count = 1

    assert bridge.call('selectShow', {'index': 0}) == {'x': 30.0, 'y': 60.0}
    assert page.load_states == ['domcontentloaded']
    assert len(page.evaluations) == 2


def test_call_raises_when_the_page_never_stops_navigating() -> None:
    page = FakePage()
    bridge = Bridge(page.as_page(), CONFIG)

    page.navigation_error_count = EVALUATE_ATTEMPT_COUNT

    with pytest.raises(RuntimeError, match='navigated away'):
        bridge.call('spotClear')

    assert len(page.evaluations) == EVALUATE_ATTEMPT_COUNT


def test_call_reraises_an_unrelated_playwright_error(monkeypatch: pytest.MonkeyPatch) -> None:
    page = FakePage()
    bridge = Bridge(page.as_page(), CONFIG)

    def explode(expression: str, argument: object = None) -> object:
        message = 'Target page, context or browser has been closed'
        raise PlaywrightError(message)

    monkeypatch.setattr(page, 'evaluate', explode)

    with pytest.raises(PlaywrightError, match='has been closed'):
        bridge.call('spotClear')

    assert page.load_states == []


def test_read_returns_only_a_mapping() -> None:
    page = FakePage()
    bridge = Bridge(page.as_page(), CONFIG)

    page.control_states = [{'paused': True}]

    assert bridge.read('controlRead') == {'paused': True}
    assert bridge.read('spotClear') is None


class StringPage(FakePage):
    @override
    def evaluate(self, expression: str, argument: object = None) -> object:
        super().evaluate(expression, argument)

        return 'not-a-mapping'


def test_a_call_that_answers_with_no_mapping_reads_as_none() -> None:
    page = StringPage()
    bridge = Bridge(page.as_page(), CONFIG)

    assert bridge.call('controlPeek') is None
    assert bridge.read('controlPeek') is None
