from __future__ import annotations

from typing import TYPE_CHECKING

from limelight import ffmpeg
from limelight.artifacts import VOICEOVER_FILE_NAME
from limelight.transcript import EventName, cue_text, event_offset_ms

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from limelight.ffmpeg import Encoder
    from limelight.transcript import Event

    Synthesizer = Callable[[str, Path], None]


CUE_SUFFIX_DEFAULT = '.wav'
VOICEOVER_EVENTS = (EventName.NARRATE, EventName.TITLE)


class VoiceoverExport:
    """
    An export that speaks the narration and mixes it onto one track.

    This class synthesizes each cue to its own file and hands the offsets to the
    encoder, so a clip that runs long overlaps the next rather than pushing it out
    of step with the video.
    """

    def __init__(
        self,
        synthesize: Synthesizer,
        *,
        encoder: Encoder | None = None,
        file_name: str = VOICEOVER_FILE_NAME,
        cue_suffix: str = CUE_SUFFIX_DEFAULT,
    ) -> None:
        """
        The constructor for the VoiceoverExport class.

        :param synthesize: The callable that speaks a line into an audio file.
        :param encoder: The encoder the mix runs through, or None to use ffmpeg on PATH.
        :param file_name: The name of the mixed track.
        :param cue_suffix: The file extension for each synthesized clip, including the dot.
        :raises ValueError: If the file name is empty, or the suffix does not start with a dot.
        """

        if not file_name.strip():
            message = f'file_name must not be empty (got "{file_name}")'
            raise ValueError(message)

        if not cue_suffix.startswith('.'):
            message = f'cue_suffix must start with a dot: {cue_suffix}'
            raise ValueError(message)

        self._cue_suffix = cue_suffix
        self._encoder = encoder if encoder is not None else ffmpeg.Ffmpeg()
        self._file_name = file_name
        self._synthesize = synthesize

    def export(self, events: list[Event], directory: Path) -> Path:
        """
        A method that speaks each cue and mixes them into one track.

        :param events: The recorded events of the run.
        :param directory: The directory the clips and the track are written to.
        :return: The path the track was written to.
        :raises ValueError: If the run carries nothing to speak.
        """

        cues = voiceover_cues(events)

        if not cues:
            message = 'no narrate or title events to voice'
            raise ValueError(message)

        destination = directory / self._file_name
        cue_files: list[tuple[int, Path]] = []

        for index, cue in enumerate(cues):
            offset_ms, text = cue
            path = directory / f'voiceover-cue-{index:02d}{self._cue_suffix}'

            self._synthesize(text, path)

            cue_file = (offset_ms, path)
            cue_files.append(cue_file)

        arguments = ffmpeg.arguments_voiceover(cue_files, destination)

        self._encoder.run(arguments)

        return destination


def voiceover_cues(events: list[Event]) -> list[tuple[int, str]]:
    """
    A function that collects the lines a run has to speak.

    :param events: The recorded events of the run.
    :return: The offset and the text of each cue, with the silent events dropped.
    """

    cues: list[tuple[int, str]] = []

    for event in events:
        if event.get('event') not in VOICEOVER_EVENTS:
            continue

        text = cue_text(event)

        if not text:
            continue

        cue = (event_offset_ms(event), text)

        cues.append(cue)

    return cues
