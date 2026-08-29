from __future__ import annotations

import pytest

from pathlib import Path
from typing import TYPE_CHECKING

from playwright.sync_api import sync_playwright

from limelight import Demo, DemoConfig, StaticApplication
from limelight.demo import locator_label

if TYPE_CHECKING:
    from collections.abc import Iterator


pytestmark = pytest.mark.browser


PAGE_HTML = """
<html><body>
<button id="approve">Approve</button>
<label for="number">Order number</label>
<input id="number" placeholder="SO-0000" />
<label><input type="checkbox" id="urgent" /> Mark urgent</label>
<input id="plain" value="typed already" />
<input id="bare" placeholder="Search..." />
<span id="aria" aria-label="Total value"></span>
</body></html>
"""


@pytest.fixture(scope='module')
def demo() -> Iterator[Demo]:
    with sync_playwright() as playwright:
        executable = Path(playwright.chromium.executable_path)

        if not executable.exists():
            pytest.skip('chromium is not installed; run `playwright install chromium`')

        browser = playwright.chromium.launch()
        page = browser.new_page()

        page.set_content(PAGE_HTML)

        application = StaticApplication(base_url='http://limelight.test')

        yield Demo(page, application, name='labels', config=DemoConfig())

        browser.close()


def test_button_label_is_its_text(demo: Demo) -> None:
    assert locator_label(demo.page.locator('#approve')) == 'Approve'


def test_checkbox_label_is_its_caption_not_its_value(demo: Demo) -> None:
    assert locator_label(demo.page.locator('#urgent')) == 'Mark urgent'


def test_empty_input_label_is_its_field_name(demo: Demo) -> None:
    assert locator_label(demo.page.locator('#number')) == 'Order number'


def test_unlabelled_input_falls_back_to_its_value(demo: Demo) -> None:
    assert locator_label(demo.page.locator('#plain')) == 'typed already'


def test_unlabelled_empty_input_falls_back_to_its_placeholder(demo: Demo) -> None:
    assert locator_label(demo.page.locator('#bare')) == 'Search...'


def test_aria_label_is_used_when_there_is_no_text(demo: Demo) -> None:
    assert locator_label(demo.page.locator('#aria')) == 'Total value'
