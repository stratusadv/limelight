from __future__ import annotations

from limelight.export.subtitles import vtt_render

from events import events_sample


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
