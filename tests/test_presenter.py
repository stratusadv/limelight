from __future__ import annotations

import json

from pathlib import Path
from typing_extensions import TYPE_CHECKING

from limelight.config import DEMO_MODE_NARRATE, DemoConfig
from limelight.presenter import Presenter, PresenterNarrated, PresenterSilent, presenter_build

from fakes import FakeLocator, FakePage

if TYPE_CHECKING:
    import pytest

    from limelight.ledger import LedgerRow


def test_silent_config_builds_null_presenter() -> None:
    presenter = presenter_build(FakePage().as_page(), DemoConfig(), shot_directory=Path('test-results/demo'))

    assert isinstance(presenter, PresenterSilent)


def test_narrated_config_builds_narrated_presenter() -> None:
    config = DemoConfig(mode=DEMO_MODE_NARRATE)

    presenter = presenter_build(FakePage().as_page(), config, shot_directory=Path('test-results/demo'))

    assert isinstance(presenter, PresenterNarrated)


def test_both_presenters_satisfy_protocol() -> None:
    page = FakePage()
    config = DemoConfig(mode=DEMO_MODE_NARRATE)

    assert isinstance(presenter_build(page.as_page(), config, shot_directory=Path('x')), Presenter)
    assert isinstance(PresenterSilent(), Presenter)


def test_silent_presenter_never_touches_the_page() -> None:
    page = FakePage()
    presenter = presenter_build(page.as_page(), DemoConfig(), shot_directory=Path('x'))

    rows: list[LedgerRow] = []

    presenter.beat()
    presenter.clear()
    presenter.clear_spotlight()
    presenter.delta_card('Totals', rows)
    presenter.hold()
    presenter.narrate('Welcome')
    presenter.shot('welcome')
    presenter.spotlight(FakeLocator().as_locator())
    presenter.title_card('Chapter')
    presenter.use_page(page.as_page())

    assert page.evaluations == []
    assert page.screenshot_paths == []
    assert page.waits_ms == []


def test_narrated_presenter_routes_shots_to_camera(tmp_path: Path) -> None:
    page = FakePage()
    config = DemoConfig(mode=DEMO_MODE_NARRATE, shots=True)

    presenter = presenter_build(page.as_page(), config, shot_directory=tmp_path / 'shots')
    presenter.shot('welcome')

    assert page.screenshot_paths == [str(tmp_path / 'shots' / '01-welcome.png')]


def test_silent_presenter_acts_directly_on_the_locator() -> None:
    presenter = presenter_build(FakePage().as_page(), DemoConfig(), shot_directory=Path('x'))
    locator = FakeLocator()

    presenter.click(locator.as_locator())
    presenter.fill(locator.as_locator(), 'hello')
    presenter.select(locator.as_locator(), 'Approved')

    assert locator.click_count == 1
    assert locator.fill_values == ['hello']
    assert locator.select_labels == ['Approved']
    assert locator.typed_sequences == []


def test_silent_presenter_acts_directly_for_new_actions() -> None:
    presenter = presenter_build(FakePage().as_page(), DemoConfig(), shot_directory=Path('x'))
    locator = FakeLocator()

    presenter.check(locator.as_locator())
    presenter.hover(locator.as_locator())
    presenter.press(locator.as_locator(), 'Enter')
    presenter.uncheck(locator.as_locator())

    assert locator.check_count == 1
    assert locator.hover_count == 1
    assert locator.pressed_keys == ['Enter']
    assert locator.uncheck_count == 1


def test_silent_presenter_slides_via_gesture(monkeypatch: pytest.MonkeyPatch) -> None:
    slides: list[tuple[object, object, object]] = []

    def slide_stub(page: object, *, track: object, thumb: object) -> None:
        slide = (page, track, thumb)
        slides.append(slide)

    monkeypatch.setattr('limelight.presenter.slide_to_end', slide_stub)

    presenter = presenter_build(FakePage().as_page(), DemoConfig(), shot_directory=Path('x'))
    track = FakeLocator()
    thumb = FakeLocator()

    presenter.slide(track=track.as_locator(), thumb=thumb.as_locator())

    assert len(slides) == 1


def test_narrated_presenter_records_actions(tmp_path: Path) -> None:
    page = FakePage()
    config = DemoConfig(mode=DEMO_MODE_NARRATE)

    presenter = presenter_build(page.as_page(), config, shot_directory=tmp_path / 'shots')

    locator = FakeLocator()
    locator.label = 'Approve'

    presenter.click(locator.as_locator())
    presenter.fill(locator.as_locator(), 'SO-100')
    presenter.select(locator.as_locator(), 'Approved')
    presenter.press(locator.as_locator(), 'Enter')

    transcript_path = tmp_path / 'shots' / 'transcript.json'
    payload = json.loads(transcript_path.read_text(encoding='utf-8'))
    events = payload['events']

    assert [event['event'] for event in events] == ['click', 'fill', 'select', 'press']
    assert events[0]['target'] == 'Approve'
    assert events[1]['value'] == 'SO-100'
    assert events[2]['option'] == 'Approved'
    assert events[3]['key'] == 'Enter'


def test_narrated_presenter_records_transcript(tmp_path: Path) -> None:
    page = FakePage()
    config = DemoConfig(mode=DEMO_MODE_NARRATE, shots=True)

    presenter = presenter_build(page.as_page(), config, shot_directory=tmp_path / 'shots')

    presenter.title_card('Order Approval')
    presenter.narrate('Open the order', body='Navigate to it.')
    presenter.shot('welcome')

    transcript_path = tmp_path / 'shots' / 'transcript.json'

    assert transcript_path.is_file()

    payload = json.loads(transcript_path.read_text(encoding='utf-8'))
    events = payload['events']

    assert [event['event'] for event in events] == ['title_card', 'narrate', 'shot']
    assert events[1]['title'] == 'Open the order'
    assert events[2]['file'] == '01-welcome.png'
