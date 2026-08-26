from __future__ import annotations

import re

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from playwright.sync_api import Page


SHOT_NAME_INVALID_PATTERN = re.compile(r'[^A-Za-z0-9._-]+')


class Camera:
    def __init__(self, page: Page, directory: Path, *, enabled: bool) -> None:
        directory_text = str(directory).strip()

        if directory_text in ('', '.'):
            message = f'directory must be a real path (got "{directory}")'
            raise ValueError(message)

        self._directory = directory
        self._enabled = enabled
        self._page = page
        self._sequence = 0

    def shot(self, name: str) -> Path | None:
        if not name:
            return None

        if not self._enabled:
            return None

        name_clean = SHOT_NAME_INVALID_PATTERN.sub('-', name).strip('-.')

        if not name_clean:
            return None

        self._sequence += 1

        path = self._directory / f'{self._sequence:02d}-{name_clean}.png'

        self._directory.mkdir(parents=True, exist_ok=True)
        self._page.screenshot(path=str(path))

        return path

    def use_page(self, page: Page) -> None:
        self._page = page
