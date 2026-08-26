from __future__ import annotations

import json
import time

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from pathlib import Path


EVENT_KEYS_RESERVED = frozenset(('event', 'offset_ms'))


class Transcript:
    def __init__(
        self,
        path: Path,
        *,
        clock: Callable[[], float] = time.monotonic,
        wall_clock: Callable[[], float] = time.time,
    ) -> None:
        self._clock = clock
        self._events: list[dict[str, object]] = []
        self._path = path
        self._started_at = clock()
        self._started_at_epoch_ms = int(wall_clock() * 1000)

    def _write(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            'events': self._events,
            'started_at_epoch_ms': self._started_at_epoch_ms,
        }

        self._path.write_text(json.dumps(payload, indent=2), encoding='utf-8')

    @property
    def events(self) -> list[dict[str, object]]:
        return list(self._events)

    def record(self, event: str, detail: Mapping[str, object]) -> None:
        if not event:
            message = 'event must not be empty'
            raise ValueError(message)

        keys_reserved = EVENT_KEYS_RESERVED & set(detail)

        if keys_reserved:
            keys = ', '.join(sorted(keys_reserved))

            message = f'detail must not use reserved keys: {keys}'
            raise ValueError(message)

        offset_ms = int((self._clock() - self._started_at) * 1000)

        entry: dict[str, object] = {'event': event, 'offset_ms': offset_ms, **detail}

        self._events.append(entry)
        self._write()

    @property
    def started_at_epoch_ms(self) -> int:
        return self._started_at_epoch_ms
