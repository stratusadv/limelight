from __future__ import annotations

import contextlib

from typing import TYPE_CHECKING

from playwright.sync_api import Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError

from limelight.javascript import script

if TYPE_CHECKING:
    from collections.abc import Mapping

    from playwright.sync_api import FloatRect, Locator

    from limelight.overlay.bridge import Bridge
    from limelight.overlay.playback import Playback


BOX_POLL_MS = 60
BOX_SAMPLE_COUNT_MAX = 25
BOX_TIMEOUT_MS = 4000
DRAG_CHUNK_COUNT = 8
DRAG_MOUSE_STEP_COUNT = 3
MOVE_MS = 500
POINT_HIT_SCRIPT = script('point_hit.js')
POINT_HIT_TIMEOUT_MS = 2000
PULSE_MS = 350


class Cursor:
    """
    A driver for the pointer the viewer sees and the mouse the page receives.

    This class moves the drawn cursor and the real mouse together, so the pointer
    on screen is over the element at the moment the click lands.
    """

    def __init__(self, bridge: Bridge, playback: Playback, *, visible: bool = True) -> None:
        """
        The constructor for the Cursor class.

        :param bridge: The bridge into the overlay running on the page.
        :param playback: The playback clock the movement is paced against.
        :param visible: Whether the pointer is drawn on the page.
        """

        self._bridge = bridge
        self._playback = playback
        self._visible = visible

    def _call(self, function_name: str, argument: Mapping[str, object] | None = None) -> object:
        """
        A method that calls the overlay unless the pointer is hidden.

        An invisible pointer still moves the real mouse and still takes the time the
        movement would have taken, so a demo recorded without a pointer keeps the
        pacing of one recorded with it.

        :param function_name: The name of the function on the overlay API.
        :param argument: The value passed to the function.
        :return: The result of the function, or None if the pointer is hidden.
        """

        if not self._visible:
            return None

        return self._bridge.call(function_name, argument)

    def box(self, locator: Locator) -> FloatRect | None:
        """
        A method that waits until an element stops moving and returns its box.

        The box is polled until two consecutive readings agree, because an element that
        is still animating into place reports the position it is passing through, and a
        cursor aimed at that position lands beside the element.

        :param locator: The locator for the element to measure.
        :return: The settled bounding box, or None if the element never resolved.
        """

        box_previous = None

        for _ in range(BOX_SAMPLE_COUNT_MAX):
            try:
                box = locator.bounding_box(timeout=BOX_TIMEOUT_MS)
            except PlaywrightTimeoutError:
                return None

            if box is not None:
                if box == box_previous:
                    return box

            box_previous = box

            self._bridge.page.wait_for_timeout(BOX_POLL_MS)

        return box_previous

    def drag(self, *, x_start: float, x_end: float, y: float, ms: int) -> None:
        """
        A method that drags the pointer along a horizontal path.

        The travel is split into chunks so the drawn cursor and the real mouse advance
        together, and a control that listens for movement sees the intermediate values
        rather than one jump.

        :param x_start: The horizontal position the drag begins at.
        :param x_end: The horizontal position the drag ends at.
        :param y: The vertical position the drag holds.
        :param ms: The duration of the whole drag.
        """

        chunk_ms = max(1, ms // DRAG_CHUNK_COUNT)
        travel = x_end - x_start
        mouse = self._bridge.page.mouse

        mouse.move(x_start, y)
        mouse.down()

        for chunk_index in range(1, DRAG_CHUNK_COUNT + 1):
            x_chunk = x_start + travel * chunk_index / DRAG_CHUNK_COUNT

            argument = {'x': x_chunk, 'y': y, 'ms': chunk_ms, 'direct': True}

            self._call('cursorMove', argument)
            mouse.move(x_chunk, y, steps=DRAG_MOUSE_STEP_COUNT)
            self._playback.sleep(chunk_ms)

        mouse.up()

    def glide(self, locator: Locator) -> tuple[float, float] | None:
        """
        A method that moves the pointer to the center of an element.

        :param locator: The locator for the element to move onto.
        :return: The point the pointer arrived at, or None if the element never resolved.
        """

        box = self.box(locator)

        if box is None:
            return None

        x_center = box['x'] + box['width'] / 2
        y_center = box['y'] + box['height'] / 2

        self.travel(x=x_center, y=y_center)

        return (x_center, y_center)

    def hide(self) -> None:
        """A method that hides the drawn pointer."""

        self._call('cursorHide')

    def hits(self, locator: Locator, point: tuple[float, float]) -> bool:
        """
        A method that reports whether a point lands on an element.

        An element can be covered by a sticky header or a modal backdrop, so the point
        is tested against what the page would deliver the click to rather than against
        the element box alone.

        :param locator: The locator for the element the point is meant for.
        :param point: The page coordinates to test.
        :return: True if the point reaches the element, False otherwise.
        """

        argument = {'x': point[0], 'y': point[1]}
        hits = False

        with contextlib.suppress(PlaywrightError):
            hits = bool(locator.evaluate(POINT_HIT_SCRIPT, argument, timeout=POINT_HIT_TIMEOUT_MS))

        return hits

    def move(self, point: tuple[float, float]) -> None:
        """
        A method that moves the real mouse to a point.

        :param point: The page coordinates to move to.
        """

        self._bridge.page.mouse.move(point[0], point[1])

    def press(self, point: tuple[float, float]) -> None:
        """
        A method that clicks the real mouse at a point.

        :param point: The page coordinates to click at.
        """

        mouse = self._bridge.page.mouse

        mouse.move(point[0], point[1])
        mouse.down()
        mouse.up()

    def pulse(self) -> None:
        """A method that plays the click animation on the drawn pointer."""

        pulse_ms = int(PULSE_MS / self._playback.speed_factor_live)

        self._call('cursorPulse')
        self._playback.sleep(pulse_ms)

    def show(self) -> None:
        """A method that shows the drawn pointer."""

        self._call('cursorShow')

    def travel(self, *, x: float, y: float) -> None:
        """
        A method that animates the drawn pointer to a point and waits for it to arrive.

        The overlay returns the duration it chose, which can differ from the one asked
        for when the pointer is already close, so the wait follows the animation rather
        than a fixed time.

        :param x: The horizontal position to move to.
        :param y: The vertical position to move to.
        """

        reference_ms = int(MOVE_MS / self._playback.speed_factor_live)
        argument = {'x': x, 'y': y, 'ms': reference_ms}
        result = self._call('cursorMove', argument)
        move_ms = float(reference_ms)

        if isinstance(result, int | float):
            if not isinstance(result, bool):
                move_ms = float(result)

        self._playback.sleep(move_ms)
