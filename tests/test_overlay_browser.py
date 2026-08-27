from __future__ import annotations

import pytest

from pathlib import Path
from typing import TYPE_CHECKING

from playwright.sync_api import sync_playwright

from limelight.overlay import Overlay
from limelight.timing import DemoTiming

if TYPE_CHECKING:
    from collections.abc import Iterator

    from playwright.sync_api import Page


pytestmark = pytest.mark.browser


PAGE_HTML = """
<html><body style="margin:0;height:600px">
<button id="go" onclick="window.clicked = true"
        style="position:absolute;left:40px;top:40px;width:120px;height:32px">Go</button>
<input id="name" style="position:absolute;left:40px;top:120px;width:200px" />
</body></html>
"""

PAGE_HTML_TALL = """
<html><body style="margin:0;height:3000px"></body></html>
"""


@pytest.fixture(scope='module')
def demo_page() -> Iterator[tuple[Page, Overlay]]:
    with sync_playwright() as playwright:
        executable = Path(playwright.chromium.executable_path)

        if not executable.exists():
            pytest.skip('chromium is not installed; run `playwright install chromium`')

        browser = playwright.chromium.launch()
        page = browser.new_page()
        timing = DemoTiming(step_ms=1, scale_factor=0.05)
        overlay = Overlay(page, timing, controls=True)

        yield page, overlay

        browser.close()


def overlay_install(page: Page, overlay: Overlay, html: str) -> None:
    page.set_content(html)
    overlay._ensure()


def test_caption_renders_markup_as_text(demo_page: tuple[Page, Overlay]) -> None:
    page, overlay = demo_page

    overlay_install(page, overlay, PAGE_HTML)

    page.evaluate(
        "() => window.__limelight.caption("
        "{title: 'Enter <order> & save', body: '', step: '', tag: '', kind: ''})",
    )

    title_text = page.evaluate("() => document.querySelector('#limelight-caption h3').textContent")

    assert title_text == 'Enter <order> & save'


def test_click_glides_cursor_then_clicks(demo_page: tuple[Page, Overlay]) -> None:
    page, overlay = demo_page

    overlay_install(page, overlay, PAGE_HTML)
    overlay.click(page.locator('#go'))

    assert page.evaluate('() => window.clicked') is True

    page.wait_for_function(
        "() => document.getElementById('limelight-cursor').style.left === '100px'"
        " && document.getElementById('limelight-cursor').style.top === '56px'",
    )


def test_cursor_move_duration_scales_with_distance(demo_page: tuple[Page, Overlay]) -> None:
    page, overlay = demo_page

    overlay_install(page, overlay, PAGE_HTML)

    duration_arrive = page.evaluate('() => window.__limelight.cursorMove({x: 10, y: 10, ms: 500})')

    page.wait_for_timeout(float(duration_arrive) + 100)

    duration_short = page.evaluate('() => window.__limelight.cursorMove({x: 40, y: 10, ms: 500})')

    page.wait_for_timeout(float(duration_short) + 100)

    duration_long = page.evaluate('() => window.__limelight.cursorMove({x: 1200, y: 600, ms: 500})')

    assert isinstance(duration_short, int)
    assert isinstance(duration_long, int)
    assert duration_short < duration_long
    assert duration_long <= 1000


def test_fill_types_value_and_raises_key_hud(demo_page: tuple[Page, Overlay]) -> None:
    page, overlay = demo_page

    overlay_install(page, overlay, PAGE_HTML)
    overlay.fill(page.locator('#name'), 'hi')

    assert page.locator('#name').input_value() == 'hi'
    assert page.evaluate("() => document.getElementById('limelight-keys') !== null") is True


def test_control_bar_exists_with_speed_state(demo_page: tuple[Page, Overlay]) -> None:
    page, overlay = demo_page

    overlay_install(page, overlay, PAGE_HTML)

    state = page.evaluate('() => window.__limelight.controlPeek()')

    assert page.evaluate("() => document.getElementById('limelight-control') !== null") is True
    assert isinstance(state['speedFactor'], (int, float))


def test_spot_follows_page_scroll(demo_page: tuple[Page, Overlay]) -> None:
    page, overlay = demo_page

    overlay_install(page, overlay, PAGE_HTML_TALL)

    page.evaluate(
        '() => window.__limelight.spot('
        "{box: {x: 0, y: 500, width: 100, height: 50}, label: '', dim: true})",
    )
    page.evaluate('() => window.scrollTo(0, 100)')
    page.wait_for_function("() => document.getElementById('limelight-spot').style.top === '392px'")
