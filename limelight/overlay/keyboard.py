from __future__ import annotations

import contextlib

from typing import TYPE_CHECKING

from playwright.sync_api import Error as PlaywrightError

from limelight.javascript import script

if TYPE_CHECKING:
    from playwright.sync_api import Locator

    from limelight.overlay.bridge import Bridge
    from limelight.overlay.playback import Playback


CHARACTER_MS = 55
DRIVE_SLACK_MS = 5000
INPUT_TYPES_UNTYPEABLE = ('color', 'date', 'datetime-local', 'month', 'range', 'time', 'week')
INPUT_TYPE_MASKED = 'password'
INPUT_TYPE_SCRIPT = script('input_type.js')
INPUT_TYPE_TIMEOUT_MS = 2000
KEYS_UNMASKED = ('Enter', 'Tab')
VALUE_MASK = '********'


def _input_type_of(locator: Locator) -> str | None:
    """
    A function that reads the type of the input a locator points at.

    :param locator: The locator for the field.
    :return: The lowercase input type, an empty string for an element that is not an
        input, or None if the type could not be read.
    """

    input_type = None

    with contextlib.suppress(PlaywrightError):
        input_type_raw = locator.evaluate(INPUT_TYPE_SCRIPT, timeout=INPUT_TYPE_TIMEOUT_MS)
        input_type = str(input_type_raw or '')

    return input_type


def _is_masked(locator: Locator) -> bool:
    """
    A function that reports whether a field's value is kept off the key display and the transcript.

    A field whose type cannot be read counts as masked, so a failed read never puts
    a password on screen or on disk.

    :param locator: The locator for the field.
    :return: True if the field is a password input or its type could not be read, False otherwise.
    """

    input_type = _input_type_of(locator)

    if input_type is None:
        return True

    return input_type == INPUT_TYPE_MASKED


class Keyboard:
    """
    A typist that drives keyboard input and the on-screen key display.

    This class wraps each keystroke in a drive window, so the overlay knows the
    input it sees came from the demo rather than from a viewer at the keyboard.
    """

    def __init__(self, bridge: Bridge, playback: Playback) -> None:
        """
        The constructor for the Keyboard class.

        :param bridge: The bridge into the overlay running on the page.
        :param playback: The playback clock the typing is paced against.
        """

        self._bridge = bridge
        self._playback = playback

    def _drive_begin(self, duration_ms: float) -> None:
        """
        A method that opens the window in which input is treated as driven.

        The window is given slack beyond the expected duration because a keystroke can
        land late under load, and input arriving after the window closes is read as a
        viewer typing.

        :param duration_ms: The expected duration of the input.
        """

        argument = {'ms': duration_ms + DRIVE_SLACK_MS}

        self._bridge.call('inputDriveBegin', argument)

    def _drive_end(self) -> None:
        """A method that closes the driven input window."""

        self._bridge.call('inputDriveEnd')

    def _typed_by_frame(self, locator: Locator, value: str, delay_ms: float) -> None:
        """
        A method that types one character per playback tick.

        The delay is taken by the playback clock rather than by Playwright, because a
        frame-paced run advances its own timeline and a Playwright delay would sleep
        against the wall clock instead.

        :param locator: The locator for the field being typed into.
        :param value: The text to type.
        :param delay_ms: The time held between characters.
        """

        for character in value:
            locator.press_sequentially(character)
            self._playback.sleep(delay_ms)

    def press(self, locator: Locator, key: str) -> None:
        """
        A method that presses one key and flashes it on the overlay.

        :param locator: The locator for the element the key is pressed on.
        :param key: The key to press.
        """

        argument = {'text': key_masked(locator, key)}
        self._bridge.call('keyFlash', argument)
        self._drive_begin(0)

        locator.press(key)

        self._drive_end()

    def type(self, locator: Locator, value: str) -> None:
        """
        A method that types text into a field, character by character.

        :param locator: The locator for the field being typed into.
        :param value: The text to type.
        """

        delay_ms = CHARACTER_MS / self._playback.speed_factor_live

        self._drive_begin(len(value) * delay_ms)

        if not _is_masked(locator):
            self._bridge.call('keyHudEnable')

        locator.fill('')

        if self._playback.frame_paced:
            self._typed_by_frame(locator, value, delay_ms)
        else:
            locator.press_sequentially(value, delay=delay_ms)

        self._bridge.call('keyHudDisable')
        self._drive_end()

    @staticmethod
    def types_faithfully(locator: Locator) -> bool:
        """
        A method that reports whether a field shows the characters typed into it.

        A date, color, or range input renders its own control and turns keystrokes into
        a value of its own, so typing into one produces neither the text nor the timing
        a viewer would recognize.

        :param locator: The locator for the field.
        :return: True if the field can be typed into character by character, False otherwise.
        """

        return _input_type_of(locator) not in INPUT_TYPES_UNTYPEABLE


def key_masked(locator: Locator, key: str) -> str:
    """
    A function that masks a key pressed into a masked field.

    The Enter and Tab keys stay readable, because they move between fields or submit
    the form and carry no part of the value.

    :param locator: The locator for the element the key is pressed on.
    :param key: The key to press.
    :return: The key, or the mask if the element is a masked field.
    """

    if key in KEYS_UNMASKED:
        return key

    return value_masked(locator, key)


def value_masked(locator: Locator, value: str) -> str:
    """
    A function that masks a value typed into a masked field.

    :param locator: The locator for the field being typed into.
    :param value: The text to type.
    :return: The value, or the mask if the field is masked.
    """

    if _is_masked(locator):
        return VALUE_MASK

    return value
