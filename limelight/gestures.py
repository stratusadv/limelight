from __future__ import annotations

from typing_extensions import TYPE_CHECKING

from playwright.sync_api import expect

if TYPE_CHECKING:
    from playwright.sync_api import Locator, Page


SLIDE_STEP_COUNT_DEFAULT = 25


def slide_to_end(
    page: Page,
    *,
    track: Locator,
    thumb: Locator,
    step_count: int = SLIDE_STEP_COUNT_DEFAULT,
) -> None:
    if step_count < 1:
        message = f'step_count must be positive: {step_count}'
        raise ValueError(message)

    expect(thumb).to_be_visible()

    track_box = track.bounding_box()
    thumb_box = thumb.bounding_box()

    if track_box is None:
        message = 'track has no bounding box; is it visible?'
        raise ValueError(message)

    if thumb_box is None:
        message = 'thumb has no bounding box; is it visible?'
        raise ValueError(message)

    x_start = thumb_box['x'] + thumb_box['width'] / 2
    x_end = track_box['x'] + track_box['width']
    y_center = thumb_box['y'] + thumb_box['height'] / 2

    page.mouse.move(x_start, y_center)
    page.mouse.down()
    page.mouse.move(x_end, y_center, steps=step_count)
    page.mouse.up()
