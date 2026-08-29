from __future__ import annotations

import json

import pytest

from typing import TYPE_CHECKING

from limelight.transcript import (
    EventName,
    Transcript,
    event_offset_ms,
    transcript_load,
    transcript_path_resolve,
)

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

    transcript.record(EventName.NARRATE, detail)

    assert transcript.events == [{'event': 'narrate', 'offset_ms': 1250, 'title': 'Welcome'}]


def test_record_writes_file_each_time(tmp_path: Path) -> None:
    path = tmp_path / 'demo' / 'transcript.json'
    transcript = Transcript(path)

    detail: dict[str, object] = {}

    transcript.record(EventName.NARRATE, detail)

    payload = json.loads(path.read_text(encoding='utf-8'))

    assert len(payload['events']) == 1


def test_record_rejects_reserved_keys(tmp_path: Path) -> None:
    transcript = Transcript(tmp_path / 'transcript.json')

    detail: dict[str, object] = {'offset_ms': 1}

    with pytest.raises(ValueError, match='reserved'):
        transcript.record(EventName.NARRATE, detail)


def test_events_returns_a_copy(tmp_path: Path) -> None:
    transcript = Transcript(tmp_path / 'transcript.json')

    detail = {'title': 'Welcome'}

    transcript.record(EventName.NARRATE, detail)

    events = transcript.events
    events.clear()

    assert len(transcript.events) == 1


def test_load_returns_the_recorded_events(tmp_path: Path) -> None:
    path = tmp_path / 'transcript.json'
    transcript = Transcript(path)

    detail = {'title': 'Welcome'}

    transcript.record(EventName.NARRATE, detail)

    assert transcript_load(path) == transcript.events


def test_load_rejects_missing_events(tmp_path: Path) -> None:
    path = tmp_path / 'transcript.json'
    path.write_text('{"nope": 1}', encoding='utf-8')

    with pytest.raises(TypeError, match='no events'):
        transcript_load(path)


def test_load_rejects_non_object(tmp_path: Path) -> None:
    path = tmp_path / 'transcript.json'
    path.write_text('[]', encoding='utf-8')

    with pytest.raises(TypeError, match='JSON object'):
        transcript_load(path)


def test_path_resolve_enters_a_directory(tmp_path: Path) -> None:
    assert transcript_path_resolve(tmp_path) == tmp_path / 'transcript.json'
    assert transcript_path_resolve(tmp_path / 'other.json') == tmp_path / 'other.json'


def test_an_event_without_an_offset_reads_as_zero() -> None:
    assert event_offset_ms({'event': 'narrate'}) == 0
    assert event_offset_ms({'event': 'narrate', 'offset_ms': 'soon'}) == 0
