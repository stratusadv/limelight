from __future__ import annotations

import json

import pytest

from typing import TYPE_CHECKING

from limelight.export import (
    chapters_render,
    main,
    markdown_render,
    transcript_events_load,
    transcript_payload_load,
    vtt_render,
)

if TYPE_CHECKING:
    from pathlib import Path


def events_sample() -> list[dict[str, object]]:
    delta_rows = [
        {
            'label': 'Orders',
            'before': '3',
            'after': '5',
            'delta': '+2',
            'direction': 'up',
            'sentiment': 'good',
        },
    ]

    return [
        {
            'event': 'title_card',
            'offset_ms': 0,
            'title': 'Order Approval',
            'kicker': 'Chapter One',
            'subtitle': 'Draft to approved.',
        },
        {
            'event': 'narrate',
            'offset_ms': 2000,
            'title': 'Open the order',
            'body': 'Navigate to it.',
            'step': 'Navigate',
            'tag': '',
            'kind': '',
        },
        {
            'event': 'spotlight',
            'offset_ms': 4000,
            'label': 'Click "Orders"',
        },
        {
            'event': 'shot',
            'offset_ms': 5000,
            'name': 'orders',
            'file': '01-orders.png',
        },
        {
            'event': 'delta_card',
            'offset_ms': 6000,
            'title': 'Totals',
            'kicker': '',
            'subtitle': '',
            'rows': delta_rows,
        },
    ]


def test_markdown_renders_walkthrough() -> None:
    content = markdown_render(events_sample(), title='Demo')

    assert '# Demo' in content
    assert '# Order Approval' in content
    assert '*Chapter One*' in content
    assert '## Open the order' in content
    assert 'Navigate to it.' in content
    assert '- Click "Orders"' in content
    assert '![orders](01-orders.png)' in content
    assert '| Orders | 3 | 5 | +2 |' in content


def test_markdown_renders_action_bullets() -> None:
    events: list[dict[str, object]] = [
        {'event': 'click', 'offset_ms': 0, 'target': 'Approve'},
        {'event': 'fill', 'offset_ms': 1, 'target': 'Order number', 'value': 'SO-100'},
        {'event': 'fill', 'offset_ms': 2, 'target': '', 'value': 'note'},
        {'event': 'select', 'offset_ms': 3, 'target': '', 'option': 'Approved'},
        {'event': 'press', 'offset_ms': 4, 'target': '', 'key': 'Enter'},
        {'event': 'check', 'offset_ms': 5, 'target': 'Urgent'},
        {'event': 'hover', 'offset_ms': 6, 'target': 'Totals'},
        {'event': 'slide', 'offset_ms': 7, 'target': ''},
        {'event': 'uncheck', 'offset_ms': 8, 'target': 'Urgent'},
    ]

    content = markdown_render(events)

    assert '- Click "Approve"' in content
    assert '- Fill "Order number" with "SO-100"' in content
    assert '- Type "note"' in content
    assert '- Select "Approved"' in content
    assert '- Press Enter' in content
    assert '- Check "Urgent"' in content
    assert '- Hover over "Totals"' in content
    assert '- Slide to confirm' in content
    assert '- Uncheck "Urgent"' in content


def test_markdown_skips_actions_without_targets() -> None:
    events: list[dict[str, object]] = [
        {'event': 'click', 'offset_ms': 0, 'target': ''},
    ]

    assert markdown_render(events) == '\n'


def test_markdown_skips_unknown_events() -> None:
    events: list[dict[str, object]] = [
        {'event': 'mystery', 'offset_ms': 0},
    ]

    assert markdown_render(events) == '\n'


def test_vtt_renders_cues_with_next_event_ends() -> None:
    content = vtt_render(events_sample())

    assert content.startswith('WEBVTT\n')
    assert '00:00:00.000 --> 00:00:02.000\nOrder Approval' in content
    assert '00:00:02.000 --> 00:00:04.000\nOpen the order\nNavigate to it.' in content


def test_vtt_escapes_markup_in_cue_text() -> None:
    events: list[dict[str, object]] = [
        {'event': 'narrate', 'offset_ms': 0, 'title': 'Enter <order> & save'},
    ]

    content = vtt_render(events)

    assert 'Enter &lt;order&gt; &amp; save' in content


def test_vtt_last_cue_gets_fallback_duration() -> None:
    events: list[dict[str, object]] = [
        {'event': 'narrate', 'offset_ms': 1000, 'title': 'Only'},
    ]

    content = vtt_render(events)

    assert '00:00:01.000 --> 00:00:05.500\nOnly' in content


def test_chapters_lists_title_cards() -> None:
    assert chapters_render(events_sample()) == '00:00 Order Approval\n'


def test_chapters_empty_without_title_cards() -> None:
    assert chapters_render([]) == ''


def test_load_rejects_missing_events(tmp_path: Path) -> None:
    path = tmp_path / 'transcript.json'
    path.write_text('{}', encoding='utf-8')

    with pytest.raises(TypeError, match='events'):
        transcript_events_load(path)


def test_payload_load_returns_the_whole_object(tmp_path: Path) -> None:
    path = tmp_path / 'transcript.json'
    path.write_text('{"events": [], "started_at_epoch_ms": 123}', encoding='utf-8')

    payload = transcript_payload_load(path)

    assert payload['started_at_epoch_ms'] == 123


def test_payload_load_rejects_non_object(tmp_path: Path) -> None:
    path = tmp_path / 'transcript.json'
    path.write_text('[]', encoding='utf-8')

    with pytest.raises(TypeError, match='JSON object'):
        transcript_payload_load(path)


def test_main_writes_exports_beside_transcript(tmp_path: Path) -> None:
    directory = tmp_path / 'demo'
    directory.mkdir()

    payload = {'events': events_sample()}
    transcript_path = directory / 'transcript.json'

    transcript_path.write_text(json.dumps(payload), encoding='utf-8')

    arguments = [str(directory)]
    exit_code = main(arguments)

    assert exit_code == 0
    assert (directory / 'chapters.txt').is_file()
    assert (directory / 'subtitles.vtt').is_file()
    assert (directory / 'walkthrough.md').is_file()
