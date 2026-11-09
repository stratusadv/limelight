from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

from playwright.sync_api import sync_playwright

from limelight import Demo, DemoConfig, Ledger, StaticApplication

if TYPE_CHECKING:
    from playwright.sync_api import Browser, Page, Route


BASE_URL = 'http://shop.example.com'

DELTAS_EXPECTED = ('-1', '+730 CAD')

NARRATED = DemoConfig(mode='narrate', speed_factor=1000.0, step_ms=1)

PAGE_HTML = """
<html><body>
<h1>Sales</h1>
<p>Open orders: <span id="open">3</span></p>
<p>Approved value: <span id="approved">1250.50</span></p>
<button onclick="
    document.querySelector('#open').textContent = '2';
    document.querySelector('#approved').textContent = '1980.50';
">Approve SHOP-214</button>
</body></html>
"""


def main() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()

        order_metrics(browser, DemoConfig())
        order_metrics(browser, NARRATED)

        browser.close()


def order_metrics(browser: Browser, config: DemoConfig) -> None:
    page = browser.new_page()

    page.route(f'{BASE_URL}/**', sales_serve)

    application = StaticApplication(base_url=BASE_URL)
    demo = Demo(page, application, name='order-metrics', config=config)

    demo.goto('/sales')

    ledger = (
        Ledger()
        .track('Open orders', partial(reading, page, '#open'), improves=Ledger.Direction.DOWN)
        .track('Approved value', partial(reading, page, '#approved'), unit='CAD')
    )

    before = ledger.snapshot()

    demo.click(page.get_by_role('button', name='Approve SHOP-214'))

    rows = ledger.rows(before)

    demo.metrics('What Changed', rows, kicker='Sales', subtitle='One order approved.')

    page.close()

    if tuple(row['delta'] for row in rows) != DELTAS_EXPECTED:
        message = f'the ledger read the wrong change: {rows}'
        raise RuntimeError(message)

    if rows[0]['sentiment'] is not Ledger.Sentiment.GOOD:
        message = f'fewer open orders should read as good: {rows[0]}'
        raise RuntimeError(message)


def reading(page: Page, selector: str) -> float:
    return float(page.locator(selector).inner_text())


def sales_serve(route: Route) -> None:
    route.fulfill(body=PAGE_HTML, content_type='text/html')


if __name__ == '__main__':
    main()
