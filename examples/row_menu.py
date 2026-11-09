from __future__ import annotations

from typing import TYPE_CHECKING

from playwright.sync_api import expect, sync_playwright

from limelight import (
    Confirm,
    Demo,
    DemoConfig,
    Dropdown,
    StaticApplication,
    trigger_until_response,
)

if TYPE_CHECKING:
    from playwright.sync_api import Browser, Route


BASE_URL = 'http://shop.example.com'

NARRATED = DemoConfig(mode='narrate', speed_factor=1000.0, step_ms=1)

PAGE_HTML = """
<html><body>
<h1>Orders</h1>
<table>
<tr id="SHOP-214"><td>SHOP-214</td><td>
    <button class="menu-toggle" onclick="menuOpen(this)">Actions</button>
    <ul class="menu" hidden><li class="menu-item" onclick="promptOpen(this)">Delete</li></ul>
    <span class="prompt" hidden>
        <button class="danger" onclick="orderDelete(this)">Delete</button>
    </span>
</td></tr>
<tr id="SHOP-215"><td>SHOP-215</td><td>
    <button class="menu-toggle" onclick="menuOpen(this)">Actions</button>
    <ul class="menu" hidden><li class="menu-item" onclick="promptOpen(this)">Delete</li></ul>
    <span class="prompt" hidden>
        <button class="danger" onclick="orderDelete(this)">Delete</button>
    </span>
</td></tr>
</table>
<script>
function menuOpen(button) {
    button.nextElementSibling.hidden = false;
}

function promptOpen(item) {
    item.closest('.menu').hidden = true;
    item.closest('td').querySelector('.prompt').hidden = false;
}

async function orderDelete(button) {
    const row = button.closest('tr');

    await fetch(`/orders/${row.id}`, {method: 'DELETE'});

    row.remove();
}
</script>
</body></html>
"""


class DangerConfirm(Confirm):
    button_selector = '.danger'


class RowMenu(Dropdown):
    item_selector = '.menu-item'
    menu_selector = '.menu'
    trigger_selector = '.menu-toggle'


def main() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()

        order_delete(browser, DemoConfig())
        order_delete(browser, NARRATED)

        browser.close()


def order_delete(browser: Browser, config: DemoConfig) -> None:
    page = browser.new_page()

    page.route(f'{BASE_URL}/**', orders_serve)

    application = StaticApplication(base_url=BASE_URL)
    demo = Demo(page, application, name='row-menu', config=config)

    demo.goto('/orders')

    row = page.locator('tr', has_text='SHOP-214')

    RowMenu(demo, row).choose('Delete', label='Delete this order')

    trigger_until_response(
        page,
        lambda: DangerConfirm(demo, row).accept('Delete'),
        method='DELETE',
    )

    expect(row).to_have_count(0)
    expect(page.locator('tr', has_text='SHOP-215')).to_have_count(1)

    page.close()


def orders_serve(route: Route) -> None:
    if route.request.method == 'DELETE':
        route.fulfill(status=204)
    else:
        route.fulfill(body=PAGE_HTML, content_type='text/html')


if __name__ == '__main__':
    main()
