from __future__ import annotations

from typing import TYPE_CHECKING

from playwright.sync_api import expect, sync_playwright

from limelight import (
    Demo,
    DemoConfig,
    StaticApplication,
    requests_settled,
    trigger_until_visible,
)

if TYPE_CHECKING:
    from playwright.sync_api import Browser, Route


BASE_URL = 'http://shop.example.com'

CLICK_TIMEOUT_MS = 300

NARRATED = DemoConfig(mode='narrate', speed_factor=1000.0, step_ms=1)

PAGE_HTML = """
<html><body>
<h1>Order SHOP-214</h1>
<button id="approve">Approve</button>
<p id="approved" hidden>Approved by Riley Chen</p>
<button id="save" onclick="noteSave(this)">Save note</button>
<p id="saved" hidden>Note saved</p>
<script>
function approve() {
    document.querySelector('#approved').hidden = false;
}

async function noteSave() {
    await fetch('/orders/SHOP-214/note', {method: 'POST'});

    document.querySelector('#saved').hidden = false;
}

document.addEventListener('click', () => {
    document.querySelector('#approve').onclick = approve;
}, {once: true});
</script>
</body></html>
"""


def main() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()

        order_approve(browser, DemoConfig())
        order_approve(browser, NARRATED)

        browser.close()


def order_approve(browser: Browser, config: DemoConfig) -> None:
    page = browser.new_page()

    page.route(f'{BASE_URL}/**', orders_serve)

    application = StaticApplication(base_url=BASE_URL)
    demo = Demo(page, application, name='lost-click', config=config)

    demo.goto('/orders/SHOP-214')

    button = page.get_by_role('button', name='Approve')

    trigger_until_visible(
        page.get_by_text('Approved by Riley Chen'),
        lambda: demo.click(button),
        timeout_ms=CLICK_TIMEOUT_MS,
    )

    with requests_settled(page, url_fragment='/orders/SHOP-214/note'):
        demo.click(page.get_by_role('button', name='Save note'))

    expect(page.get_by_text('Note saved')).to_be_visible()

    page.close()


def orders_serve(route: Route) -> None:
    if route.request.method == 'POST':
        route.fulfill(status=204)
    else:
        route.fulfill(body=PAGE_HTML, content_type='text/html')


if __name__ == '__main__':
    main()
