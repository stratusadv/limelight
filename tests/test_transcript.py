from __future__ import annotations

import json

import pytest

from typing_extensions import TYPE_CHECKING

from limelight.transcript import Transcript

if TYPE_CHECKING:
    from pathlib import Path


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def test_record_appends_event_with_offset(tmp_path: Path) -> None:
    clock = FakeClock()
    transcript = Transcript(tmp_path / 'transcript.json', clock=clock)

    clock.now = 101.25

    detail = {'title': 'Welcome'}

    transcript.record('narrate', detail)

    assert transcript.events == [{'event': 'narrate', 'offset_ms': 1250, 'title': 'Welcome'}]


def test_record_writes_file_each_time(tmp_path: Path) -> None:
    path = tmp_path / 'demo' / 'transcript.json'
    transcript = Transcript(path)

    detail: dict[str, object] = {}

    transcript.record('narrate', detail)

    payload = json.loads(path.read_text(encoding='utf-8'))

    assert len(payload['events']) == 1


def test_record_rejects_empty_event(tmp_path: Path) -> None:
    transcript = Transcript(tmp_path / 'transcript.json')

    detail: dict[str, object] = {}

    with pytest.raises(ValueError, match='event'):
        transcript.record('', detail)


def test_record_rejects_reserved_keys(tmp_path: Path) -> None:
    transcript = Transcript(tmp_path / 'transcript.json')

    detail: dict[str, object] = {'offset_ms': 1}

    with pytest.raises(ValueError, match='reserved'):
        transcript.record('narrate', detail)


def test_payload_carries_wall_clock_epoch(tmp_path: Path) -> None:
    path = tmp_path / 'transcript.json'
    transcript = Transcript(path, wall_clock=lambda: 12.345)

    detail: dict[str, object] = {}

    transcript.record('narrate', detail)

    payload = json.loads(path.read_text(encoding='utf-8'))

    assert payload['started_at_epoch_ms'] == 12345
    assert transcript.started_at_epoch_ms == 12345


def test_events_returns_a_copy(tmp_path: Path) -> None:
    transcript = Transcript(tmp_path / 'transcript.json')

    detail = {'title': 'Welcome'}

    transcript.record('narrate', detail)

    events = transcript.events
    events.clear()

    assert len(transcript.events) == 1
