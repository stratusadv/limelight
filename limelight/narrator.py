from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from limelight.gestures import slide_to_end

if TYPE_CHECKING:
    from pathlib import Path

    from playwright.sync_api import Locator, Page

    from limelight.ledger import LedgerRow


class Narrator(Protocol):
    """
    A protocol for the layer a demo performs its actions through.

    This protocol covers every action a demo takes on the page along with the
    narration drawn over it, so a run can swap a silent implementation for a
    presenting one without the demo code changing.
    """

    def check(self, locator: Locator) -> None:
        """
        A method that checks a checkbox.

        :param locator: The locator for the checkbox.
        """

        ...

    def click(self, locator: Locator, *, force: bool = False) -> None:
        """
        A method that clicks an element.

        :param locator: The locator for the element to click.
        :param force: Whether to click without waiting for the element to be actionable.
        """

        ...

    def fill(self, locator: Locator, value: str) -> None:
        """
        A method that puts text into a field.

        :param locator: The locator for the field.
        :param value: The text to put into the field.
        """

        ...

    def hover(self, locator: Locator) -> None:
        """
        A method that hovers over an element.

        :param locator: The locator for the element to hover over.
        """

        ...

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

        ...

    def narrate(
        self,
        title: str,
        *,
        body: str = '',
        step: str = '',
        ms: int | None = None,
    ) -> None:
        """
        A method that shows a caption over the page.

        :param title: The heading for the caption.
        :param body: The paragraph below the heading.
        :param step: The label naming where the demo is in its script.
        :param ms: The time the caption is held on screen, or None for the default.
        """

        ...

    def pause(self, ms: int | None = None) -> None:
        """
        A method that holds the demo without showing anything.

        :param ms: The time to hold for, or None for the default.
        """

        ...

    def press(self, locator: Locator, key: str) -> None:
        """
        A method that presses a key on an element.

        :param locator: The locator for the element the key is pressed on.
        :param key: The key to press.
        """

        ...

    def screenshot(self, name: str) -> Path | None:
        """
        A method that captures the page.

        :param name: The label for the shot.
        :return: The path the screenshot was written to, or None if the run takes no shots.
        """

        ...

    def select(self, locator: Locator, option_label: str) -> None:
        """
        A method that picks an option from a select element by its label.

        :param locator: The locator for the select element.
        :param option_label: The visible text of the option to pick.
        """

        ...

    def slide(self, *, track: Locator, thumb: Locator) -> None:
        """
        A method that drags a slider handle to the end of its track.

        :param track: The locator for the slider track.
        :param thumb: The locator for the slider handle.
        """

        ...

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

        ...

    def switch_page(self, page: Page) -> None:
        """
        A method that points the narrator at a different page.

        :param page: The page later actions are performed on.
        """

        ...

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

        ...

    def uncheck(self, locator: Locator) -> None:
        """
        A method that clears a checkbox.

        :param locator: The locator for the checkbox.
        """

        ...

    def wait(self, ms: int) -> None:
        """
        A method that holds the demo for a duration.

        :param ms: The time to hold for.
        """

        ...


class Silent:
    """
    A narrator that performs the actions and draws nothing.

    This class is the narrator for a run with no overlay, so each narration method
    is a no-op and each action goes straight to Playwright.
    """

    def __init__(self, page: Page) -> None:
        """
        The constructor for the Silent class.

        :param page: The page the actions are performed on.
        """

        self._page = page

    def check(self, locator: Locator) -> None:
        """
        A method that checks a checkbox.

        :param locator: The locator for the checkbox.
        """

        locator.check()

    def click(self, locator: Locator, *, force: bool = False) -> None:
        """
        A method that clicks an element.

        :param locator: The locator for the element to click.
        :param force: Whether to click without waiting for the element to be actionable.
        """

        locator.click(force=force)

    def fill(self, locator: Locator, value: str) -> None:
        """
        A method that puts text into a field.

        :param locator: The locator for the field.
        :param value: The text to put into the field.
        """

        locator.fill(value)

    def hover(self, locator: Locator) -> None:
        """
        A method that hovers over an element.

        :param locator: The locator for the element to hover over.
        """

        locator.hover()

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
        A method that shows no table, because a silent run draws nothing.

        :param title: The heading for the table.
        :param rows: The rendered comparison of each metric.
        :param kicker: The line above the heading.
        :param subtitle: The line below the heading.
        :param ms: The time the table would be held on screen.
        """

    def narrate(
        self,
        title: str,
        *,
        body: str = '',
        step: str = '',
        ms: int | None = None,
    ) -> None:
        """
        A method that shows no caption, because a silent run draws nothing.

        :param title: The heading for the caption.
        :param body: The paragraph below the heading.
        :param step: The label naming where the demo is in its script.
        :param ms: The time the caption would be held on screen.
        """

    def pause(self, ms: int | None = None) -> None:
        """
        A method that holds for nothing, because a silent run has no pacing.

        :param ms: The time the pause would hold for.
        """

    def press(self, locator: Locator, key: str) -> None:
        """
        A method that presses a key on an element.

        :param locator: The locator for the element the key is pressed on.
        :param key: The key to press.
        """

        locator.press(key)

    def screenshot(self, name: str) -> Path | None:
        """
        A method that takes no screenshot, because a silent run captures nothing.

        :param name: The label the shot would carry.
        :return: None.
        """

        return None

    def select(self, locator: Locator, option_label: str) -> None:
        """
        A method that picks an option from a select element by its label.

        :param locator: The locator for the select element.
        :param option_label: The visible text of the option to pick.
        """

        locator.select_option(label=option_label)

    def slide(self, *, track: Locator, thumb: Locator) -> None:
        """
        A method that drags a slider handle to the end of its track.

        :param track: The locator for the slider track.
        :param thumb: The locator for the slider handle.
        """

        slide_to_end(self._page, track=track, thumb=thumb)

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
        A method that highlights nothing, because a silent run draws nothing.

        :param locator: The locator for the element that would be highlighted.
        :param label: The caption that would be shown beside the element.
        :param dim: Whether the rest of the page would be dimmed.
        :param scroll: Whether the element would be scrolled into view.
        :param ms: The time the highlight would be held.
        """

    def switch_page(self, page: Page) -> None:
        """
        A method that points the narrator at a different page.

        :param page: The page later actions are performed on.
        """

        self._page = page

    def title(
        self,
        text: str,
        *,
        kicker: str = '',
        subtitle: str = '',
        ms: int | None = None,
    ) -> None:
        """
        A method that shows no title card, because a silent run draws nothing.

        :param text: The heading for the card.
        :param kicker: The line above the heading.
        :param subtitle: The line below the heading.
        :param ms: The time the card would be held on screen.
        """

    def uncheck(self, locator: Locator) -> None:
        """
        A method that clears a checkbox.

        :param locator: The locator for the checkbox.
        """

        locator.uncheck()

    def wait(self, ms: int) -> None:
        """
        A method that holds the demo for a duration.

        :param ms: The time to hold for.
        """

        self._page.wait_for_timeout(ms)
