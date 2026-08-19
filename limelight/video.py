from __future__ import annotations

import shutil
import subprocess

from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


GIF_FPS_DEFAULT = 12
GIF_WIDTH_DEFAULT = 960


def _binary_locate(name: str) -> str:
    binary = shutil.which(name)

    if binary is None:
        message = f'{name} not found on PATH; install it to render video artifacts'
        raise RuntimeError(message)

    return binary


def _source_validate(source: Path) -> None:
    if not source.is_file():
        message = f'source video not found: {source}'
        raise FileNotFoundError(message)


def _subtitles_filter(subtitles: Path) -> str:
    path_text = str(subtitles).replace('\\', '\\\\').replace("'", "\\'").replace(':', '\\:')

    return f'subtitles={path_text}'


def ffmpeg_arguments_gif(
    source: Path,
    destination: Path,
    *,
    fps: int = GIF_FPS_DEFAULT,
    width: int = GIF_WIDTH_DEFAULT,
) -> list[str]:
    if fps < 1:
        message = f'fps must be positive: {fps}'
        raise ValueError(message)

    if width < 1:
        message = f'width must be positive: {width}'
        raise ValueError(message)

    filter_graph = (
        f'fps={fps},scale={width}:-1:flags=lanczos,'
        'split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse'
    )

    return ['-i', str(source), '-vf', filter_graph, str(destination)]


def ffmpeg_arguments_mp4(
    source: Path,
    destination: Path,
    *,
    audio: Path | None = None,
    subtitles: Path | None = None,
    trim_lead_ms: int = 0,
) -> list[str]:
    if trim_lead_ms < 0:
        message = f'trim_lead_ms must be non-negative: {trim_lead_ms}'
        raise ValueError(message)

    arguments: list[str] = []

    if trim_lead_ms > 0:
        arguments += ['-ss', f'{trim_lead_ms / 1000:.3f}']

    arguments += ['-i', str(source)]

    if audio is not None:
        arguments += ['-i', str(audio)]

    if subtitles is not None:
        arguments += ['-vf', _subtitles_filter(subtitles)]

    arguments += [
        '-c:v',
        'libx264',
        '-pix_fmt',
        'yuv420p',
        '-movflags',
        '+faststart',
    ]

    if audio is not None:
        arguments += [
            '-map',
            '0:v:0',
            '-map',
            '1:a:0',
            '-c:a',
            'aac',
            '-shortest',
        ]

    arguments += [str(destination)]

    return arguments


def ffmpeg_run(arguments: list[str]) -> None:
    command = [_binary_locate('ffmpeg'), '-y', *arguments]

    subprocess.run(command, check=True)


def ffprobe_arguments_duration(source: Path) -> list[str]:
    return [
        '-v',
        'error',
        '-show_entries',
        'format=duration',
        '-of',
        'default=noprint_wrappers=1:nokey=1',
        str(source),
    ]


def ffprobe_run(arguments: list[str]) -> str:
    command = [_binary_locate('ffprobe'), *arguments]
    result = subprocess.run(command, check=True, capture_output=True, text=True)

    return result.stdout


def render_gif(
    source: Path,
    destination: Path | None = None,
    *,
    fps: int = GIF_FPS_DEFAULT,
    width: int = GIF_WIDTH_DEFAULT,
) -> Path:
    _source_validate(source)

    destination_path = destination if destination is not None else source.with_suffix('.gif')
    arguments = ffmpeg_arguments_gif(source, destination_path, fps=fps, width=width)

    ffmpeg_run(arguments)

    return destination_path


def render_mp4(
    source: Path,
    destination: Path | None = None,
    *,
    audio: Path | None = None,
    subtitles: Path | None = None,
    trim_lead_ms: int = 0,
) -> Path:
    _source_validate(source)

    destination_path = destination if destination is not None else source.with_suffix('.mp4')

    arguments = ffmpeg_arguments_mp4(
        source,
        destination_path,
        audio=audio,
        subtitles=subtitles,
        trim_lead_ms=trim_lead_ms,
    )

    ffmpeg_run(arguments)

    return destination_path


def trim_lead_ms_from_epochs(*, session_started_at_epoch_ms: int, video_started_at_epoch_ms: int) -> int:
    lead_ms = session_started_at_epoch_ms - video_started_at_epoch_ms

    return max(0, lead_ms)


def video_duration_ms(source: Path) -> int:
    _source_validate(source)

    arguments = ffprobe_arguments_duration(source)
    duration_text = ffprobe_run(arguments).strip()

    if not duration_text:
        message = f'ffprobe returned no duration for {source}'
        raise RuntimeError(message)

    return int(float(duration_text) * 1000)


def video_started_at_epoch_ms(source: Path) -> int:
    _source_validate(source)

    ended_at_epoch_ms = int(source.stat().st_mtime * 1000)

    return ended_at_epoch_ms - video_duration_ms(source)
