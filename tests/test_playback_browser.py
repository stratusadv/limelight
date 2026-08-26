from __future__ import annotations

import time

import pytest

from pathlib import Path
from typing import TYPE_CHECKING

from playwright.sync_api import sync_playwright

from limelight.config import SPEED_FACTORS
from limelight.overlay import Overlay
from limelight.presenter import PresenterSilent
from limelight.timing import DemoTiming

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from playwright.sync_api import Browser, Page


pytestmark = pytest.mark.browser


BUSY_SCRIPT = """
() => {
    window.__busy = true;

    let burn = () => {
        if (!window.__busy) {
            return;
        }

        let end = performance.now() + 45;

        while (performance.now() < end) {
        }

        setTimeout(burn, 5);
    };

    burn();
}
"""

PAGE_FIRST = """
<html><body style="margin:0;height:900px">
<button id="go" onclick="window.clicks = (window.clicks || 0) + 1"
        style="position:absolute;left:40px;top:40px;width:120px;height:32px">Go</button>
<input id="name" style="position:absolute;left:40px;top:120px;width:200px" />
<div id="panel" tabindex="0" style="position:absolute;left:40px;top:180px;width:200px;height:40px">Panel</div>
<input id="start" type="date" name="start_date" style="position:absolute;left:40px;top:240px" />
<textarea id="notes" style="position:absolute;left:40px;top:300px"></textarea>
<script>
    window.clicks = 0;
    window.panelKeys = [];
    document.getElementById('panel').addEventListener('keydown', (event) => {
        window.panelKeys.push(event.key);
    });
</script>
</body></html>
"""

PAGE_SECOND = '<html><body style="margin:0;height:900px"><h1 id="second">Second</h1></body></html>'

PAGE_ANIMATED = """
<html><head><style>
    @keyframes pulse { from { opacity: 1; } to { opacity: .3; } }
    @keyframes veil-out { from { opacity: 1; } to { opacity: 0; } }
    #pulse {
        position: absolute; left: 400px; top: 40px; width: 16px; height: 16px;
        background: #444; animation: pulse 1s linear infinite;
    }
    #veil {
        position: fixed; inset: 0; background: rgba(0, 0, 0, .4);
        display: none; pointer-events: none;
    }
    #veil.showing { display: block; }
    #veil.hiding { display: block; animation: veil-out .6s linear; }
    #sheet { position: fixed; left: 40px; top: 300px; display: none; }
    #sheet.showing { display: block; }
</style></head>
<body style="margin:0;height:900px">
<button id="open" style="position:absolute;left:40px;top:40px;width:140px;height:32px">Open</button>
<div id="pulse"></div>
<div id="veil"></div>
<div id="sheet"><button id="confirm">Confirm</button></div>
<script>
    window.confirmations = 0;

    let veil = document.getElementById('veil');
    let sheet = document.getElementById('sheet');
    let hiding = false;

    document.getElementById('open').addEventListener('click', () => {
        if (hiding) {
            return;
        }

        veil.classList.add('showing');
        sheet.classList.add('showing');
    });

    document.getElementById('confirm').addEventListener('click', () => {
        window.confirmations += 1;
        hiding = true;

        sheet.classList.remove('showing');
        veil.classList.remove('showing');
        veil.classList.add('hiding');

        veil.addEventListener('animationend', () => {
            veil.classList.remove('hiding');
            hiding = false;
        }, { once: true });
    });
</script>
</body></html>
"""

PAGE_UNDER_BAR = """
<html><head><style>
    html { overflow-y: scroll; }
    html::-webkit-scrollbar { width: 15px; }
    html::-webkit-scrollbar-thumb { background: #888; }
</style></head>
<body style="margin:0;height:2000px">
<button id="wide" onclick="window.wideClicks = (window.wideClicks || 0) + 1"
        style="position:fixed;left:0;right:0;bottom:0;height:90px;width:100%">Clear</button>
<input id="field" style="position:absolute;left:40px;top:40px;width:200px" />
<script>
    window.wideClicks = 0;
    window.outsideClicks = 0;
    window.blurs = 0;

    document.addEventListener('click', () => { window.outsideClicks += 1; });
    document.addEventListener('mousedown', () => { window.outsideClicks += 1; });
    document.getElementById('field').addEventListener('blur', () => { window.blurs += 1; });
</script>
</body></html>
"""


PAGE_FRAMED = """
<html><body style="margin:0;height:900px">
<h1 id="host">Host</h1>
<iframe id="inner" src="http://limelight.test/first" style="width:600px;height:300px"></iframe>
</body></html>
"""

URL_FRAMED = 'http://limelight.test/framed'
URL_UNDER_BAR = 'http://limelight.test/underbar'
URL_ANIMATED = 'http://limelight.test/animated'
URL_FIRST = 'http://limelight.test/first'
URL_SECOND = 'http://limelight.test/second'


@pytest.fixture(scope='module')
def browser() -> Iterator[Browser]:
    with sync_playwright() as playwright:
        executable = Path(playwright.chromium.executable_path)

        if not executable.exists():
            pytest.skip('chromium is not installed; run `playwright install chromium`')

        browser = playwright.chromium.launch()

        yield browser

        browser.close()


@pytest.fixture
def demo_page(browser: Browser) -> Iterator[tuple[Page, Overlay]]:
    context = browser.new_context(viewport={'width': 1280, 'height': 720})
    page = context.new_page()

    page.route('**/first', lambda route: route.fulfill(content_type='text/html', body=PAGE_FIRST))
    page.route('**/second', lambda route: route.fulfill(content_type='text/html', body=PAGE_SECOND))

    overlay = Overlay(page, DemoTiming(step_ms=600), controls=True)

    page.goto(URL_FIRST)

    yield page, overlay

    context.close()


@pytest.fixture
def animated_page(browser: Browser) -> Iterator[tuple[Page, Overlay]]:
    context = browser.new_context(viewport={'width': 1280, 'height': 720})
    page = context.new_page()

    page.set_default_timeout(3000)
    page.route('**/animated', lambda route: route.fulfill(content_type='text/html', body=PAGE_ANIMATED))

    overlay = Overlay(page, DemoTiming(step_ms=600), controls=True)

    page.goto(URL_ANIMATED)

    yield page, overlay

    context.close()


@pytest.fixture
def turbo_page(browser: Browser) -> Iterator[tuple[Page, Overlay]]:
    context = browser.new_context(viewport={'width': 1280, 'height': 720})
    page = context.new_page()

    page.route('**/first', lambda route: route.fulfill(content_type='text/html', body=PAGE_FIRST))

    overlay = Overlay(page, DemoTiming(step_ms=600), controls=True, speed_factor=SPEED_FACTORS['turbo'])

    page.goto(URL_FIRST)

    yield page, overlay

    context.close()


@pytest.fixture
def under_bar_page(browser: Browser) -> Iterator[tuple[Page, Overlay]]:
    context = browser.new_context(viewport={'width': 1280, 'height': 720})
    page = context.new_page()

    page.set_default_timeout(4000)
    page.route('**/underbar', lambda route: route.fulfill(content_type='text/html', body=PAGE_UNDER_BAR))

    overlay = Overlay(page, DemoTiming(step_ms=600), controls=True)

    page.goto(URL_UNDER_BAR)

    yield page, overlay

    context.close()


@pytest.fixture
def framed_page(browser: Browser) -> Iterator[tuple[Page, Overlay]]:
    context = browser.new_context(viewport={'width': 1280, 'height': 720})
    page = context.new_page()

    page.route('**/framed', lambda route: route.fulfill(content_type='text/html', body=PAGE_FRAMED))
    page.route('**/first', lambda route: route.fulfill(content_type='text/html', body=PAGE_FIRST))

    overlay = Overlay(page, DemoTiming(step_ms=600), controls=True)

    page.goto(URL_FRAMED)

    yield page, overlay

    context.close()


@pytest.fixture
def step_page(browser: Browser) -> Iterator[tuple[Page, Overlay]]:
    context = browser.new_context(viewport={'width': 1280, 'height': 720})
    page = context.new_page()

    page.route('**/first', lambda route: route.fulfill(content_type='text/html', body=PAGE_FIRST))

    overlay = Overlay(page, DemoTiming(step_ms=600), controls=True, step_mode=True)

    page.goto(URL_FIRST)

    yield page, overlay

    context.close()


def control_peek(page: Page) -> dict[str, object]:
    return page.evaluate('() => window.__limelight.controlPeek()')


def elapsed_ms(action: Callable[[], None]) -> float:
    started = time.monotonic()

    action()

    return (time.monotonic() - started) * 1000


def test_control_bar_reaches_every_page_of_a_demo(demo_page: tuple[Page, Overlay]) -> None:
    page, _ = demo_page

    page.goto(URL_SECOND)

    assert page.evaluate("() => document.getElementById('limelight-control') !== null") is True


def test_pause_button_halts_a_hold_until_play(demo_page: tuple[Page, Overlay]) -> None:
    page, overlay = demo_page

    page.locator('#limelight-control-pause').click()
    page.evaluate("() => setTimeout(() => document.getElementById('limelight-control-pause').click(), 700)")

    held_ms = elapsed_ms(lambda: overlay.beat(300))

    assert held_ms >= 700
    assert control_peek(page)['paused'] is False


def test_pause_survives_a_page_navigation(demo_page: tuple[Page, Overlay]) -> None:
    page, _ = demo_page

    page.locator('#limelight-control-pause').click()
    page.goto(URL_SECOND)

    assert control_peek(page)['paused'] is True


def test_speed_survives_a_page_navigation(demo_page: tuple[Page, Overlay]) -> None:
    page, _ = demo_page

    page.locator('#limelight-control-faster').click()
    page.goto(URL_SECOND)

    assert control_peek(page)['speedFactor'] == 1.5


def test_space_pauses_with_focus_on_the_element_just_clicked(demo_page: tuple[Page, Overlay]) -> None:
    page, overlay = demo_page

    overlay.click(page.locator('#go'))
    page.keyboard.press('Space')

    assert control_peek(page)['paused'] is True
    assert page.evaluate('() => window.clicks') == 1


def test_skip_key_works_with_focus_on_the_element_just_clicked(demo_page: tuple[Page, Overlay]) -> None:
    page, overlay = demo_page

    overlay.click(page.locator('#go'))
    page.keyboard.press('ArrowRight')

    assert control_peek(page)['skip'] is True


def test_space_pauses_with_focus_in_the_field_just_filled(demo_page: tuple[Page, Overlay]) -> None:
    page, overlay = demo_page

    overlay.fill(page.locator('#name'), 'ab')
    page.keyboard.press('Space')

    assert control_peek(page)['paused'] is True
    assert page.locator('#name').input_value() == 'ab'


def test_driven_typing_is_not_read_as_playback_input(demo_page: tuple[Page, Overlay]) -> None:
    page, overlay = demo_page

    overlay.fill(page.locator('#name'), 'a b c')

    assert page.locator('#name').input_value() == 'a b c'
    assert control_peek(page)['paused'] is False


def test_fill_of_a_date_input_matches_the_silent_value(demo_page: tuple[Page, Overlay]) -> None:
    page, overlay = demo_page

    silent = PresenterSilent()
    silent.fill(page.locator('#start'), '2026-08-02')

    silent_value = page.locator('#start').input_value()

    page.locator('#start').fill('')
    overlay.fill(page.locator('#start'), '2026-08-02')

    assert page.locator('#start').input_value() == silent_value
    assert silent_value == '2026-08-02'


def test_fill_still_types_into_a_text_input(demo_page: tuple[Page, Overlay]) -> None:
    page, overlay = demo_page

    overlay.fill(page.locator('#name'), 'SO-100')

    assert page.locator('#name').input_value() == 'SO-100'


def test_fill_still_types_into_a_textarea(demo_page: tuple[Page, Overlay]) -> None:
    page, overlay = demo_page

    overlay.fill(page.locator('#notes'), 'a note')

    assert page.locator('#notes').input_value() == 'a note'


def test_driven_press_of_a_bound_key_reaches_the_application(demo_page: tuple[Page, Overlay]) -> None:
    page, overlay = demo_page

    overlay.press(page.locator('#panel'), 'ArrowRight')

    assert page.evaluate('() => window.panelKeys') == ['ArrowRight']
    assert control_peek(page)['skip'] is False


def test_driven_press_does_not_shift_the_speed(demo_page: tuple[Page, Overlay]) -> None:
    page, overlay = demo_page

    overlay.press(page.locator('#panel'), 'ArrowDown')

    assert control_peek(page)['speedFactor'] == 1


def test_skip_pressed_between_steps_survives_to_the_next_hold(demo_page: tuple[Page, Overlay]) -> None:
    page, overlay = demo_page

    page.locator('#limelight-control-skip').click()

    held_ms = elapsed_ms(lambda: overlay.spotlight(page.locator('#go'), label='here', ms=3000))

    assert held_ms < 1500


def test_step_mode_next_survives_an_ungated_fade(step_page: tuple[Page, Overlay]) -> None:
    page, overlay = step_page

    page.locator('#limelight-control-skip').click()
    overlay._wait(200, gated=False)

    assert control_peek(page)['skip'] is True


def test_turbo_collapses_a_long_hold(demo_page: tuple[Page, Overlay]) -> None:
    page, overlay = demo_page

    page.locator('#limelight-control-turbo').click()

    held_ms = elapsed_ms(lambda: overlay.beat(5000))

    assert held_ms < 400


def settle_ms(page: Page) -> float:
    return elapsed_ms(lambda: page.evaluate('() => window.__limelight.settle({ms: 2000})'))


def test_turbo_does_not_outrun_an_app_animation(animated_page: tuple[Page, Overlay]) -> None:
    page, overlay = animated_page

    page.locator('#limelight-control-turbo').click()

    overlay.click(page.locator('#open'))
    overlay.click(page.locator('#confirm'))
    overlay.click(page.locator('#open'))
    overlay.click(page.locator('#confirm'))

    assert page.evaluate('() => window.confirmations') == 2


def test_settle_waits_out_an_app_animation(animated_page: tuple[Page, Overlay]) -> None:
    page, _ = animated_page

    page.locator('#open').click()
    page.locator('#confirm').click()

    assert settle_ms(page) >= 300


def test_settle_ignores_an_endless_app_animation(animated_page: tuple[Page, Overlay]) -> None:
    page, _ = animated_page

    assert settle_ms(page) < 300


def test_settle_ignores_the_overlays_own_fade(animated_page: tuple[Page, Overlay]) -> None:
    page, _ = animated_page

    page.evaluate('() => window.__limelight.backdropShow()')

    assert settle_ms(page) < 300


def test_configured_turbo_starts_the_bar_engaged(turbo_page: tuple[Page, Overlay]) -> None:
    page, _ = turbo_page

    assert control_peek(page)['speedFactor'] == SPEED_FACTORS['turbo']
    assert page.locator('#limelight-control-speed').text_content() == 'Turbo'
    assert 'engaged' in (page.locator('#limelight-control-turbo').get_attribute('class') or '')


def test_configured_turbo_collapses_a_hold_with_no_button_press(turbo_page: tuple[Page, Overlay]) -> None:
    _, overlay = turbo_page

    held_ms = elapsed_ms(lambda: overlay.beat(5000))

    assert held_ms < 400


def test_configured_turbo_still_yields_to_the_bar(turbo_page: tuple[Page, Overlay]) -> None:
    page, _ = turbo_page

    page.locator('#limelight-control-turbo').click()

    assert control_peek(page)['speedFactor'] == 1


def test_control_bar_does_not_intercept_a_click_beneath_it(under_bar_page: tuple[Page, Overlay]) -> None:
    page, overlay = under_bar_page

    overlay.click(page.locator('#wide'))

    assert page.evaluate('() => window.wideClicks') == 1


def test_control_bar_does_not_intercept_a_raw_click_beneath_it(under_bar_page: tuple[Page, Overlay]) -> None:
    page, _ = under_bar_page

    page.locator('#wide').click()

    assert page.evaluate('() => window.wideClicks') == 1


def test_control_bar_buttons_stay_clickable(under_bar_page: tuple[Page, Overlay]) -> None:
    page, _ = under_bar_page

    page.locator('#limelight-control-turbo').click()

    assert control_peek(page)['speedFactor'] == 1000
    assert page.evaluate('() => window.wideClicks') == 0


def test_control_bar_clicks_do_not_reach_the_application(under_bar_page: tuple[Page, Overlay]) -> None:
    page, _ = under_bar_page

    page.locator('#limelight-control-pause').click()
    page.locator('#limelight-control-pause').click()

    assert control_peek(page)['paused'] is False
    assert page.evaluate('() => window.outsideClicks') == 0


def test_control_bar_clicks_do_not_steal_focus_from_the_application(under_bar_page: tuple[Page, Overlay]) -> None:
    page, _ = under_bar_page

    page.locator('#field').click()
    page.locator('#limelight-control-pause').click()

    assert page.evaluate('() => window.blurs') == 0
    assert page.evaluate('() => document.activeElement.id') == 'field'
    assert control_peek(page)['paused'] is True


def bar_center(page: Page) -> dict[str, float]:
    return page.evaluate(
        "() => { let r = document.getElementById('limelight-control').getBoundingClientRect();"
        ' return {x: r.x + r.width / 2, y: r.y + r.height / 2}; }'
    )


def test_control_press_survives_the_demo_driving_the_mouse(under_bar_page: tuple[Page, Overlay]) -> None:
    page, _ = under_bar_page

    pause = page.evaluate(
        "() => { let r = document.getElementById('limelight-control-pause').getBoundingClientRect();"
        ' return {x: r.x + r.width / 2, y: r.y + r.height / 2}; }'
    )

    page.mouse.move(pause['x'], pause['y'])
    page.mouse.down()
    page.mouse.move(120, 60)
    page.mouse.up()

    assert control_peek(page)['paused'] is True


def test_overlay_does_not_install_inside_an_iframe(framed_page: tuple[Page, Overlay]) -> None:
    page, _ = framed_page

    frame = page.frame_locator('#inner')

    page.wait_for_selector('#limelight-control')

    assert frame.locator('#limelight-control').count() == 0
    assert page.frames[1].evaluate('() => window.__limelight === undefined') is True


def test_overlay_still_installs_in_the_top_frame_of_a_framed_page(framed_page: tuple[Page, Overlay]) -> None:
    page, overlay = framed_page

    overlay.beat(50)

    assert page.locator('#limelight-control').count() == 1


def test_speed_label_is_separated_from_its_neighbours(demo_page: tuple[Page, Overlay]) -> None:
    page, _ = demo_page

    style = page.evaluate(
        "() => { let node = document.getElementById('limelight-control-speed');"
        ' let computed = getComputedStyle(node);'
        " return {left: computed.paddingLeft, right: computed.paddingRight, shadow: computed.boxShadow}; }"
    )

    assert style['left'] != '0px'
    assert style['right'] != '0px'
    assert style['shadow'] != 'none'


def test_last_control_button_has_no_trailing_divider(demo_page: tuple[Page, Overlay]) -> None:
    page, _ = demo_page

    shadow = page.evaluate(
        "() => getComputedStyle(document.querySelector('#limelight-control button:last-child')).boxShadow"
    )

    assert shadow == 'none'


def test_turbo_label_fits_without_resizing_the_bar(demo_page: tuple[Page, Overlay]) -> None:
    page, _ = demo_page

    width = "() => document.getElementById('limelight-control').getBoundingClientRect().width"

    width_before = page.evaluate(width)

    page.locator('#limelight-control-turbo').click()

    assert page.locator('#limelight-control-speed').text_content() == 'Turbo'
    assert page.evaluate(width) == width_before


def test_hold_lands_on_its_nominal_duration_under_a_busy_page(demo_page: tuple[Page, Overlay]) -> None:
    page, overlay = demo_page

    page.evaluate(BUSY_SCRIPT)

    held_ms = elapsed_ms(lambda: overlay.beat(3000))

    page.evaluate('() => { window.__busy = false; }')

    assert held_ms >= 3000
    assert held_ms < 3000 * 1.08


def test_repeated_installs_do_not_stack_key_handlers(demo_page: tuple[Page, Overlay]) -> None:
    page, overlay = demo_page

    overlay._ensure()
    overlay._ensure()

    page.keyboard.press('Space')

    assert control_peek(page)['paused'] is True
