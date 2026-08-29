from __future__ import annotations

import json
import time

from enum import StrEnum
from typing import TYPE_CHECKING

from limelight.artifacts import TRANSCRIPT_FILE_NAME

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from pathlib import Path


    Event = dict[str, object]


class EventName(StrEnum):
    """An enumeration of the actions a demo records."""

    CHECK = 'check'
    CLICK = 'click'
    FILL = 'fill'
    HOVER = 'hover'
    METRICS = 'metrics'
    NARRATE = 'narrate'
    PRESS = 'press'
    SCREENSHOT = 'screenshot'
    SELECT = 'select'
    SLIDE = 'slide'
    SPOTLIGHT = 'spotlight'
    TITLE = 'title'
    UNCHECK = 'uncheck'


EVENT_KEYS_RESERVED = frozenset(('event', 'offset_ms'))


class Transcript:
    """
    A recorder for the events of a demo run and their timing.

    This class stamps each event with the milliseconds elapsed since the run
    started and rewrites the JSON file after every append, so a crashed run still
    leaves the events it got through on disk.
    """

    def __init__(self, path: Path, *, clock: Callable[[], float] = time.monotonic) -> None:
        """
        The constructor for the Transcript class.

        :param path: The file the events are written to.
        :param clock: The monotonic clock the offsets are measured against.
        """

        self._clock = clock
        self._events: list[Event] = []
        self._path = path
        self._started_at = clock()

    def _write(self) -> None:
        """A method that writes the recorded events to disk."""

        self._path.parent.mkdir(parents=True, exist_ok=True)

        payload = {'events': self._events}

        self._path.write_text(json.dumps(payload, indent=2), encoding='utf-8')

    @property
    def events(self) -> list[Event]:
        """
        A property that exposes the recorded events.

        :return: A copy of the events, so a caller cannot append to the recording.
        """

        return list(self._events)

    def record(self, event: EventName, detail: Mapping[str, object]) -> None:
        """
        A method that appends one event to the recording and writes the file.

        :param event: The kind of action being recorded.
        :param detail: The fields describing the action.
        :raises ValueError: If the detail carries a key the transcript reserves.
        """

        keys_reserved = EVENT_KEYS_RESERVED & set(detail)

        if keys_reserved:
            keys = ', '.join(sorted(keys_reserved))

            message = f'detail must not use reserved keys: {keys}'
            raise ValueError(message)

        offset_ms = int((self._clock() - self._started_at) * 1000)

        entry: Event = {'event': event, 'offset_ms': offset_ms, **detail}

        self._events.append(entry)
        self._write()


def event_offset_ms(event: Event) -> int:
    """
    A function that reads the offset out of a recorded event.

    :param event: The event to read.
    :return: The milliseconds since the run started, or 0 if the event carries no offset.
    """

    offset = event.get('offset_ms')

    if isinstance(offset, int):
        return offset

    return 0


def event_text(event: Event, key: str) -> str:
    """
    A function that reads a string field out of a recorded event.

    :param event: The event to read.
    :param key: The name of the field.
    :return: The field value, or an empty string if it is missing or not a string.
    """

    value = event.get(key)

    if isinstance(value, str):
        return value

    return ''


def transcript_load(path: Path) -> list[Event]:
    """
    A function that loads the events from a transcript file.

    :param path: The path to the transcript file.
    :return: The recorded events, with any non-object entry dropped.
    :raises TypeError: If the file holds no JSON object, or carries no event list.
    """

    payload = json.loads(path.read_text(encoding='utf-8'))

    if not isinstance(payload, dict):
        message = f'transcript is not a JSON object: {path}'
        raise TypeError(message)

    events = payload.get('events')

    if not isinstance(events, list):
        message = f'no events found in {path}'
        raise TypeError(message)

    return [event for event in events if isinstance(event, dict)]


def transcript_path_resolve(path: Path) -> Path:
    """
    A function that resolves a path that may name either a transcript or its directory.

    :param path: The path to a transcript file, or to the directory holding one.
    :return: The path to the transcript file.
    """

    if path.is_dir():
        return path / TRANSCRIPT_FILE_NAME

    return path
