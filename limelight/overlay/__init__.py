from __future__ import annotations

import contextlib

from typing import TYPE_CHECKING

from playwright.sync_api import Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError

from limelight.gestures import slide_geometry
from limelight.javascript import script

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from playwright.sync_api import Locator, Page

    from limelight.capture.camera import Camera
    from limelight.ledger import LedgerRow
    from limelight.overlay.bridge import Bridge
    from limelight.overlay.cursor import Cursor
    from limelight.overlay.keyboard import Keyboard
    from limelight.overlay.playback import Playback


CARD_FADE_MS = 450
SCROLL_SETTLE_MS = 250
SCROLL_TIMEOUT_MS = 4000
SELECT_DROPDOWN_BEAT_MS = 250
SELECT_OPTION_LABELS_SCRIPT = script('select_option_labels.js')
SELECT_OPTION_LABELS_TIMEOUT_MS = 2000
SETTLE_MS_MAX = 2000
SLIDE_MS = 700


class Overlay:
    """
    A narrator that performs each action as a viewer would see it done.

    This class moves the drawn cursor onto the element, plays a click, and lets the
    real mouse follow, falling back to Playwright whenever the element cannot be
    reached at a point. The narration cards and the spotlight are drawn through the
    same bridge.
    """

    def __init__(
        self,
        bridge: Bridge,
        playback: Playback,
        cursor: Cursor,
        keyboard: Keyboard,
        *,
        camera: Camera | None = None,
    ) -> None:
        """
        The constructor for the Overlay class.

        :param bridge: The bridge into the overlay running on the page.
        :param playback: The playback clock the actions are paced against.
        :param cursor: The pointer the actions are performed with.
        :param keyboard: The typist the keystrokes are performed with.
        :param camera: The camera screenshots are taken with, or None for a run that takes none.
        """

        self._bridge = bridge
        self._camera = camera
        self._cursor = cursor
        self._keyboard = keyboard
        self._playback = playback

    def _approach(self, locator: Locator) -> tuple[float, float] | None:
        """
        A method that settles the page, scrolls to an element, and glides onto it.

        :param locator: The locator for the element to approach.
        :return: The point the pointer arrived at, or None if the element never resolved.
        """

        self._settle()
        self._scroll(locator)

        return self._cursor.glide(locator)

    def _card(self, name: str, argument: Mapping[str, object], ms: int | None) -> None:
        """
        A method that shows a full-screen card and clears it again.

        The fade is waited out ungated, so a viewer who skips the card lands on the
        next step rather than on the card mid-fade.

        :param name: The name of the card on the overlay API.
        :param argument: The content of the card.
        :param ms: The time the card is held on screen, or None for the default.
        """

        self._bridge.call('spotClear')
        self._bridge.call('captionRemove')
        self._bridge.call('backdropRemove')
        self._bridge.call(name, argument)

        self._playback.wait(self._playback.step_ms_of(ms))

        self._bridge.call(f'{name}Hide')
        self._playback.wait(CARD_FADE_MS, gated=False)
        self._bridge.call(f'{name}Remove')

    def _checkbox_drive(
        self,
        locator: Locator,
        point: tuple[float, float] | None,
        *,
        checked_target: bool,
    ) -> None:
        """
        A method that brings a checkbox to the state asked for.

        The state is read before and after the click, because a checkbox can carry a
        label that toggles it a second time, and a blind click would leave it where it
        started.

        :param locator: The locator for the checkbox.
        :param point: The point the pointer arrived at, or None if the element never resolved.
        :param checked_target: The state the checkbox is driven to.
        """

        if self._checked_state(locator) is checked_target:
            return

        if point is not None:
            if self._cursor.hits(locator, point):
                self._cursor.press(point)

        if self._checked_state(locator) is checked_target:
            return

        if checked_target:
            locator.check()
        else:
            locator.uncheck()

    def _checked_state(self, locator: Locator) -> bool | None:
        """
        A method that reads whether a checkbox is checked.

        :param locator: The locator for the checkbox.
        :return: The state of the checkbox, or None if it could not be read.
        """

        state = None

        with contextlib.suppress(PlaywrightError):
            state = locator.is_checked()

        return state

    def _click(self, locator: Locator, *, force: bool) -> None:
        """
        A method that clicks an element under the drawn pointer.

        The click is delivered at the point only when the point reaches the element, so
        an element under a sticky header is clicked through Playwright instead of at a
        coordinate the page would hand to the header.

        :param locator: The locator for the element to click.
        :param force: Whether to click without waiting for the element to be actionable.
        """

        point = self._approach(locator)

        self._cursor.pulse()

        if point is None:
            locator.click(force=force)

            return

        if force or self._cursor.hits(locator, point):
            self._cursor.press(point)
        else:
            locator.click()

    def _scroll(self, locator: Locator) -> None:
        """
        A method that scrolls an element into view and waits for the page to settle.

        :param locator: The locator for the element to scroll to.
        """

        with contextlib.suppress(PlaywrightTimeoutError):
            locator.scroll_into_view_if_needed(timeout=SCROLL_TIMEOUT_MS)

        self._playback.wait(SCROLL_SETTLE_MS, gated=False)

    def _select_dropdown_walk(self, locator: Locator, labels: list[str], option_label: str) -> None:
        """
        A method that plays a drawn dropdown and walks the pointer to an option.

        The dropdown a browser renders for a select element is drawn outside the page
        and never appears in the capture, so the overlay draws its own to show the
        choice being made.

        :param locator: The locator for the select element.
        :param labels: The visible text of each option.
        :param option_label: The visible text of the option being picked.
        """

        box = locator.bounding_box()

        if box is None:
            return

        index = labels.index(option_label)
        argument = {'box': box, 'options': labels, 'index': index}
        target = self._bridge.call('selectShow', argument)

        self._playback.wait(SELECT_DROPDOWN_BEAT_MS, gated=False)

        if isinstance(target, dict):
            self._cursor.travel(x=float(target['x']), y=float(target['y']))

            mark_argument = {'index': index}
            self._bridge.call('selectMark', mark_argument)
            self._cursor.pulse()

        self._playback.wait(SELECT_DROPDOWN_BEAT_MS, gated=False)
        self._bridge.call('selectHide')

    def _select_option_labels(self, locator: Locator) -> list[str]:
        """
        A method that reads the visible text of each option in a select element.

        :param locator: The locator for the select element.
        :return: The label of each option, or an empty list if they could not be read.
        """

        labels: list[str] = []

        with contextlib.suppress(PlaywrightError):
            labels_raw = locator.evaluate(
                SELECT_OPTION_LABELS_SCRIPT,
                timeout=SELECT_OPTION_LABELS_TIMEOUT_MS,
            )

            labels = [str(label) for label in labels_raw]

        return labels

    def _settle(self) -> None:
        """A method that waits for the page animations to come to rest."""

        with contextlib.suppress(PlaywrightError):
            self._bridge.call('settle', {'ms': SETTLE_MS_MAX})

    def _toggle(self, locator: Locator, *, checked_target: bool) -> None:
        """
        A method that approaches a checkbox and drives it to a state.

        :param locator: The locator for the checkbox.
        :param checked_target: The state the checkbox is driven to.
        """

        point = self._approach(locator)

        self._cursor.pulse()
        self._checkbox_drive(locator, point, checked_target=checked_target)
        self.pause()

    def check(self, locator: Locator) -> None:
        """
        A method that checks a checkbox.

        :param locator: The locator for the checkbox.
        """

        self._toggle(locator, checked_target=True)

    def click(self, locator: Locator, *, force: bool = False) -> None:
        """
        A method that clicks an element.

        :param locator: The locator for the element to click.
        :param force: Whether to click without waiting for the element to be actionable.
        """

        self._click(locator, force=force)
        self.pause()

    def fill(self, locator: Locator, value: str) -> None:
        """
        A method that types text into a field.

        A field that cannot be typed into faithfully is filled in one go, because a
        date or a range control turns the keystrokes into a value of its own.

        :param locator: The locator for the field.
        :param value: The text to put into the field.
        """

        self._click(locator, force=False)

        if self._keyboard.types_faithfully(locator):
            self._keyboard.type(locator, value)
        else:
            locator.fill(value)

        self.pause()

    def hover(self, locator: Locator) -> None:
        """
        A method that hovers over an element.

        :param locator: The locator for the element to hover over.
        """

        point = self._approach(locator)

        if point is not None and self._cursor.hits(locator, point):
            self._cursor.move(point)
        else:
            locator.hover()

        self.pause()

    def metrics(
        self,
        title: str,
        rows: list[LedgerRow],
        *,
        kicker: str = '',
        subtitle: str = '',
        ms: int | None = None,
    ) -> None:
        """
        A method that shows a table of before and after readings.

        :param title: The heading for the table.
        :param rows: The rendered comparison of each metric.
        :param kicker: The line above the heading.
        :param subtitle: The line below the heading.
        :param ms: The time the table is held on screen, or None for the default.
        """

        argument = {'title': title, 'kicker': kicker, 'subtitle': subtitle, 'rows': rows}

        self._card('metrics', argument, ms)

    def narrate(
        self,
        title: str,
        *,
        body: str = '',
        step: str = '',
        ms: int | None = None,
    ) -> None:
        """
        A method that shows a caption over a dimmed page.

        :param title: The heading for the caption.
        :param body: The paragraph below the heading.
        :param step: The label naming where the demo is in its script.
        :param ms: The time the caption is held on screen, or None for the default.
        """

        self._bridge.call('spotClear')
        self._bridge.call('backdropShow')

        argument = {'title': title, 'body': body, 'step': step}
        self._bridge.call('caption', argument)

        self._playback.wait(self._playback.step_ms_of(ms))

        self._bridge.call('captionRemove')
        self._bridge.call('backdropRemove')

    def pause(self, ms: int | None = None) -> None:
        """
        A method that holds the demo without showing anything.

        :param ms: The time to hold for, or None for the default.
        """

        self._playback.wait(self._playback.step_ms_of(ms))

    def press(self, locator: Locator, key: str) -> None:
        """
        A method that presses a key on an element.

        :param locator: The locator for the element the key is pressed on.
        :param key: The key to press.
        """

        self._settle()
        self._keyboard.press(locator, key)
        self.pause()

    def screenshot(self, name: str) -> Path | None:
        """
        A method that captures the page without the overlay chrome.

        The control bar and the pointer are hidden for the shot, because they belong to
        the recording rather than to the application being documented.

        :param name: The label for the shot.
        :return: The path the screenshot was written to, or None if the run takes no shots.
        """

        if self._camera is None:
            return None

        self._bridge.call('controlHide')
        self._cursor.hide()

        path = self._camera.screenshot(name)

        self._bridge.call('controlShow')
        self._cursor.show()

        return path

    def select(self, locator: Locator, option_label: str) -> None:
        """
        A method that picks an option from a select element by its label.

        :param locator: The locator for the select element.
        :param option_label: The visible text of the option to pick.
        """

        point = self._approach(locator)

        self._cursor.pulse()

        if point is not None:
            labels = self._select_option_labels(locator)

            if option_label in labels:
                self._select_dropdown_walk(locator, labels, option_label)

        locator.select_option(label=option_label)
        self.pause()

    def slide(self, *, track: Locator, thumb: Locator) -> None:
        """
        A method that drags a slider handle to the end of its track.

        :param track: The locator for the slider track.
        :param thumb: The locator for the slider handle.
        """

        self._approach(thumb)
        self._cursor.pulse()

        geometry = slide_geometry(track=track, thumb=thumb)
        slide_ms = int(SLIDE_MS / self._playback.speed_factor_live)

        self._cursor.drag(
            x_start=geometry.x_start,
            x_end=geometry.x_end,
            y=geometry.y_center,
            ms=slide_ms,
        )

        self.pause()

    def spotlight(
        self,
        locator: Locator,
        *,
        label: str = '',
        dim: bool = True,
        scroll: bool = True,
        ms: int | None = None,
    ) -> None:
        """
        A method that highlights an element and dims the rest of the page.

        :param locator: The locator for the element to highlight.
        :param label: The caption shown beside the element.
        :param dim: Whether the rest of the page is dimmed.
        :param scroll: Whether the element is scrolled into view first.
        :param ms: The time the highlight is held, or None for the default.
        """

        self._bridge.call('captionRemove')
        self._bridge.call('backdropRemove')

        if scroll:
            self._scroll(locator)

        box = self._cursor.box(locator)

        if box is not None:
            argument = {'box': box, 'label': label, 'dim': dim}
            self._bridge.call('spot', argument)

        self._playback.wait(self._playback.step_ms_of(ms))
        self._bridge.call('spotClear')

    def switch_page(self, page: Page) -> None:
        """
        A method that points the overlay at a different page.

        :param page: The page later actions are performed on.
        """

        self._bridge.switch_page(page)

        if self._camera is not None:
            self._camera.switch_page(page)

    def title(
        self,
        text: str,
        *,
        kicker: str = '',
        subtitle: str = '',
        ms: int | None = None,
    ) -> None:
        """
        A method that shows a full-screen title card.

        :param text: The heading for the card.
        :param kicker: The line above the heading.
        :param subtitle: The line below the heading.
        :param ms: The time the card is held on screen, or None for the default.
        """

        argument = {'kicker': kicker, 'title': text, 'subtitle': subtitle}

        self._card('title', argument, ms)

    def uncheck(self, locator: Locator) -> None:
        """
        A method that clears a checkbox.

        :param locator: The locator for the checkbox.
        """

        self._toggle(locator, checked_target=False)

    def wait(self, ms: int) -> None:
        """
        A method that holds the demo for a duration.

        The hold is ungated, so a wait that covers work the page is doing cannot be
        skipped out from under it.

        :param ms: The time to hold for.
        """

        self._playback.wait(ms, gated=False)
