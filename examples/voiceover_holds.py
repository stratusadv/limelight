from __future__ import annotations

import tempfile
import wave

from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

from playwright.sync_api import sync_playwright

from limelight import Demo, DemoConfig, StaticApplication
from limelight.export import transcript_load, voiceover_cues

if TYPE_CHECKING:
    from playwright.sync_api import Browser, Route


BASE_URL = 'http://shop.example.com'

CLIP_MS_PER_CHARACTER = 5

CLIP_SAMPLE_RATE = 8000
CLIP_SAMPLE_WIDTH = 2

NARRATED = DemoConfig(mode='narrate', speed_factor=1000.0, step_ms=1)

PAGE_HTML = """
<html><body>
<h1>Order SHOP-214</h1>
</body></html>
"""


def main() -> None:
    with sync_playwright() as playwright, tempfile.TemporaryDirectory() as directory:
        browser = playwright.chromium.launch()

        recording = order_walk(browser, NARRATED)
        holds = holds_measured(recording, directory=Path(directory))

        order_walk(browser, replace(NARRATED, holds=holds))

        browser.close()

    title, caption = voiceover_cues(transcript_load(recording))
    title_offset_ms, title_text = title
    caption_offset_ms, _ = caption

    if caption_offset_ms - title_offset_ms < holds[title_text]:
        message = f'the title gave way before its clip of {holds[title_text]}ms ended'
        raise RuntimeError(message)


def clip_write(text: str, path: Path) -> None:
    with wave.open(str(path), 'wb') as clip:
        clip.setnchannels(1)
        clip.setsampwidth(CLIP_SAMPLE_WIDTH)
        clip.setframerate(CLIP_SAMPLE_RATE)

        frame_count = len(text) * CLIP_MS_PER_CHARACTER * CLIP_SAMPLE_RATE // 1000

        clip.writeframes(bytes(frame_count * CLIP_SAMPLE_WIDTH))


def holds_measured(recording: Path, *, directory: Path) -> dict[str, int]:
    holds = {}

    for index, cue in enumerate(voiceover_cues(transcript_load(recording))):
        _, text = cue
        path = directory / f'cue-{index:02d}.wav'

        clip_write(text, path)

        with wave.open(str(path), 'rb') as clip:
            holds[text] = round(clip.getnframes() / clip.getframerate() * 1000)

    return holds


def order_serve(route: Route) -> None:
    route.fulfill(body=PAGE_HTML, content_type='text/html')


def order_walk(browser: Browser, config: DemoConfig) -> Path:
    page = browser.new_page()

    page.route(f'{BASE_URL}/**', order_serve)

    application = StaticApplication(base_url=BASE_URL)
    demo = Demo(page, application, name='voiceover-holds', config=config)

    demo.goto('/orders/SHOP-214')
    demo.title('Order Approval', subtitle='Draft to approved.')
    demo.narrate('Approve the order', body='Riley Chen signs off on SHOP-214.')

    page.close()

    return demo.directory


if __name__ == '__main__':
    main()
