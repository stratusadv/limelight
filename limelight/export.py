from __future__ import annotations

import argparse
import json
import sys

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


ACTION_EVENTS = ('check', 'click', 'fill', 'hover', 'press', 'select', 'slide', 'uncheck')
ACTION_VERBS = {
    'check': 'Check',
    'click': 'Click',
    'hover': 'Hover over',
    'uncheck': 'Uncheck',
}
CHAPTER_EVENTS = ('title_card',)
CUE_EVENTS = ('narrate', 'title_card')
CUE_MS_FALLBACK = 4500
EXPORT_FILE_NAMES = ('chapters.txt', 'subtitles.vtt', 'walkthrough.md')
TRANSCRIPT_FILE_NAME = 'transcript.json'


def _cue_end_ms(events: list[dict[str, object]], index: int, start_ms: int) -> int:
    for event_next in events[index + 1:]:
        offset_ms = _offset_ms(event_next)

        if offset_ms > start_ms:
            return offset_ms

    return start_ms + CUE_MS_FALLBACK


def _cue_text(event: dict[str, object]) -> str:
    title = _vtt_text(_text(event, 'title'))
    body = _vtt_text(_text(event, 'body'))

    if body:
        return f'{title}\n{body}'

    return title


def _markdown_action_lines(event: dict[str, object]) -> list[str]:
    name = _text(event, 'event')

    if name == 'fill':
        return _markdown_fill_lines(event)

    if name == 'press':
        return _markdown_press_lines(event)

    if name == 'select':
        return _markdown_select_lines(event)

    if name == 'slide':
        return ['- Slide to confirm', '']

    return _markdown_verb_lines(event)


def _markdown_delta_lines(event: dict[str, object]) -> list[str]:
    lines = [f'## {_text(event, "title")}', '']
    subtitle = _text(event, 'subtitle')

    if subtitle:
        lines += [subtitle, '']

    rows = event.get('rows')

    if not isinstance(rows, list):
        return lines

    lines += [
        '| Metric | Before | After | Delta |',
        '|---|---|---|---|',
    ]

    for row in rows:
        if isinstance(row, dict):
            cells = (
                _text(row, 'label'),
                _text(row, 'before'),
                _text(row, 'after'),
                _text(row, 'delta'),
            )

            lines.append('| ' + ' | '.join(cells) + ' |')

    lines.append('')

    return lines


def _markdown_event_lines(event: dict[str, object]) -> list[str]:
    name = _text(event, 'event')

    if name in ACTION_EVENTS:
        return _markdown_action_lines(event)

    renderers = {
        'delta_card': _markdown_delta_lines,
        'narrate': _markdown_narrate_lines,
        'shot': _markdown_shot_lines,
        'spotlight': _markdown_spotlight_lines,
        'title_card': _markdown_title_lines,
    }

    renderer = renderers.get(name)

    if renderer is None:
        return []

    return renderer(event)


def _markdown_fill_lines(event: dict[str, object]) -> list[str]:
    target = _text(event, 'target')
    value = _text(event, 'value')

    if target:
        return [f'- Fill "{target}" with "{value}"', '']

    return [f'- Type "{value}"', '']


def _markdown_narrate_lines(event: dict[str, object]) -> list[str]:
    lines = [f'## {_text(event, "title")}', '']
    body = _text(event, 'body')

    if body:
        lines += [body, '']

    return lines


def _markdown_press_lines(event: dict[str, object]) -> list[str]:
    key = _text(event, 'key')

    if not key:
        return []

    return [f'- Press {key}', '']


def _markdown_select_lines(event: dict[str, object]) -> list[str]:
    option = _text(event, 'option')

    if not option:
        return []

    return [f'- Select "{option}"', '']


def _markdown_shot_lines(event: dict[str, object]) -> list[str]:
    file_name = _text(event, 'file')

    if not file_name:
        return []

    name = _text(event, 'name')

    return [f'![{name}]({file_name})', '']


def _markdown_spotlight_lines(event: dict[str, object]) -> list[str]:
    label = _text(event, 'label')

    if not label:
        return []

    return [f'- {label}', '']


def _markdown_title_lines(event: dict[str, object]) -> list[str]:
    lines = [f'# {_text(event, "title")}', '']
    kicker = _text(event, 'kicker')
    subtitle = _text(event, 'subtitle')

    if kicker:
        lines += [f'*{kicker}*', '']

    if subtitle:
        lines += [subtitle, '']

    return lines


def _markdown_verb_lines(event: dict[str, object]) -> list[str]:
    verb = ACTION_VERBS.get(_text(event, 'event'), '')
    target = _text(event, 'target')

    if not verb:
        return []

    if not target:
        return []

    return [f'- {verb} "{target}"', '']


def _offset_ms(event: dict[str, object]) -> int:
    offset = event.get('offset_ms')

    if isinstance(offset, int):
        return offset

    return 0


def _text(event: dict[str, object], key: str) -> str:
    value = event.get(key)

    if isinstance(value, str):
        return value

    return ''


def _timestamp(ms: int) -> str:
    seconds_total, milliseconds = divmod(ms, 1000)
    minutes_total, seconds = divmod(seconds_total, 60)
    hours, minutes = divmod(minutes_total, 60)

    return f'{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}'


def _timestamp_chapter(ms: int) -> str:
    minutes, seconds = divmod(ms // 1000, 60)

    return f'{minutes:02d}:{seconds:02d}'


def _vtt_text(value: str) -> str:
    return value.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def chapters_render(events: list[dict[str, object]]) -> str:
    lines = [
        f'{_timestamp_chapter(_offset_ms(event))} {_text(event, "title")}'
        for event in events
        if event.get('event') in CHAPTER_EVENTS
    ]

    if not lines:
        return ''

    return '\n'.join(lines) + '\n'


def exports_write(events: list[dict[str, object]], directory: Path, *, title: str = '') -> list[Path]:
    contents = {
        'chapters.txt': chapters_render(events),
        'subtitles.vtt': vtt_render(events),
        'walkthrough.md': markdown_render(events, title=title),
    }

    paths: list[Path] = []

    for file_name, content in contents.items():
        path = directory / file_name

        path.write_text(content, encoding='utf-8')
        paths.append(path)

    return paths


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='limelight-export')

    parser.add_argument('transcript', type=Path)
    parser.add_argument('--title', default='')

    arguments = parser.parse_args(argv)

    transcript_path = transcript_path_resolve(arguments.transcript)
    events = transcript_events_load(transcript_path)
    paths = exports_write(events, transcript_path.parent, title=arguments.title)

    for path in paths:
        sys.stdout.write(f'{path}\n')

    return 0


def markdown_render(events: list[dict[str, object]], *, title: str = '') -> str:
    lines: list[str] = []

    if title:
        lines += [f'# {title}', '']

    for event in events:
        lines += _markdown_event_lines(event)

    return '\n'.join(lines).strip() + '\n'


def transcript_events_load(path: Path) -> list[dict[str, object]]:
    payload = transcript_payload_load(path)
    events = payload.get('events')

    if not isinstance(events, list):
        message = f'no events found in {path}'
        raise TypeError(message)

    return [event for event in events if isinstance(event, dict)]


def transcript_path_resolve(path: Path) -> Path:
    if path.is_dir():
        return path / TRANSCRIPT_FILE_NAME

    return path


def transcript_payload_load(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding='utf-8'))

    if not isinstance(payload, dict):
        message = f'transcript is not a JSON object: {path}'
        raise TypeError(message)

    return payload


def vtt_render(events: list[dict[str, object]]) -> str:
    lines = ['WEBVTT']

    for index, event in enumerate(events):
        if event.get('event') not in CUE_EVENTS:
            continue

        start_ms = _offset_ms(event)
        end_ms = _cue_end_ms(events, index, start_ms)

        lines += [
            '',
            f'{_timestamp(start_ms)} --> {_timestamp(end_ms)}',
            _cue_text(event),
        ]

    return '\n'.join(lines) + '\n'
