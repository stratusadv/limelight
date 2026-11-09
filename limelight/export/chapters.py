from __future__ import annotations

from typing import TYPE_CHECKING

from limelight.artifacts import CHAPTERS_FILE_NAME
from limelight.transcript import EventName, event_offset_ms, event_text
from limelight.export.export import TextExport

if TYPE_CHECKING:
    from limelight.transcript import Event


CHAPTER_EVENTS = (EventName.TITLE,)


def _timestamp_chapter(offset_ms: int) -> str:
    """
    A function that formats an offset as a chapter timestamp.

    :param offset_ms: The milliseconds since the run started.
    :return: The offset as minutes and seconds.
    """

    minutes, seconds = divmod(offset_ms // 1000, 60)

    return f'{minutes:02d}:{seconds:02d}'


def chapters_export() -> TextExport:
    """
    A function that builds the export for the chapter list.

    :return: The export that writes the chapter file.
    """

    return TextExport(CHAPTERS_FILE_NAME, chapters_render)


def chapters_render(events: list[Event]) -> str:
    """
    A function that renders the title events as a chapter list.

    :param events: The recorded events of the run.
    :return: One line per chapter, or an empty string if the run has no titles.
    """

    lines = [
        f'{_timestamp_chapter(event_offset_ms(event))} {event_text(event, "title")}'
        for event in events
        if event.get('event') in CHAPTER_EVENTS
    ]

    if not lines:
        return ''

    return '\n'.join(lines) + '\n'
