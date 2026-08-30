from __future__ import annotations

from typing import TYPE_CHECKING

from playwright.sync_api import expect

from limelight.components.modal import ELEMENT_WAIT_TIMEOUT_MS

if TYPE_CHECKING:
    from playwright.sync_api import Locator

    from limelight.demo import Demo


class Confirm:
    """
    A driver for the inline prompt that stands between an action and its effect.

    This class finds the button that carries the action through and clicks it,
    waiting for it before saying anything about it. Only visible buttons are
    considered, because a page that renders one prompt per row keeps every
    unopened prompt in the markup.

    The click is left unbarriered on purpose. A prompt sits in front of anything
    from a form post to a background write, so the caller wraps the accept in the
    barrier that proves its own effect landed.

    ::

        trigger_until_response(
            page,
            lambda: Confirm(demo).accept('Delete'),
            method=HTTPMethod.POST,
        )
    """

    button_selector = 'button'

    def __init__(self, demo: Demo, root: Locator | None = None) -> None:
        """
        The constructor for the Confirm class.

        :param demo: The demo driving the browser.
        :param root: The region holding the prompt, or None for the whole page.
        """

        self.demo = demo
        self.root = root

    def accept(self, text: str = '', *, label: str = '') -> None:
        """
        A method that carries the action through.

        :param text: The text on the button, or an empty string for the only one.
        :param label: The spotlight caption, defaulting to the button text.
        :raises AssertionError: If the button never appears.
        """

        button = self.button(text)

        expect(button).to_be_visible(timeout=ELEMENT_WAIT_TIMEOUT_MS)

        caption = label or text

        if caption:
            self.demo.spotlight(button, label=caption)

        self.demo.click(button)

    def button(self, text: str = '') -> Locator:
        """
        A method that gets the button that carries the action through.

        :param text: The text on the button, or an empty string for the only one.
        :return: The locator for the button.
        """

        scope = self.root if self.root is not None else self.demo.page
        buttons = scope.locator(self.button_selector).filter(visible=True)

        if text:
            buttons = buttons.filter(has_text=text)

        return buttons.first
