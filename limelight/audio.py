from __future__ import annotations

from typing_extensions import TYPE_CHECKING

from limelight.video import ffmpeg_run

if TYPE_CHECKING:
    from pathlib import Path
    from typing_extensions import Callable


VOICEOVER_EVENTS = ('narrate', 'title_card')


def _event_text(event: dict[str, object], key: str) -> str:
    value = event.get(key)

    if isinstance(value, str):
        return value

    return ''


def _voiceover_cue_text(event: dict[str, object]) -> str:
    pieces = [
        _event_text(event, 'title'),
        _event_text(event, 'subtitle'),
        _event_text(event, 'body'),
    ]

    return ' '.join(piece for piece in pieces if piece)


def ffmpeg_arguments_voiceover(cues: list[tuple[int, Path]], destination: Path) -> list[str]:
    if not cues:
        message = 'cues must not be empty'
        raise ValueError(message)

    arguments: list[str] = []
    filters: list[str] = []
    labels: list[str] = []

    for index, cue in enumerate(cues):
        offset_ms, path = cue

        if offset_ms < 0:
            message = f'cue offset_ms must be non-negative: {offset_ms}'
            raise ValueError(message)

        arguments += ['-i', str(path)]

        filters.append(f'[{index}]adelay={offset_ms}|{offset_ms}[voice{index}]')
        labels.append(f'[voice{index}]')

    mix = f'{"".join(labels)}amix=inputs={len(cues)}:normalize=0[voiceover]'
    filter_graph = ';'.join([*filters, mix])

    arguments += ['-filter_complex', filter_graph, '-map', '[voiceover]', str(destination)]

    return arguments


def voiceover_cues(events: list[dict[str, object]]) -> list[tuple[int, str]]:
    cues: list[tuple[int, str]] = []

    for event in events:
        if event.get('event') not in VOICEOVER_EVENTS:
            continue

        text = _voiceover_cue_text(event)

        if not text:
            continue

        offset = event.get('offset_ms')
        offset_ms = offset if isinstance(offset, int) else 0
        cue = (offset_ms, text)

        cues.append(cue)

    return cues


def voiceover_render(
    events: list[dict[str, object]],
    synthesize: Callable[[str, Path], None],
    destination: Path,
    *,
    cue_suffix: str = '.wav',
) -> Path:
    cues = voiceover_cues(events)

    if not cues:
        message = 'no narrate or title_card events to voice'
        raise ValueError(message)

    destination.parent.mkdir(parents=True, exist_ok=True)

    cue_files: list[tuple[int, Path]] = []

    for index, cue in enumerate(cues):
        offset_ms, text = cue
        path = destination.parent / f'voiceover-cue-{index:02d}{cue_suffix}'

        synthesize(text, path)

        cue_file = (offset_ms, path)
        cue_files.append(cue_file)

    arguments = ffmpeg_arguments_voiceover(cue_files, destination)

    ffmpeg_run(arguments)

    return destination
