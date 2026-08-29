from __future__ import annotations

import pytest

from pathlib import Path

from limelight.capture.camera import Camera

from fakes import FakePage


def test_directory_must_be_real() -> None:
    with pytest.raises(ValueError, match='directory'):
        Camera(FakePage().as_page(), Path())


def test_empty_name_rejected(tmp_path: Path) -> None:
    page = FakePage()
    camera = Camera(page.as_page(), tmp_path / 'shots')

    with pytest.raises(ValueError, match='shot name'):
        camera.screenshot('')

    assert page.screenshot_paths == []


def test_screenshot_name_is_sanitized_for_the_filesystem(tmp_path: Path) -> None:
    page = FakePage()
    directory = tmp_path / 'shots'
    camera = Camera(page.as_page(), directory)

    path = camera.screenshot('order/approve now!')

    assert path == directory / '01-order-approve-now.png'


def test_screenshot_name_with_no_valid_characters_rejected(tmp_path: Path) -> None:
    page = FakePage()
    camera = Camera(page.as_page(), tmp_path / 'shots')

    with pytest.raises(ValueError, match='shot name'):
        camera.screenshot('///')

    assert page.screenshot_paths == []


def test_screenshot_creates_directory_and_captures(tmp_path: Path) -> None:
    page = FakePage()
    directory = tmp_path / 'shots'
    camera = Camera(page.as_page(), directory)

    path = camera.screenshot('welcome')

    assert directory.is_dir()
    assert path == directory / '01-welcome.png'
    assert page.screenshot_paths == [str(directory / '01-welcome.png')]


def test_screenshots_number_in_capture_order(tmp_path: Path) -> None:
    page = FakePage()
    directory = tmp_path / 'shots'
    camera = Camera(page.as_page(), directory)

    camera.screenshot('welcome')
    camera.screenshot('orders')

    paths_expected = [
        str(directory / '01-welcome.png'),
        str(directory / '02-orders.png'),
    ]

    assert page.screenshot_paths == paths_expected


def test_switch_page_switches_target(tmp_path: Path) -> None:
    page_first = FakePage()
    page_second = FakePage()
    camera = Camera(page_first.as_page(), tmp_path / 'shots')

    camera.switch_page(page_second.as_page())
    camera.screenshot('welcome')

    assert page_first.screenshot_paths == []
    assert len(page_second.screenshot_paths) == 1
