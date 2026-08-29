from __future__ import annotations

import argparse
import sys

from pathlib import Path
from typing import TYPE_CHECKING

from limelight.artifacts import SUBTITLES_FILE_NAME
from limelight.export import exports_run
from limelight.export.chapters import chapters_export
from limelight.export.subtitles import subtitles_export
from limelight.export.video import GifExport, VideoExport
from limelight.export.walkthrough import walkthrough_export
from limelight.ffmpeg import Ffmpeg
from limelight.transcript import transcript_load, transcript_path_resolve

if TYPE_CHECKING:
    from collections.abc import Sequence

    from limelight.export import Export
    from limelight.ffmpeg import Encoder


def _arguments_parse(argv: Sequence[str] | None) -> argparse.Namespace:
    """
    A function that parses the command line for the render command.

    :param argv: The arguments to parse, or None to read them from the process.
    :return: The parsed arguments.
    """

    parser = argparse.ArgumentParser(prog='limelight-render')

    parser.add_argument('transcript', type=Path)
    parser.add_argument('--audio', type=Path, default=None)
    parser.add_argument('--gif', action='store_true')
    parser.add_argument('--subtitles', action='store_true')
    parser.add_argument('--title', default='')

    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None, *, encoder: Encoder | None = None) -> int:
    """
    A function that renders every artifact asked for on the command line.

    The video render is run whenever audio or subtitles are asked for, because both
    are laid over the frames rather than shipped beside them.

    :param argv: The arguments to parse, or None to read them from the process.
    :param encoder: The encoder the renders run through, or None to use ffmpeg on PATH.
    :return: The exit status of the command.
    """

    arguments = _arguments_parse(argv)

    if encoder is None:
        encoder = Ffmpeg()

    transcript_path = transcript_path_resolve(arguments.transcript)
    directory = transcript_path.parent
    events = transcript_load(transcript_path)

    exports: list[Export] = [
        chapters_export(),
        subtitles_export(),
        walkthrough_export(arguments.title),
    ]

    subtitles = directory / SUBTITLES_FILE_NAME if arguments.subtitles else None
    video_needed = subtitles is not None

    if arguments.audio is not None:
        video_needed = True

    if video_needed:
        video_export = VideoExport(encoder, audio=arguments.audio, subtitles=subtitles)
        exports.append(video_export)

    if arguments.gif:
        gif_export = GifExport(encoder)
        exports.append(gif_export)

    for path in exports_run(events, directory, exports):
        sys.stdout.write(f'{path}\n')

    return 0
