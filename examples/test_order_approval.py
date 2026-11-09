from __future__ import annotations

from typing import TYPE_CHECKING

from playwright.sync_api import expect

from limelight import Demo, StaticApplication

if TYPE_CHECKING:
    from playwright.sync_api import Page, Route


BASE_URL = 'http://shop.example.com'

PAGE_HTML = """
<html><body>
<h1>Order SHOP-214</h1>
<button onclick="this.textContent = 'Approved'">Approve</button>
</body></html>
"""


def order_serve(route: Route) -> None:
    route.fulfill(body=PAGE_HTML, content_type='text/html')


def test_order_approval_demo(page: Page) -> None:
    page.route(f'{BASE_URL}/**', order_serve)

    application = StaticApplication(base_url=BASE_URL)
    demo = Demo(page, application, name='order-approval')

    demo.goto('/orders/SHOP-214')
    demo.title('Order Approval', subtitle='Draft to approved.')
    demo.narrate('Approve the order', body='Riley Chen signs off on SHOP-214.')
    demo.click(page.get_by_role('button', name='Approve'))

    expect(page.get_by_role('button', name='Approved')).to_be_visible()
