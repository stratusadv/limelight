from __future__ import annotations

import re

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from playwright.sync_api import Page


SCREENSHOT_NAME_INVALID_PATTERN = re.compile(r'[^A-Za-z0-9._-]+')


class Camera:
    """
    A screenshot recorder for a demo run.

    This class numbers each screenshot as it is taken, so the files sort in the
    order the demo produced them rather than by name.
    """

    def __init__(self, page: Page, directory: Path) -> None:
        """
        The constructor for the Camera class.

        :param page: The page the screenshots are taken from.
        :param directory: The directory the screenshots are written to.
        :raises ValueError: If the directory is empty or the current directory.
        """

        directory_text = str(directory).strip()

        if directory_text in ('', '.'):
            message = f'directory must be a real path (got "{directory}")'
            raise ValueError(message)

        self._directory = directory
        self._page = page
        self._sequence = 0

    def screenshot(self, name: str) -> Path:
        """
        A method that captures the current page to a numbered PNG file.

        :param name: The label for the shot, with unusable characters replaced by a dash.
        :return: The path the screenshot was written to.
        :raises ValueError: If the name carries no characters usable in a file name.
        """

        name_clean = SCREENSHOT_NAME_INVALID_PATTERN.sub('-', name).strip('-.')

        if not name_clean:
            message = f'screenshot name carries no filename characters: "{name}"'
            raise ValueError(message)

        self._sequence += 1

        path = self._directory / f'{self._sequence:02d}-{name_clean}.png'

        self._directory.mkdir(parents=True, exist_ok=True)
        self._page.screenshot(path=str(path))

        return path

    def switch_page(self, page: Page) -> None:
        """
        A method that points the camera at a different page.

        :param page: The page later screenshots are taken from.
        """

        self._page = page
