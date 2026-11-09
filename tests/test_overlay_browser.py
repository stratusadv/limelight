from __future__ import annotations

import pytest

from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

from limelight.config import DemoConfig
from limelight.overlay.bridge import Bridge
from limelight.overlay.cursor import Cursor
from limelight.overlay.keyboard import Keyboard
from limelight.overlay.overlay import Overlay
from limelight.overlay.playback import Playback
from limelight.theme import Theme

if TYPE_CHECKING:
    from collections.abc import Iterator

    from playwright.sync_api import Page, Route


pytestmark = pytest.mark.browser


FRAMES_HOLD_SCRIPT = """
() => {
    window.__framesHeld = [];
    window.__framesNative = [window.requestAnimationFrame, window.cancelAnimationFrame];
    window.requestAnimationFrame = (callback) => window.__framesHeld.push(callback);
    window.cancelAnimationFrame = (handle) => {
        window.__framesHeld[handle - 1] = null;
    };
}
"""

FRAMES_RELEASE_SCRIPT = """
() => {
    [window.requestAnimationFrame, window.cancelAnimationFrame] = window.__framesNative;
    window.__framesHeld.forEach((callback) => callback?.(performance.now()));
}
"""

HIDDEN_SCRIPT = "(id) => !document.getElementById(id).classList.contains('show')"
KEY_FLASH_WAIT_MS = 1200

STORAGE_REFUSED_SCRIPT = """
() => {
    try {
        return window.sessionStorage === null;
    } catch (error) {
        return error.name === 'SecurityError';
    }
}
"""

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

SITE_PAGES = MappingProxyType(
    {
        '/first': PAGE_HTML_LINK,
        '/second': PAGE_HTML_SECOND,
    },
)

SCROLLBAR_WIDTH_PX = 17

SCROLLBAR_SHOW_SCRIPT = """
(width) => Object.defineProperty(window.visualViewport, 'width', {
    configurable: true,
    get: () => window.innerWidth - width,
})
"""

SCROLLBAR_HIDE_SCRIPT = '() => delete window.visualViewport.width'

SPOT_RECT_SCRIPT = """
() => {
    let rect = document.getElementById('limelight-spot').getBoundingClientRect();

    return {
        bottom: rect.bottom,
        left: rect.left,
        right: rect.right,
        top: rect.top,
        viewport_height: window.innerHeight,
        viewport_width: window.innerWidth,
    };
}
"""


@pytest.fixture(scope='module')
def browser_page() -> Iterator[Page]:
    with sync_playwright() as playwright:
        executable = Path(playwright.chromium.executable_path)

        if not executable.exists():
            pytest.skip('chromium is not installed; run `playwright install chromium`')

        browser = playwright.chromium.launch()

        yield browser.new_page()

        browser.close()


@pytest.fixture(scope='module')
def demo_page(browser_page: Page) -> tuple[Page, Overlay]:
    config = DemoConfig(mode='narrate', step_ms=1, speed_factor=20.0)

    return browser_page, overlay_build(browser_page, config)


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
        '() => window.__limelight.caption('
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


def test_hide_cancels_a_show_waiting_for_its_frame(demo_page: tuple[Page, Overlay]) -> None:
    page, overlay = demo_page

    overlay_install(page, overlay, PAGE_HTML)

    page.evaluate(FRAMES_HOLD_SCRIPT)
    page.evaluate("() => window.__limelight.caption({title: 'Held'})")
    page.evaluate('() => window.__limelight.captionHide()')
    page.evaluate(FRAMES_RELEASE_SCRIPT)

    assert page.evaluate(HIDDEN_SCRIPT, 'limelight-caption') is True


def test_key_flash_clears_after_a_late_frame(demo_page: tuple[Page, Overlay]) -> None:
    page, overlay = demo_page

    overlay_install(page, overlay, PAGE_HTML)

    page.evaluate(FRAMES_HOLD_SCRIPT)
    page.evaluate("() => window.__limelight.keyFlash({text: 'Enter'})")
    page.wait_for_timeout(KEY_FLASH_WAIT_MS)
    page.evaluate(FRAMES_RELEASE_SCRIPT)

    assert page.evaluate(HIDDEN_SCRIPT, 'limelight-keys') is False

    page.wait_for_function(HIDDEN_SCRIPT, arg='limelight-keys', timeout=KEY_FLASH_WAIT_MS * 2)


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


def test_control_bar_clears_a_scrollbar_when_the_page_resizes(
    demo_page: tuple[Page, Overlay],
) -> None:
    page, overlay = demo_page

    overlay_install(page, overlay, PAGE_HTML)

    page.evaluate(SCROLLBAR_SHOW_SCRIPT, SCROLLBAR_WIDTH_PX)
    page.evaluate("() => document.documentElement.style.width = '50%'")

    page.wait_for_function(
        f"() => document.getElementById('limelight-control').style.right"
        f" === '{32 - SCROLLBAR_WIDTH_PX}px'",
    )

    page.evaluate(SCROLLBAR_HIDE_SCRIPT)


def test_control_bar_clears_a_scrollbar_when_the_viewport_resizes(
    demo_page: tuple[Page, Overlay],
) -> None:
    page, overlay = demo_page

    overlay_install(page, overlay, PAGE_HTML)

    page.evaluate(SCROLLBAR_SHOW_SCRIPT, SCROLLBAR_WIDTH_PX)
    page.evaluate("() => window.visualViewport.dispatchEvent(new Event('resize'))")

    page.wait_for_function(
        f"() => document.getElementById('limelight-control').style.right"
        f" === '{32 - SCROLLBAR_WIDTH_PX}px'",
    )

    page.evaluate(SCROLLBAR_HIDE_SCRIPT)


def test_control_buttons_act_on_press_not_click(demo_page: tuple[Page, Overlay]) -> None:
    page, overlay = demo_page

    overlay_install(page, overlay, PAGE_HTML)

    button = page.locator('#limelight-control-pause')
    paused = '() => window.__limelight.controlPeek().paused'
    paused_start = page.evaluate(paused)

    button.dispatch_event('pointerdown')

    paused_pressed = page.evaluate(paused)

    button.dispatch_event('click', {'detail': 1})

    paused_clicked = page.evaluate(paused)

    button.dispatch_event('click', {'detail': 0})

    paused_activated = page.evaluate(paused)

    assert paused_pressed is not paused_start
    assert paused_clicked is paused_pressed
    assert paused_activated is paused_start


def test_install_sets_the_theme_properties(demo_page: tuple[Page, Overlay]) -> None:
    page, overlay = demo_page

    overlay_install(page, overlay, PAGE_HTML)

    theme = Theme()
    read = '(name) => document.documentElement.style.getPropertyValue(name)'

    assert page.evaluate(read, '--limelight-accent') == theme.color_accent
    assert page.evaluate(read, '--limelight-spotlight') == theme.color_spotlight
    assert page.evaluate(read, '--limelight-font') == theme.font_family


def test_overlay_runs_on_a_page_that_refuses_session_storage(browser_page: Page) -> None:
    config = DemoConfig(mode='narrate', step_ms=1, speed_factor=20.0)
    overlay = overlay_build(browser_page, config)

    browser_page.goto('data:text/html,<html><body style="margin:0"></body></html>')
    overlay._bridge.ensure()

    refused = browser_page.evaluate(STORAGE_REFUSED_SCRIPT)
    duration = browser_page.evaluate('() => window.__limelight.cursorMove({x: 40, y: 40, ms: 10})')
    state = browser_page.evaluate('() => window.__limelight.controlPeek()')

    assert refused is True
    assert isinstance(duration, int)
    assert state['speedFactor'] == config.speed_factor


def test_spot_follows_page_scroll(demo_page: tuple[Page, Overlay]) -> None:
    page, overlay = demo_page

    overlay_install(page, overlay, PAGE_HTML_TALL)

    page.evaluate(
        '() => window.__limelight.spot('
        "{box: {x: 0, y: 500, width: 100, height: 50}, label: '', dim: true})",
    )
    page.evaluate('() => window.scrollTo(0, 100)')
    page.wait_for_function("() => document.getElementById('limelight-spot').style.top === '392px'")


def test_spot_follows_page_scroll_after_a_repeated_install(
    demo_page: tuple[Page, Overlay],
) -> None:
    page, overlay = demo_page

    overlay_install(page, overlay, PAGE_HTML_TALL)

    page.evaluate('() => window.scrollTo(0, 0)')

    page.evaluate(
        '() => window.__limelight.spot('
        "{box: {x: 0, y: 500, width: 100, height: 50}, label: '', dim: true})",
    )

    overlay._bridge.ensure()

    page.evaluate('() => window.scrollTo(0, 100)')
    page.wait_for_function("() => document.getElementById('limelight-spot').style.top === '392px'")


def test_spot_frames_an_element_inside_the_viewport_evenly(
    demo_page: tuple[Page, Overlay],
) -> None:
    page, overlay = demo_page

    overlay_install(page, overlay, PAGE_HTML)

    page.evaluate(
        '() => window.__limelight.spot('
        "{box: {x: 40, y: 40, width: 120, height: 32}, label: '', dim: true})",
    )

    spot = page.evaluate(SPOT_RECT_SCRIPT)

    assert spot['left'] < 40
    assert spot['top'] < 40
    assert spot['right'] - 160 == 40 - spot['left']
    assert spot['bottom'] - 72 == 40 - spot['top']


def test_spot_keeps_every_edge_on_screen_when_its_element_runs_past_the_viewport(
    demo_page: tuple[Page, Overlay],
) -> None:
    page, overlay = demo_page

    overlay_install(page, overlay, PAGE_HTML)

    page.evaluate(
        '() => window.__limelight.spot({box: {x: -40, y: 120,'
        ' width: window.innerWidth + 80, height: window.innerHeight},'
        " label: 'Flow', dim: true})",
    )

    spot = page.evaluate(SPOT_RECT_SCRIPT)

    assert spot['left'] > 0
    assert spot['top'] > 0
    assert spot['right'] < spot['viewport_width']
    assert spot['bottom'] < spot['viewport_height']
