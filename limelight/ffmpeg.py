from __future__ import annotations

import shutil
import subprocess

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pathlib import Path
    from subprocess import Popen


BINARY_DEFAULT = 'ffmpeg'

FRAMES_CRF_DEFAULT = 14
FRAMES_CRF_MAX = 51
FRAMES_PRESET_DEFAULT = 'fast'

GIF_FPS_DEFAULT = 12
GIF_WIDTH_DEFAULT = 960


def _subtitles_filter(subtitles: Path) -> str:
    """
    A function that escapes a subtitle path into an ffmpeg filter argument.

    The path is escaped three times over because the filter graph is parsed as a
    string within a string: a backslash, a quote, and the colon that separates a
    filter option each end the argument early on Windows paths.

    :param subtitles: The path to the subtitle file.
    :return: The subtitles filter with the escaped path.
    """

    path_text = str(subtitles).replace('\\', '\\\\').replace("'", "\\'").replace(':', '\\:')

    return f'subtitles={path_text}'


@runtime_checkable
class Encoder(Protocol):
    """
    A protocol for the encoder a render writes its frames through.

    This protocol covers the two ways ffmpeg is driven: a pipe that frames are
    streamed into, and a blocking run for a one-shot conversion.
    """

    def pipe(self, arguments: list[str]) -> Popen[bytes]:
        """
        A method that starts an encoder reading frames from its standard input.

        :param arguments: The command-line arguments for the encoder.
        :return: The running encoder process.
        """

        ...

    def run(self, arguments: list[str]) -> None:
        """
        A method that runs an encoder to completion.

        :param arguments: The command-line arguments for the encoder.
        """

        ...


class Ffmpeg:
    """An encoder backed by the ffmpeg binary on PATH."""

    def __init__(self, binary: str = BINARY_DEFAULT) -> None:
        """
        The constructor for the Ffmpeg class.

        :param binary: The name of the ffmpeg executable.
        :raises ValueError: If the binary name is empty.
        """

        if not binary.strip():
            message = 'binary must not be empty'
            raise ValueError(message)

        self.binary = binary

    def _locate(self) -> str:
        """
        A method that resolves the ffmpeg binary on PATH.

        The binary is looked up per call rather than at construction, so a demo that
        never renders a video artifact runs on a machine without ffmpeg installed.

        :return: The absolute path to the binary.
        :raises RuntimeError: If the binary is not on PATH.
        """

        path = shutil.which(self.binary)

        if path is None:
            message = f'{self.binary} not found on PATH; install it to render video artifacts'
            raise RuntimeError(message)

        return path

    def pipe(self, arguments: list[str]) -> Popen[bytes]:
        """
        A method that starts ffmpeg reading frames from its standard input.

        :param arguments: The command-line arguments for ffmpeg.
        :return: The running ffmpeg process.
        :raises RuntimeError: If the binary is not on PATH.
        """

        command = [self._locate(), '-y', '-loglevel', 'error', *arguments]

        return subprocess.Popen(command, stdin=subprocess.PIPE)

    def run(self, arguments: list[str]) -> None:
        """
        A method that runs ffmpeg to completion.

        The output is captured rather than inherited, so a failure carries what ffmpeg
        said about it: a bare exit status names neither the input it could not read nor
        the filter it could not build.

        :param arguments: The command-line arguments for ffmpeg.
        :raises RuntimeError: If the binary is not on PATH, or ffmpeg exits with a
            non-zero status.
        """

        command = [self._locate(), '-y', '-loglevel', 'error', *arguments]

        outcome = subprocess.run(command, capture_output=True, check=False)

        if outcome.returncode != 0:
            detail = outcome.stderr.decode('utf-8', 'replace').strip()

            message = f'ffmpeg exited with status {outcome.returncode}: {detail}'
            raise RuntimeError(message)


def arguments_frames(
    destination: Path,
    *,
    fps: int,
    crf: int = FRAMES_CRF_DEFAULT,
    preset: str = FRAMES_PRESET_DEFAULT,
) -> list[str]:
    """
    A function that builds the ffmpeg arguments for encoding piped frames.

    :param destination: The file the video is written to.
    :param fps: The frame rate the frames are played back at.
    :param crf: The constant rate factor, where a lower number is higher quality.
    :param preset: The encoder preset, trading speed against file size.
    :return: The command-line arguments for ffmpeg.
    :raises ValueError: If the frame rate is not positive, or the rate factor is out of range.
    """

    if fps < 1:
        message = f'fps must be positive: {fps}'
        raise ValueError(message)

    if crf < 0:
        message = f'crf must be non-negative: {crf}'
        raise ValueError(message)

    if crf > FRAMES_CRF_MAX:
        message = f'crf must not exceed {FRAMES_CRF_MAX}: {crf}'
        raise ValueError(message)

    return [
        '-f',
        'image2pipe',
        '-framerate',
        str(fps),
        '-i',
        '-',
        '-c:v',
        'libx264',
        '-preset',
        preset,
        '-crf',
        str(crf),
        '-pix_fmt',
        'yuv420p',
        '-movflags',
        '+faststart',
        str(destination),
    ]


def arguments_gif(
    source: Path,
    *,
    destination: Path,
    fps: int = GIF_FPS_DEFAULT,
    width: int = GIF_WIDTH_DEFAULT,
) -> list[str]:
    """
    A function that builds the ffmpeg arguments for converting a video to a GIF.

    The graph generates a palette from the scaled frames before applying it,
    because the default palette is the 216-color web set and a screen recording
    banded against it shows visible steps across a gradient.

    :param source: The video to convert.
    :param destination: The file the GIF is written to.
    :param fps: The frame rate of the GIF.
    :param width: The width the frames are scaled to, with the height kept in proportion.
    :return: The command-line arguments for ffmpeg.
    :raises ValueError: If the frame rate or the width is not positive.
    """

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


def arguments_mp4(
    source: Path,
    *,
    destination: Path,
    audio: Path | None = None,
    subtitles: Path | None = None,
) -> list[str]:
    """
    A function that builds the ffmpeg arguments for the final video.

    The shortest flag ends the output with the video rather than the audio, so a
    voiceover that overruns the last frame cannot pad the file with a still.

    :param source: The rendered video the audio and subtitles are laid over.
    :param destination: The file the video is written to.
    :param audio: The voiceover to mix in, or None for a silent video.
    :param subtitles: The subtitles to burn in, or None to leave the frames alone.
    :return: The command-line arguments for ffmpeg.
    """

    arguments = ['-i', str(source)]

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


def arguments_voiceover(cues: list[tuple[int, Path]], destination: Path) -> list[str]:
    """
    A function that builds the ffmpeg arguments for one voiceover track.

    Each clip is delayed to its own cue and the delayed streams are mixed, with
    normalization off because amix otherwise divides every input by the number of
    inputs and a long transcript fades to silence.

    :param cues: The offset in milliseconds and the audio file for each clip.
    :param destination: The file the mixed track is written to.
    :return: The command-line arguments for ffmpeg.
    :raises ValueError: If there are no cues, or a cue offset is negative.
    """

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
