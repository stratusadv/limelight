from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from playwright.sync_api import expect

if TYPE_CHECKING:
    from playwright.sync_api import Locator, Page


SLIDE_STEP_COUNT_DEFAULT = 25


@dataclass(frozen=True)
class SlideGeometry:
    """
    The coordinates a slider drag runs between.

    This class holds the page positions measured once, before the mouse is
    pressed, so a drag never re-reads a box that the drag itself has moved.
    """

    x_end: float
    x_start: float
    y_center: float


def slide_geometry(*, track: Locator, thumb: Locator) -> SlideGeometry:
    """
    A function that measures the drag path across a slider.

    :param track: The locator for the slider track.
    :param thumb: The locator for the slider handle.
    :return: The start, end, and vertical center of the drag.
    :raises ValueError: If either element has no bounding box.
    """

    track_box = track.bounding_box()
    thumb_box = thumb.bounding_box()

    if track_box is None:
        message = 'track has no bounding box; is it visible?'
        raise ValueError(message)

    if thumb_box is None:
        message = 'thumb has no bounding box; is it visible?'
        raise ValueError(message)

    return SlideGeometry(
        x_end=track_box['x'] + track_box['width'],
        x_start=thumb_box['x'] + thumb_box['width'] / 2,
        y_center=thumb_box['y'] + thumb_box['height'] / 2,
    )


def slide_to_end(
    page: Page,
    *,
    track: Locator,
    thumb: Locator,
    step_count: int = SLIDE_STEP_COUNT_DEFAULT,
) -> None:
    """
    A function that drags a slider handle to the far end of its track.

    The move is broken into steps because a single jump emits one mouse event,
    and a slider that listens for movement never sees the intermediate values.

    :param page: The page that owns the slider.
    :param track: The locator for the slider track.
    :param thumb: The locator for the slider handle.
    :param step_count: The number of mouse moves the drag is split into.
    :raises ValueError: If the step count is not positive.
    """

    if step_count < 1:
        message = f'step_count must be positive: {step_count}'
        raise ValueError(message)

    expect(thumb).to_be_visible()

    geometry = slide_geometry(track=track, thumb=thumb)

    page.mouse.move(geometry.x_start, geometry.y_center)
    page.mouse.down()
    page.mouse.move(geometry.x_end, geometry.y_center, steps=step_count)
    page.mouse.up()
