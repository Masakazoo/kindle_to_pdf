import pytest
from unittest.mock import MagicMock, patch
import sys
import os

# srcディレクトリをパスに追加してインポート可能にする
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from kindle_to_pdf.converter import KindleToPDF

@pytest.fixture
def mock_kindle_converter():
    with patch("kindle_to_pdf.converter.Path") as mock_path:
        # モックの設定
        mock_path.return_value.expanduser.return_value.exists.return_value = True
        converter = KindleToPDF(book_name="test_book", total_pages=10, page_turn_direction='left')
        return converter

def test_initialization(mock_kindle_converter):
    assert mock_kindle_converter.book_name == "test_book"
    assert mock_kindle_converter.total_pages == 10
    assert mock_kindle_converter.page_turn_direction == 'left'

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
    mock_kindle_converter.page_turn_direction = 'left'
    mock_kindle_converter.turn_page()
    
    args = mock_subprocess.call_args[0][0]
    assert "key code 124" in args[2] # 124 is Right Arrow

@patch("subprocess.run")
def test_turn_page_right(mock_subprocess, mock_kindle_converter):
    # 右開き（←キー送信）
    mock_kindle_converter.page_turn_direction = 'right'
    mock_kindle_converter.turn_page()
    
    args = mock_subprocess.call_args[0][0]
    assert "key code 123" in args[2] # 123 is Left Arrow
