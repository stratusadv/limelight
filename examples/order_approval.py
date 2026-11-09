from __future__ import annotations

from typing import TYPE_CHECKING

from playwright.sync_api import sync_playwright

from limelight import Demo, DemoConfig, StaticApplication

if TYPE_CHECKING:
    from playwright.sync_api import Route


BASE_URL = 'http://orders.example'

PAGE_HTML = """
<html><body>
<h1>Order SO-1042</h1>
<button onclick="this.textContent = 'Approved'">Approve</button>
</body></html>
"""


def main() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()

        page.route(f'{BASE_URL}/**', order_serve)

        application = StaticApplication(base_url=BASE_URL)
        config = DemoConfig(mode='narrate', speed_factor=1000.0, step_ms=1)
        demo = Demo(page, application, name='order-approval', config=config)

        demo.goto('/orders/1042')
        demo.title('Order Approval', subtitle='Draft to approved.')
        demo.narrate('Approve the order', body='The button stands for the whole workflow.')
        demo.click(page.get_by_role('button', name='Approve'))

        approved = page.get_by_role('button', name='Approved').is_visible()

        browser.close()

    if not approved:
        message = 'the order was not approved'
        raise RuntimeError(message)


def order_serve(route: Route) -> None:
    route.fulfill(body=PAGE_HTML, content_type='text/html')


if __name__ == '__main__':
    main()
