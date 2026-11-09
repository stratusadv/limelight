from __future__ import annotations

from typing import TYPE_CHECKING

from limelight.artifacts import SUBTITLES_FILE_NAME
from limelight.transcript import EventName, event_offset_ms, event_text
from limelight.export.export import TextExport

if TYPE_CHECKING:
    from limelight.transcript import Event


CUE_EVENTS = (EventName.NARRATE, EventName.TITLE)
CUE_MS_FALLBACK = 4500


def _cue_end_ms(events: list[Event], *, index: int, start_ms: int) -> int:
    """
    A function that finds when a cue gives way to the next event.

    The search skips any event sharing the start offset, because two events
    recorded in the same millisecond would otherwise produce a cue of zero length
    that no player displays.

    :param events: The recorded events of the run.
    :param index: The position of the cue event.
    :param start_ms: The offset the cue begins at.
    :return: The offset the cue ends at.
    :raises RuntimeError: If the cue would end before it begins.
    """

    end_ms = start_ms + CUE_MS_FALLBACK

    for event_next in events[index + 1 :]:
        offset_ms = event_offset_ms(event_next)

        if offset_ms > start_ms:
            end_ms = offset_ms

            break

    if end_ms <= start_ms:
        message = f'the cue at {start_ms}ms would end at {end_ms}ms'
        raise RuntimeError(message)

    return end_ms


def _cue_text(event: Event) -> str:
    """
    A function that renders the text of one cue.

    :param event: The event the cue is built from.
    :return: The title, with the body on a second line where there is one.
    """

    title = _vtt_text(event_text(event, 'title'))
    body = _vtt_text(event_text(event, 'body'))

    if body:
        return f'{title}\n{body}'

    return title


def _timestamp(offset_ms: int) -> str:
    """
    A function that formats an offset as a WebVTT timestamp.

    :param offset_ms: The milliseconds since the run started.
    :return: The offset as hours, minutes, seconds, and milliseconds.
    """

    seconds_total, milliseconds = divmod(offset_ms, 1000)
    minutes_total, seconds = divmod(seconds_total, 60)
    hours, minutes = divmod(minutes_total, 60)

    return f'{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}'


def _vtt_text(value: str) -> str:
    """
    A function that escapes the characters WebVTT reads as markup.

    :param value: The text to escape.
    :return: The text with its ampersands and angle brackets escaped.
    """

    return value.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def subtitles_export() -> TextExport:
    """
    A function that builds the export for the subtitle track.

    :return: The export that writes the WebVTT file.
    """

    return TextExport(SUBTITLES_FILE_NAME, vtt_render)


def vtt_render(events: list[Event]) -> str:
    """
    A function that renders the narration events as a WebVTT track.

    :param events: The recorded events of the run.
    :return: The subtitle track.
    """

    lines = ['WEBVTT']

    for index, event in enumerate(events):
        if event.get('event') not in CUE_EVENTS:
            continue

        start_ms = event_offset_ms(event)
        end_ms = _cue_end_ms(events, index=index, start_ms=start_ms)

        lines += [
            '',
            f'{_timestamp(start_ms)} --> {_timestamp(end_ms)}',
            _cue_text(event),
        ]

    return '\n'.join(lines) + '\n'
