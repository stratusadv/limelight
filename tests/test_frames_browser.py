from __future__ import annotations

import pytest

from pathlib import Path
from typing import TYPE_CHECKING

from playwright.sync_api import sync_playwright

from limelight.frames import DirectorySink, FrameRenderer, endpoint_free, launch_arguments_frame_control

if TYPE_CHECKING:
    from collections.abc import Iterator

    from playwright.sync_api import Page


pytestmark = pytest.mark.browser


PAGE_HTML = """
<html><head><style>
#box { position: absolute; left: 0; top: 100px; width: 200px; height: 200px; background: #36c; transition: left 1s; }
</style></head><body style="margin:0;background:#eef">
<div id="box"></div>
<script>window.go = () => { document.getElementById('box').style.left = '1000px'; };</script>
</body></html>
"""

FPS = 30
TRANSITION_MS = 1000


@pytest.fixture(scope='module')
def rendered_page() -> Iterator[tuple[Page, str]]:
    with sync_playwright() as playwright:
        executable = Path(playwright.chromium.executable_path)

        if not executable.exists():
            pytest.skip('chromium is not installed; run `playwright install chromium`')

        endpoint = endpoint_free()
        browser = playwright.chromium.launch(args=launch_arguments_frame_control(endpoint))
        page = browser.new_page(viewport={'width': 1280, 'height': 720})

        page.set_content(PAGE_HTML)

        yield page, endpoint

        browser.close()


def test_every_frame_interval_produces_one_frame(rendered_page: tuple[Page, str], tmp_path: Path) -> None:
    page, endpoint = rendered_page
    directory = tmp_path / 'frames'
    renderer = FrameRenderer(page, endpoint=endpoint, fps=FPS)

    renderer.start(DirectorySink(directory))

    frame_count_before = renderer.frame_count

    page.evaluate('go()')
    renderer.wait_ms(TRANSITION_MS)
    renderer.stop()

    frame_count_after = renderer.frame_count
    frames = sorted(directory.glob('frame-*.png'))
    frames_moving = [
        frame
        for frame, frame_next in zip(frames[frame_count_before:], frames[frame_count_before + 1:], strict=False)
        if frame.read_bytes() != frame_next.read_bytes()
    ]

    assert renderer.is_running is False
    assert frame_count_after - frame_count_before >= TRANSITION_MS * FPS // 1000
    assert len(frames) <= frame_count_after
    assert len(frames_moving) >= TRANSITION_MS * FPS // 1000 - 1


def test_static_frames_repeat_the_last_image(rendered_page: tuple[Page, str], tmp_path: Path) -> None:
    page, endpoint = rendered_page
    directory = tmp_path / 'frames'
    renderer = FrameRenderer(page, endpoint=endpoint, fps=FPS)

    page.evaluate("document.body.style.background = '#fee'")

    renderer.start(DirectorySink(directory))
    renderer.wait_ms(200)
    renderer.stop()

    frames = sorted(directory.glob('frame-*.png'))
    images = {frame.read_bytes() for frame in frames}

    assert len(frames) >= 6
    assert len(images) == 1
