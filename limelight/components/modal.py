from __future__ import annotations

import re

from typing import TYPE_CHECKING

from playwright.sync_api import expect

from limelight.barriers import trigger_until_visible

if TYPE_CHECKING:
    from playwright._impl._api_structures import AriaRole
    from playwright.sync_api import Locator

    from limelight.demo import Demo


ELEMENT_WAIT_TIMEOUT_MS = 30_000

FIELD_FILL_ATTEMPT_COUNT_MAX = 4
FIELD_SETTLE_WAIT_MS = 400

FORM_INVALID_SCRIPT = """
    form => [...form.elements]
        .filter(element => !element.checkValidity())
        .map(element => (element.name || element.id) + ' (' + element.validationMessage + ')')
        .join(', ')
"""

OPEN_SETTLE_WAIT_MS = 1500


class Modal:
    """
    A narrated driver for a modal dialog.

    This class opens a modal from the control that dispatches it, fills its
    fields by the labels a viewer can read, and submits it, narrating and
    spotlighting each step so the recording explains itself. Every wait is
    bounded, and a form the browser refuses is reported by name rather than
    left as a click that did nothing.

    The defaults describe plain HTML: a dialog found by its ARIA role, fields
    found through their labels, and openers that are links or buttons. A project
    whose markup differs subclasses this and overrides the selectors it needs,
    which is also how a modal that teleports its content into a fixed pane is
    reached.

    ::

        class DispatchModal(Modal):
            content_selector = '#dispatch-modal-content'
            opener_selector = 'a.btn'
    """

    content_role: AriaRole = 'dialog'
    content_selector = ''
    field_selector = 'input, select, textarea'
    form_selector = 'form'
    group_selector = 'xpath=..'
    label_selector = 'label'
    opener_selector = 'a, button'
    scope_selector = '.card'

    def __init__(self, demo: Demo) -> None:
        """
        The constructor for the Modal class.

        :param demo: The demo driving the browser.
        """

        self.demo = demo

    def _invalid_report(self) -> str:
        """
        A method that names the controls the browser refuses to submit.

        :return: The invalid controls and their messages, or an empty string.
        """

        return self.content.locator(self.form_selector).first.evaluate(FORM_INVALID_SCRIPT)

    def _opener(self, button: str, *, within: str) -> Locator:
        """
        A method that locates the control dispatching the modal.

        :param button: The text on the control.
        :param within: The region to scope the control to, or an empty string to
            search the whole page.
        :return: The locator for the control.
        """

        root = self.demo.page

        if within:
            opener = self.demo.page.locator(self.opener_selector).filter(has_text=button)

            root = (
                self.demo.page.locator(self.scope_selector)
                .filter(has_text=within)
                .filter(has=opener)
                .last
            )

        return root.locator(self.opener_selector).filter(has_text=button).filter(visible=True).first

    def _value_settle(self, field: Locator, value: str) -> None:
        """
        A method that fills a field until the value sticks.

        A field bound to a debounced client-side model can drop the first write,
        so the value is re-entered until the element reads back what was asked
        for.

        :param field: The locator for the field being filled.
        :param value: The value the field must hold.
        :raises AssertionError: If the field never holds the value.
        """

        for attempt in range(FIELD_FILL_ATTEMPT_COUNT_MAX):
            if attempt == 0:
                self.demo.fill(field, value)
            else:
                field.fill(value)

            if attempt == FIELD_FILL_ATTEMPT_COUNT_MAX - 1:
                break

            field.page.wait_for_timeout(FIELD_SETTLE_WAIT_MS)

            if field.input_value() == value:
                return

        expect(field).to_have_value(value, timeout=ELEMENT_WAIT_TIMEOUT_MS)

    @property
    def content(self) -> Locator:
        """
        A property that gets the open modal's content pane.

        The pane is found by its dialog role unless a selector names it, because a
        modal that teleports itself to the end of the body is not inside the markup
        that opened it.

        :return: The locator for the modal content.
        """

        if self.content_selector:
            return self.demo.page.locator(self.content_selector)

        return self.demo.page.get_by_role(self.content_role)

    @property
    def form(self) -> Locator:
        """
        A property that gets the visible form inside the open modal.

        :return: The locator for the modal form.
        """

        return self.content.locator(self.form_selector).filter(visible=True).first

    def choose(self, option_text: str, *, label: str = '') -> None:
        """
        A method that picks one option out of the open modal.

        :param option_text: The exact text of the option to pick.
        :param label: The spotlight caption, or an empty string to highlight nothing.
        :raises AssertionError: If the option never appears.
        """

        option = self.option(option_text)

        expect(option).to_be_visible(timeout=ELEMENT_WAIT_TIMEOUT_MS)

        if label:
            self.demo.spotlight(option, label=label)

        self.demo.click(option)

    def field(self, label: str) -> Locator:
        """
        A method that gets the field a label names.

        :param label: The label text shown above the field.
        :return: The locator for the input, select, or textarea.
        """

        return self.group(label).locator(self.field_selector).first

    def fill(self, label: str, value: str, *, headline: str = '', body: str = '') -> None:
        """
        A method that narrates and fills one field of the open modal.

        :param label: The label text shown above the field.
        :param value: The value the field must hold.
        :param headline: The narration headline, or an empty string to stay silent.
        :param body: The narration body shown under the headline.
        :raises AssertionError: If the field never appears or never holds the value.
        """

        expect(self.group(label)).to_be_visible(timeout=ELEMENT_WAIT_TIMEOUT_MS)

        field = self.field(label)

        expect(field).to_be_visible(timeout=ELEMENT_WAIT_TIMEOUT_MS)

        if headline:
            self.demo.narrate(headline, step='Entering details', body=body)

        self.demo.spotlight(field, label=label)

        self._value_settle(field, value)
        self.demo.pause()

    def group(self, label: str) -> Locator:
        """
        A method that gets the field group a label names.

        The lookup runs through the visible label rather than the form field
        name, because a demo spotlights what the viewer is reading.

        :param label: The label text shown above the field.
        :return: The locator for the group holding the label and its field.
        """

        pattern = re.compile(rf'^\s*{re.escape(label)}\s*\*?\s*$')

        return (
            self.content.locator(self.label_selector)
            .filter(has_text=pattern)
            .locator(self.group_selector)
            .first
        )

    def open(
        self,
        button: str | Locator,
        *,
        headline: str,
        body: str,
        step: str = 'Create',
        within: str = '',
        label: str = '',
    ) -> None:
        """
        A method that narrates a click and waits for the modal it opens.

        The control is named by its text, or handed over as a locator when the
        page holds no text that identifies it, such as an icon button on a row.

        :param button: The text on the control that dispatches the modal, or the
            locator for the control itself.
        :param headline: The narration headline.
        :param body: The narration body shown under the headline.
        :param step: The step label the narration carries.
        :param within: The region to scope the control to, when the page holds
            more than one control of that name.
        :param label: The spotlight caption, defaulting to the control text.
        :raises AssertionError: If the control or the modal form never appears.
        :raises ValueError: If a region is named for a control given as a locator.
        """

        is_named = isinstance(button, str)

        if within and not is_named:
            message = 'within scopes a control by its text, so it needs a control name'
            raise ValueError(message)

        opener = self._opener(button, within=within) if is_named else button
        caption = label or (f'Click "{button}"' if is_named else '')

        expect(opener).to_be_visible(timeout=ELEMENT_WAIT_TIMEOUT_MS)

        self.demo.narrate(headline, step=step, body=body)

        self.demo.spotlight(opener, label=caption)

        self.demo.page.wait_for_load_state('networkidle')

        self.demo.click(opener)

        expect(self.form).to_be_visible(timeout=ELEMENT_WAIT_TIMEOUT_MS)

        self.demo.page.wait_for_timeout(OPEN_SETTLE_WAIT_MS)
        self.demo.pause()

    def open_with(self, trigger: Locator, *, reveals_text: str) -> None:
        """
        A method that clicks a trigger until the modal it opens is showing.

        A trigger bound to a client-side handler can be clicked before the handler
        is listening, which opens nothing, so the click repeats until the option it
        reveals is on the page.

        :param trigger: The locator for the element that opens the modal.
        :param reveals_text: The exact text of an option the open modal shows.
        :raises AssertionError: If the modal never opens.
        """

        trigger_until_visible(trigger.click, self.option(reveals_text))

    def option(self, text: str) -> Locator:
        """
        A method that gets the option a text names.

        :param text: The exact text of the option.
        :return: The locator for the option.
        """

        return self.content.get_by_text(text, exact=True)

    def submit(self, button: str = 'Submit', *, shot: str = '') -> None:
        """
        A method that submits the open modal and waits for it to close.

        The form is checked before the click, because a browser refusing an
        invalid control leaves the modal open with nothing to read in the trace.

        :param button: The text on the submit button.
        :param shot: The screenshot name to capture before submitting, or an
            empty string to capture nothing.
        :raises AssertionError: If a control is invalid, or the modal never closes.
        """

        invalid = self._invalid_report()

        if invalid:
            message = f'The modal form cannot submit while these controls are invalid: {invalid}'
            raise AssertionError(message)

        submitter = self.content.get_by_role('button', name=button).first

        expect(submitter).to_be_enabled(timeout=ELEMENT_WAIT_TIMEOUT_MS)

        self.demo.spotlight(submitter, label=f'Click "{button}"')

        if shot:
            self.demo.screenshot(shot)

        form = self.form

        self.demo.click(submitter)

        expect(form).to_be_hidden(timeout=ELEMENT_WAIT_TIMEOUT_MS)

        self.demo.page.wait_for_load_state('domcontentloaded')
        self.demo.pause()
