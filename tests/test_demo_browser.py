from __future__ import annotations

import time

import pytest

from pathlib import Path
from typing import TYPE_CHECKING

from playwright.sync_api import sync_playwright

from limelight import Demo, DemoConfig, StaticApplication
from limelight.demo import locator_label
from limelight.export.cli import main

if TYPE_CHECKING:
    from collections.abc import Iterator

    from playwright.sync_api import Page


pytestmark = pytest.mark.browser


KEY_DISPLAY_WATCH_SCRIPT = """
() => {
    window.__keysShown = [];

    new MutationObserver(() => {
        const display = document.getElementById('limelight-keys');

        if (display) {
            window.__keysShown.push(display.textContent);
        }
    }).observe(document.body, {characterData: true, childList: true, subtree: true});
}
"""

LOGIN_HTML = """
<html><body>
<input id="password" type="password" aria-label="Password" />
<input id="note" aria-label="Note" />
</body></html>
"""

CONDITION_DELAY_SECONDS = 0.5

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


LOGIN_PHRASE = 'correct horse'

WALKTHROUGH_LOGIN = """\
- Fill "Password" with "********"

- Press ********

- Click "Password"

- Press Enter

- Fill "Note" with "ship it"
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


@pytest.fixture
def narrated_page(
    demo: Demo,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[Page]:
    monkeypatch.setattr('limelight.demo.DIRECTORY_ROOT', str(tmp_path))

    browser = demo.page.context.browser

    assert browser is not None

    page = browser.new_page()

    yield page

    page.close()


def demo_narrated(page: Page, *, speed_factor: float = 1000.0) -> Demo:
    application = StaticApplication(base_url='http://limelight.test')
    config = DemoConfig(mode='narrate', speed_factor=speed_factor, step_ms=1)

    return Demo(page, application, name='narrated', config=config)


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


def test_a_password_reaches_the_field_and_nothing_else(narrated_page: Page) -> None:
    demo = demo_narrated(narrated_page)
    password = narrated_page.locator('#password')
    note = narrated_page.locator('#note')

    narrated_page.set_content(LOGIN_HTML)
    narrated_page.evaluate(KEY_DISPLAY_WATCH_SCRIPT)

    demo.fill(password, LOGIN_PHRASE)
    demo.press(password, 'z')
    demo.click(password)
    demo.press(password, 'Enter')
    demo.fill(note, 'ship it')

    exit_code = main([str(demo.directory)])

    written = [path.read_text(encoding='utf-8') for path in demo.directory.iterdir()]
    walkthrough = (demo.directory / 'walkthrough.md').read_text(encoding='utf-8')
    keys_shown = narrated_page.evaluate('window.__keysShown')

    assert exit_code == 0
    assert password.input_value() == f'{LOGIN_PHRASE}z'
    assert not any(LOGIN_PHRASE in text for text in written)
    assert not any(LOGIN_PHRASE in text for text in keys_shown)
    assert 'z' not in keys_shown
    assert 'ship it' in keys_shown
    assert 'Enter' in keys_shown
    assert walkthrough == WALKTHROUGH_LOGIN


def test_wait_until_outlasts_a_pending_skip(narrated_page: Page) -> None:
    demo = demo_narrated(narrated_page, speed_factor=1.0)

    narrated_page.set_content(LOGIN_HTML)

    demo.pause()

    narrated_page.locator('#limelight-control-skip').click()

    ready_at = time.monotonic() + CONDITION_DELAY_SECONDS

    demo.wait_until(lambda: time.monotonic() > ready_at)


def test_wait_until_outlasts_turbo(narrated_page: Page) -> None:
    demo = demo_narrated(narrated_page)

    narrated_page.set_content(LOGIN_HTML)

    ready_at = time.monotonic() + CONDITION_DELAY_SECONDS

    demo.wait_until(lambda: time.monotonic() > ready_at)
