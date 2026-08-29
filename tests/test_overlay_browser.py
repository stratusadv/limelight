from __future__ import annotations

import pytest

from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

from limelight.config import DemoConfig
from limelight.overlay import Overlay
from limelight.overlay.bridge import Bridge
from limelight.overlay.cursor import Cursor
from limelight.overlay.keyboard import Keyboard
from limelight.overlay.playback import Playback

if TYPE_CHECKING:
    from collections.abc import Iterator

    from playwright.sync_api import Page, Route


pytestmark = pytest.mark.browser


PAGE_HTML = """
<html><body style="margin:0;height:600px">
<button id="go" onclick="window.clicked = true"
        style="position:absolute;left:40px;top:40px;width:120px;height:32px">Go</button>
<input id="name" style="position:absolute;left:40px;top:120px;width:200px" />
</body></html>
"""

PAGE_HTML_LINK = """
<html><body style="margin:0;height:600px">
<a id="next" href="/second"
   style="position:absolute;left:40px;top:40px;width:120px;height:32px">Next</a>
</body></html>
"""

PAGE_HTML_SECOND = """
<html><body style="margin:0;height:600px"><h1 id="landed">Second</h1></body></html>
"""

PAGE_HTML_TALL = """
<html><body style="margin:0;height:3000px"></body></html>
"""

SITE_ORIGIN = 'http://limelight.test'

SITE_PAGES = {
    '/first': PAGE_HTML_LINK,
    '/second': PAGE_HTML_SECOND,
}


@pytest.fixture(scope='module')
def demo_page() -> Iterator[tuple[Page, Overlay]]:
    with sync_playwright() as playwright:
        executable = Path(playwright.chromium.executable_path)

        if not executable.exists():
            pytest.skip('chromium is not installed; run `playwright install chromium`')

        browser = playwright.chromium.launch()
        page = browser.new_page()
        config = DemoConfig(mode='narrate', step_ms=1, speed_factor=20.0)
        overlay = overlay_build(page, config)

        yield page, overlay

        browser.close()


def overlay_build(page: Page, config: DemoConfig) -> Overlay:
    bridge = Bridge(page, config)
    playback = Playback(bridge, config)

    return Overlay(bridge, playback, Cursor(bridge, playback), Keyboard(bridge, playback))


def overlay_install(page: Page, overlay: Overlay, html: str) -> None:
    page.set_content(html)
    overlay._bridge.ensure()


def site_serve(route: Route) -> None:
    body = SITE_PAGES.get(urlparse(route.request.url).path)

    if body is None:
        route.abort()

        return

    route.fulfill(status=200, content_type='text/html', body=body)


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


def test_click_survives_a_link_that_navigates(demo_page: tuple[Page, Overlay]) -> None:
    page, overlay = demo_page

    page.route(f'{SITE_ORIGIN}/**', site_serve)
    page.goto(f'{SITE_ORIGIN}/first')

    overlay.click(page.locator('#next'))

    page.wait_for_url(f'{SITE_ORIGIN}/second')
    page.unroute(f'{SITE_ORIGIN}/**', site_serve)

    assert page.url == f'{SITE_ORIGIN}/second'
    assert page.locator('#landed').is_visible()


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


def test_control_bar_holds_its_window_offset_when_the_page_grows(
    demo_page: tuple[Page, Overlay],
) -> None:
    page, overlay = demo_page

    overlay_install(page, overlay, PAGE_HTML)

    offset = (
        '() => window.innerWidth'
        " - document.getElementById('limelight-control').getBoundingClientRect().right"
    )

    offset_short = page.evaluate(offset)

    page.evaluate("() => document.body.style.height = '4000px'")
    page.wait_for_function('() => document.documentElement.scrollHeight > window.innerHeight')

    assert offset_short == 32
    assert page.evaluate(offset) == 32


def test_spot_follows_page_scroll(demo_page: tuple[Page, Overlay]) -> None:
    page, overlay = demo_page

    overlay_install(page, overlay, PAGE_HTML_TALL)

    page.evaluate(
        '() => window.__limelight.spot('
        "{box: {x: 0, y: 500, width: 100, height: 50}, label: '', dim: true})",
    )
    page.evaluate('() => window.scrollTo(0, 100)')
    page.wait_for_function("() => document.getElementById('limelight-spot').style.top === '392px'")
