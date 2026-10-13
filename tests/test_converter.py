import pytest
from unittest.mock import patch
import sys
import os

# srcディレクトリをパスに追加してインポート可能にする
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from kindle_to_pdf.converter import KindleToPDF  # noqa: E402


@pytest.fixture
def mock_kindle_converter():
    with patch("kindle_to_pdf.converter.Path") as mock_path:
        # モックの設定
        mock_path.return_value.expanduser.return_value.exists.return_value = True
        converter = KindleToPDF(
            book_name="test_book", total_pages=10, page_turn_direction="left"
        )
        return converter


def test_initialization(mock_kindle_converter):
    assert mock_kindle_converter.book_name == "test_book"
    assert mock_kindle_converter.total_pages == 10
    assert mock_kindle_converter.page_turn_direction == "left"


@patch("subprocess.run")
def test_activate_kindle(mock_subprocess, mock_kindle_converter):
    mock_kindle_converter.activate_kindle()
    assert mock_subprocess.called
    args = mock_subprocess.call_args[0][0]
    assert "osascript" in args
    assert 'tell application "Kindle" to activate' in args[2]


@patch("subprocess.run")
def test_turn_page_left(mock_subprocess, mock_kindle_converter):
    # 左開き（→キー送信）
    mock_kindle_converter.page_turn_direction = "left"
    mock_kindle_converter.turn_page()

    args = mock_subprocess.call_args[0][0]
    assert "key code 124" in args[2]  # 124 is Right Arrow


@patch("subprocess.run")
def test_turn_page_right(mock_subprocess, mock_kindle_converter):
    # 右開き（←キー送信）
    mock_kindle_converter.page_turn_direction = "right"
    mock_kindle_converter.turn_page()

    args = mock_subprocess.call_args[0][0]
    assert "key code 123" in args[2]  # 123 is Left Arrow


def test_screenshot_without_window_id_fails_closed(mock_kindle_converter):
    with patch("subprocess.run") as run_subprocess:
        assert mock_kindle_converter.take_screenshot(1, window_id=None) is False
        run_subprocess.assert_not_called()


def test_missing_kindle_window_aborts_before_screenshot(mock_kindle_converter):
    with (
        patch.object(mock_kindle_converter, "activate_kindle"),
        patch.object(mock_kindle_converter, "resize_window"),
        patch.object(mock_kindle_converter, "get_window_id", return_value=None),
        patch.object(mock_kindle_converter, "take_screenshot") as screenshot,
        patch("kindle_to_pdf.converter.time.sleep"),
    ):
        assert mock_kindle_converter.capture_all_pages() == 0
        screenshot.assert_not_called()


def test_partial_capture_does_not_create_pdf(mock_kindle_converter):
    with (
        patch.object(mock_kindle_converter, "capture_all_pages", return_value=9),
        patch.object(mock_kindle_converter, "convert_to_pdf") as pdf,
    ):
        assert mock_kindle_converter.run() is None
        pdf.assert_not_called()


def test_web_server_binds_loopback_even_if_env_set_to_all_interfaces():
    from kindle_to_pdf import web

    with (
        patch.dict(os.environ, {"FLET_SERVER_IP": "0.0.0.0"}),
        patch.object(web.ft, "app") as app,
    ):
        web.run_web_app()
        assert os.environ["FLET_SERVER_IP"] == "127.0.0.1"
        app.assert_called_once()
