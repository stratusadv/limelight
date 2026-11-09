from __future__ import annotations

from typing import TYPE_CHECKING
from typing_extensions import override

from playwright.sync_api import expect, sync_playwright

from limelight import Demo, DemoConfig, Scene, StaticApplication

if TYPE_CHECKING:
    from playwright.sync_api import Browser, Locator, Route


BASE_URL = 'http://shop.example.com'

LIST_HTML = """
<html><body>
<h1>Orders</h1>
<input placeholder="Search orders" oninput="
    for (const row of document.querySelectorAll('li')) {
        row.hidden = !row.textContent.includes(this.value);
    }
">
<ul>
<li><a href="/orders/SHOP-214">SHOP-214 for Riley Chen</a></li>
<li><a href="/orders/SHOP-215">SHOP-215 for Sam Okafor</a></li>
</ul>
</body></html>
"""

NARRATED = DemoConfig(mode='narrate', speed_factor=1000.0, step_ms=1)

ORDER_HTML = """
<html><body>
<h1>Order SHOP-214</h1>
</body></html>
"""


class OrderListScene(Scene):
    route = '/orders'

    @property
    def search_field(self) -> Locator:
        return self.demo.page.get_by_placeholder('Search orders')

    @override
    def expect_ready(self) -> None:
        expect(self.search_field).to_be_visible()

    def open_order(self, number: str) -> None:
        link = self.demo.page.get_by_role('link', name=number)

        self.demo.follow(link, label=f'Open {number}')

    def search(self, text: str) -> None:
        self._teach_focus(self.search_field, headline='Search the orders', label='Search')

        self._fill(self.search_field, text)


def main() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()

        order_search(browser, DemoConfig())
        order_search(browser, NARRATED)

        browser.close()


def order_search(browser: Browser, config: DemoConfig) -> None:
    page = browser.new_page()

    page.route(f'{BASE_URL}/**', orders_serve)

    application = StaticApplication(base_url=BASE_URL)
    demo = Demo(page, application, name='order-search', config=config)

    scene = OrderListScene(demo).open()

    scene.search('SHOP-214')
    scene.open_order('SHOP-214')

    expect(page.get_by_role('heading', name='Order SHOP-214')).to_be_visible()

    page.close()


def orders_serve(route: Route) -> None:
    body = ORDER_HTML if route.request.url.endswith('SHOP-214') else LIST_HTML

    route.fulfill(body=body, content_type='text/html')


if __name__ == '__main__':
    main()
