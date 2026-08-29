from __future__ import annotations

from typing import TYPE_CHECKING

from limelight import ffmpeg
from limelight.artifacts import VOICEOVER_FILE_NAME
from limelight.transcript import EventName, event_offset_ms, event_text

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from limelight.ffmpeg import Encoder
    from limelight.transcript import Event


    Synthesizer = Callable[[str, Path], None]


CUE_SUFFIX_DEFAULT = '.wav'
VOICEOVER_EVENTS = (EventName.NARRATE, EventName.TITLE)


def _cue_text(event: Event) -> str:
    """
    A function that renders the spoken text of one cue.

    :param event: The event the cue is built from.
    :return: The title, subtitle, and body joined into one line, with the empty pieces dropped.
    """

    pieces = [
        event_text(event, 'title'),
        event_text(event, 'subtitle'),
        event_text(event, 'body'),
    ]

    return ' '.join(piece for piece in pieces if piece)


class VoiceoverExport:
    """
    An export that speaks the narration and mixes it onto one track.

    This class synthesizes each cue to its own file and hands the offsets to the
    encoder, so a clip that runs long overlaps the next rather than pushing it out
    of step with the video.
    """

    def __init__(
        self,
        encoder: Encoder,
        synthesize: Synthesizer,
        *,
        file_name: str = VOICEOVER_FILE_NAME,
        cue_suffix: str = CUE_SUFFIX_DEFAULT,
    ) -> None:
        """
        The constructor for the VoiceoverExport class.

        :param encoder: The encoder the mix runs through.
        :param synthesize: The callable that speaks a line into an audio file.
        :param file_name: The name of the mixed track.
        :param cue_suffix: The file extension for each synthesized clip, including the dot.
        """

        self._cue_suffix = cue_suffix
        self._encoder = encoder
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

        text = _cue_text(event)

        if not text:
            continue

        cue = (event_offset_ms(event), text)

        cues.append(cue)

    return cues
