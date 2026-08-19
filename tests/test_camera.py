from __future__ import annotations

import pytest

from pathlib import Path

from limelight.camera import Camera

from fakes import FakePage


def test_directory_must_be_real() -> None:
    with pytest.raises(ValueError, match='directory'):
        Camera(FakePage().as_page(), Path(), enabled=True)


def test_disabled_camera_takes_no_shot(tmp_path: Path) -> None:
    page = FakePage()
    camera = Camera(page.as_page(), tmp_path / 'shots', enabled=False)

    assert camera.shot('welcome') is None
    assert page.screenshot_paths == []


def test_empty_name_takes_no_shot(tmp_path: Path) -> None:
    page = FakePage()
    camera = Camera(page.as_page(), tmp_path / 'shots', enabled=True)

    assert camera.shot('') is None
    assert page.screenshot_paths == []


def test_shot_name_is_sanitized_for_the_filesystem(tmp_path: Path) -> None:
    page = FakePage()
    directory = tmp_path / 'shots'
    camera = Camera(page.as_page(), directory, enabled=True)

    path = camera.shot('order/approve now!')

    assert path == directory / '01-order-approve-now.png'


def test_shot_name_with_no_valid_characters_takes_no_shot(tmp_path: Path) -> None:
    page = FakePage()
    camera = Camera(page.as_page(), tmp_path / 'shots', enabled=True)

    assert camera.shot('///') is None
    assert page.screenshot_paths == []


def test_shot_creates_directory_and_screenshots(tmp_path: Path) -> None:
    page = FakePage()
    directory = tmp_path / 'shots'
    camera = Camera(page.as_page(), directory, enabled=True)

    path = camera.shot('welcome')

    assert directory.is_dir()
    assert path == directory / '01-welcome.png'
    assert page.screenshot_paths == [str(directory / '01-welcome.png')]


def test_shots_number_in_capture_order(tmp_path: Path) -> None:
    page = FakePage()
    directory = tmp_path / 'shots'
    camera = Camera(page.as_page(), directory, enabled=True)

    camera.shot('welcome')
    camera.shot('orders')

    paths_expected = [
        str(directory / '01-welcome.png'),
        str(directory / '02-orders.png'),
    ]

    assert page.screenshot_paths == paths_expected


def test_use_page_switches_target(tmp_path: Path) -> None:
    page_first = FakePage()
    page_second = FakePage()
    camera = Camera(page_first.as_page(), tmp_path / 'shots', enabled=True)

    camera.use_page(page_second.as_page())
    camera.shot('welcome')

    assert page_first.screenshot_paths == []
    assert len(page_second.screenshot_paths) == 1
