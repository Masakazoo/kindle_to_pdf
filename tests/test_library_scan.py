"""Synthetic-only tests for the Kindle for Mac metadata scanner."""

import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kindle_to_pdf.library_scan import (  # noqa: E402
    UnsupportedKindleSchema,
    main,
    parse_candidate_asin,
    scan_library,
)


def _create_db(path: Path, *, minimal: bool = False) -> Path:
    with sqlite3.connect(path) as conn:
        if minimal:
            conn.execute(
                'CREATE TABLE ZBOOK (Z_PK INTEGER PRIMARY KEY, '
                'ZDISPLAYTITLE TEXT, ZBOOKID TEXT)'
            )
            conn.execute(
                "INSERT INTO ZBOOK VALUES (1, 'A synthetic book', 'A:B0CG5853SR-0')"
            )
        else:
            conn.execute(
                'CREATE TABLE ZBOOK (Z_PK INTEGER PRIMARY KEY, '
                'ZDISPLAYTITLE TEXT, ZBOOKID TEXT, ZRAWISDICTIONARY INT, '
                'ZCONTENTTAGS TEXT, ZRAWBOOKTYPE INT)'
            )
            conn.executemany(
                "INSERT INTO ZBOOK VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (1, "Sample A", "A:B0CG5853SR-0", 0, "", 10),
                    (2, "Dictionary", "A:B0CG5853SR-0", 1, ";DICT;FREE_DICT", 16),
                    (3, "Unrecognized ID", "not-an-ASIN", 0, "", 10),
                    (4, None, "A:B0CG5853SR-0", 0, "", 10),
                ],
            )
    return path


def test_scan_candidates_never_prove_purchase(tmp_path: Path):
    db = _create_db(tmp_path / "BookData.sqlite")
    before = db.read_bytes()
    result = scan_library(db)
    assert db.read_bytes() == before
    assert len(result.candidates) == 3
    assert result.candidates[0].asin == "B0CG5853SR"
    assert all(item.purchase_status == "UNVERIFIED" for item in result.candidates)
    assert result.summary == {
        "source": "kindle_local_sqlite",
        "scan_complete": True,
        "records_total": 3,
        "dictionary_records": 1,
        "book_candidates": 2,
        "book_candidates_with_asin": 1,
        "book_candidates_without_asin": 1,
        "purchase_verification": "NOT_PERFORMED",
    }


def test_optional_columns_can_be_missing_and_uri_escapes_name(tmp_path: Path):
    db = _create_db(tmp_path / "kindle # 01.sqlite", minimal=True)
    result = scan_library(db)
    assert result.summary["book_candidates"] == 1
    assert result.candidates[0].book_type is None
    assert result.candidates[0].content_tags is None


def test_missing_schema_fails_explicitly(tmp_path: Path):
    path = tmp_path / "unknown.sqlite"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE OTHER (key TEXT)")
    with pytest.raises(UnsupportedKindleSchema, match="ZBOOK schema not supported"):
        scan_library(path)


def test_missing_database_does_not_create_file(tmp_path: Path):
    path = tmp_path / "missing.sqlite"
    with pytest.raises(FileNotFoundError):
        scan_library(path)
    assert not path.exists()


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("A:B0CG5853SR-0", "B0CG5853SR"),
        ("a:b0cg5853sr-42", "B0CG5853SR"),
        ("B0CG5853SR", None),
        ("A:not-an-asin-0", None),
        (None, None),
        (b"A:B0CG5853SR-0", None),
    ],
)
def test_asin_parser_is_conservative(value, expected):
    assert parse_candidate_asin(value) == expected


def test_cli_summary_only_no_sensitive_metadata(tmp_path: Path, capsys):
    db = _create_db(tmp_path / "BookData.sqlite")
    assert main(["--db", str(db)]) == 0
    out = capsys.readouterr().out
    assert "Sample A" not in out
    assert "B0CG5853SR" not in out
    assert '"purchase_verification": "NOT_PERFORMED"' in out


def test_cli_fails_closed_on_missing_db(tmp_path: Path, capsys):
    assert main(["--db", str(tmp_path / "missing.sqlite")]) == 2
    assert '"scan_complete": false' in capsys.readouterr().out
