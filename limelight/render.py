from __future__ import annotations

import argparse
import shutil
import sys

from pathlib import Path
from typing import TYPE_CHECKING

from limelight.export import exports_write, transcript_events_load, transcript_path_resolve, transcript_payload_load
from limelight.frames import VIDEO_FILE_NAME
from limelight.video import render_gif, render_mp4, trim_lead_ms_from_epochs, video_started_at_epoch_ms

if TYPE_CHECKING:
    from collections.abc import Sequence


RENDER_FILE_NAME = 'render.mp4'
SUFFIX_MP4 = '.mp4'


def _arguments_parse(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog='limelight-render')

    parser.add_argument('transcript', type=Path)
    parser.add_argument('--audio', type=Path, default=None)
    parser.add_argument('--gif', action='store_true')
    parser.add_argument('--subtitles', action='store_true')
    parser.add_argument('--title', default='')
    parser.add_argument('--trim-lead-ms', type=int, default=None)
    parser.add_argument('--video', type=Path, default=None)

    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _arguments_parse(argv)

    transcript_path = transcript_path_resolve(arguments.transcript)
    directory = transcript_path.parent
    events = transcript_events_load(transcript_path)
    payload = transcript_payload_load(transcript_path)

    paths = exports_write(events, directory, title=arguments.title)

    video_path = arguments.video if arguments.video is not None else video_locate(directory)
    trim_ms = arguments.trim_lead_ms if arguments.trim_lead_ms is not None else trim_lead_ms_detect(video_path, payload)
    subtitles = directory / 'subtitles.vtt' if arguments.subtitles else None

    if video_needs_render(video_path, audio=arguments.audio, subtitles=subtitles, trim_lead_ms=trim_ms):
        mp4_path = render_mp4(
            video_path,
            audio=arguments.audio,
            destination=video_path.with_name(RENDER_FILE_NAME),
            subtitles=subtitles,
            trim_lead_ms=trim_ms,
        )

        paths.append(mp4_path)
    else:
        paths.append(video_path)

    if arguments.gif:
        gif_path = render_gif(video_path)

        paths.append(gif_path)

    for path in paths:
        sys.stdout.write(f'{path}\n')

    return 0


def trim_lead_ms_detect(video: Path, payload: dict[str, object]) -> int:
    session_started_at = payload.get('started_at_epoch_ms')

    if video.suffix == SUFFIX_MP4:
        return 0

    if not isinstance(session_started_at, int):
        return 0

    if shutil.which('ffprobe') is None:
        return 0

    video_started_at = video_started_at_epoch_ms(video)

    return trim_lead_ms_from_epochs(
        session_started_at_epoch_ms=session_started_at,
        video_started_at_epoch_ms=video_started_at,
    )


def video_locate(directory: Path) -> Path:
    rendered = directory / VIDEO_FILE_NAME

    if rendered.is_file():
        return rendered

    videos = sorted(directory.rglob('*.webm'), key=lambda path: path.stat().st_mtime)

    if not videos:
        message = f'no {VIDEO_FILE_NAME} or .webm video found under {directory}; pass --video'
        raise FileNotFoundError(message)

    return videos[-1]


def video_needs_render(
    video: Path,
    *,
    audio: Path | None,
    subtitles: Path | None,
    trim_lead_ms: int,
) -> bool:
    if video.suffix != SUFFIX_MP4:
        return True

    return audio is not None or subtitles is not None or trim_lead_ms > 0
