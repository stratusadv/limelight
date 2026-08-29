from __future__ import annotations

from typing import TYPE_CHECKING

from limelight.artifacts import WALKTHROUGH_FILE_NAME
from limelight.export import TextExport
from limelight.transcript import EventName, event_text

if TYPE_CHECKING:
    from limelight.transcript import Event


ACTION_EVENTS = (
    EventName.CHECK,
    EventName.CLICK,
    EventName.FILL,
    EventName.HOVER,
    EventName.PRESS,
    EventName.SELECT,
    EventName.SLIDE,
    EventName.UNCHECK,
)

ACTION_VERBS = {
    EventName.CHECK: 'Check',
    EventName.CLICK: 'Click',
    EventName.HOVER: 'Hover over',
    EventName.UNCHECK: 'Uncheck',
}


def _action_lines(event: Event) -> list[str]:
    """
    A function that renders one action event as markdown.

    :param event: The event to render.
    :return: The lines for the action, followed by a blank line.
    """

    name = event_text(event, 'event')

    if name == EventName.FILL:
        return _fill_lines(event)

    if name == EventName.PRESS:
        return _press_lines(event)

    if name == EventName.SELECT:
        return _select_lines(event)

    if name == EventName.SLIDE:
        return ['- Slide to confirm', '']

    return _verb_lines(event)


def _event_lines(event: Event) -> list[str]:
    """
    A function that renders one event as markdown.

    :param event: The event to render.
    :return: The lines for the event, or an empty list if the event has no rendering.
    """

    name = event_text(event, 'event')

    if name in ACTION_EVENTS:
        return _action_lines(event)

    renderers = {
        EventName.METRICS: _metrics_lines,
        EventName.NARRATE: _narrate_lines,
        EventName.SCREENSHOT: _screenshot_lines,
        EventName.SPOTLIGHT: _spotlight_lines,
        EventName.TITLE: _title_lines,
    }

    renderer = renderers.get(name)

    if renderer is None:
        return []

    return renderer(event)


def _fill_lines(event: Event) -> list[str]:
    """
    A function that renders a fill event as markdown.

    :param event: The event to render.
    :return: The lines naming the field and the text put into it.
    """

    target = event_text(event, 'target')
    value = event_text(event, 'value')

    if target:
        return [f'- Fill "{target}" with "{value}"', '']

    return [f'- Type "{value}"', '']


def _metrics_lines(event: Event) -> list[str]:
    """
    A function that renders a metrics event as a markdown table.

    :param event: The event to render.
    :return: The heading, the subtitle, and the table of readings.
    """

    lines = [f'## {event_text(event, "title")}', '']
    subtitle = event_text(event, 'subtitle')

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
                event_text(row, 'label'),
                event_text(row, 'before'),
                event_text(row, 'after'),
                event_text(row, 'delta'),
            )

            lines.append('| ' + ' | '.join(cells) + ' |')

    lines.append('')

    return lines


def _narrate_lines(event: Event) -> list[str]:
    """
    A function that renders a narration event as markdown.

    :param event: The event to render.
    :return: The heading and the body.
    """

    lines = [f'## {event_text(event, "title")}', '']
    body = event_text(event, 'body')

    if body:
        lines += [body, '']

    return lines


def _press_lines(event: Event) -> list[str]:
    """
    A function that renders a key press as markdown.

    :param event: The event to render.
    :return: The line naming the key, or an empty list if the event names none.
    """

    key = event_text(event, 'key')

    if not key:
        return []

    return [f'- Press {key}', '']


def _screenshot_lines(event: Event) -> list[str]:
    """
    A function that renders a screenshot event as a markdown image.

    :param event: The event to render.
    :return: The image reference, or an empty list if the event names no file.
    """

    file_name = event_text(event, 'file')

    if not file_name:
        return []

    name = event_text(event, 'name')

    return [f'![{name}]({file_name})', '']


def _select_lines(event: Event) -> list[str]:
    """
    A function that renders a select event as markdown.

    :param event: The event to render.
    :return: The line naming the option, or an empty list if the event names none.
    """

    option = event_text(event, 'option')

    if not option:
        return []

    return [f'- Select "{option}"', '']


def _spotlight_lines(event: Event) -> list[str]:
    """
    A function that renders a spotlight event as markdown.

    :param event: The event to render.
    :return: The label, or an empty list if the spotlight carried none.
    """

    label = event_text(event, 'label')

    if not label:
        return []

    return [f'- {label}', '']


def _title_lines(event: Event) -> list[str]:
    """
    A function that renders a title event as a markdown heading.

    :param event: The event to render.
    :return: The heading, the kicker, and the subtitle.
    """

    lines = [f'# {event_text(event, "title")}', '']
    kicker = event_text(event, 'kicker')
    subtitle = event_text(event, 'subtitle')

    if kicker:
        lines += [f'*{kicker}*', '']

    if subtitle:
        lines += [subtitle, '']

    return lines


def _verb_lines(event: Event) -> list[str]:
    """
    A function that renders an action whose whole rendering is a verb and a target.

    :param event: The event to render.
    :return: The line naming the action, or an empty list if the verb or the target is missing.
    """

    verb = ACTION_VERBS.get(event_text(event, 'event'), '')
    target = event_text(event, 'target')

    if not verb:
        return []

    if not target:
        return []

    return [f'- {verb} "{target}"', '']


def markdown_render(events: list[Event], *, title: str = '') -> str:
    """
    A function that renders a whole transcript as a markdown walkthrough.

    :param events: The recorded events of the run.
    :param title: The heading the document opens with, or an empty string for none.
    :return: The walkthrough.
    """

    lines: list[str] = []

    if title:
        lines += [f'# {title}', '']

    for event in events:
        lines += _event_lines(event)

    return '\n'.join(lines).strip() + '\n'


def walkthrough_export(title: str = '') -> TextExport:
    """
    A function that builds the export for the markdown walkthrough.

    :param title: The heading the document opens with, or an empty string for none.
    :return: The export that writes the walkthrough file.
    """

    def render(events: list[Event]) -> str:
        """
        A function that renders the events under the captured title.

        :param events: The recorded events of the run.
        :return: The walkthrough.
        """

        return markdown_render(events, title=title)

    return TextExport(WALKTHROUGH_FILE_NAME, render)
