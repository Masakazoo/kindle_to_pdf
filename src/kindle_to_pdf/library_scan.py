"""Read-only Kindle for Mac *candidate* inventory scanner.

The Kindle application's private SQLite schema is undocumented and may change.
A visible row is never treated as proof of purchase. This module does not read,
copy, decrypt, or export the book content.
"""

from __future__ import annotations

import argparse
from contextlib import closing
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sqlite3
from typing import Literal


DEFAULT_BOOK_DB = (
    Path.home()
    / "Library/Containers/com.amazon.Lassen/Data/Library/Protected/BookData.sqlite"
)

# Observed in Kindle for Mac metadata as "A:B0CG5853SR-0".
# Unknown formats are deliberately left unidentified rather than guessed.
_BOOK_ID_PATTERN = re.compile(r"^[A-Z]:([A-Z0-9]{10})-[0-9]+$", re.IGNORECASE)
_REQUIRED_COLUMNS = frozenset({"Z_PK", "ZDISPLAYTITLE", "ZBOOKID"})
_OPTIONAL_COLUMNS = ("ZRAWISDICTIONARY", "ZCONTENTTAGS", "ZRAWBOOKTYPE")
_ALL_COLUMNS = ("Z_PK", "ZDISPLAYTITLE", "ZBOOKID", *_OPTIONAL_COLUMNS)


class UnsupportedKindleSchema(RuntimeError):
    """The local DB does not have the expected read-only metadata columns."""


@dataclass(frozen=True, slots=True)
class BookCandidate:
    local_row_id: int
    title: str
    asin: str | None
    content_tags: str | None
    book_type: int | None
    is_dictionary: bool

    # A local Kindle record or a purchase_date hint alone is NOT ownership proof.
    purchase_status: Literal["UNVERIFIED"] = "UNVERIFIED"


@dataclass(frozen=True, slots=True)
class LibraryScan:
    candidates: tuple[BookCandidate, ...]
    source_schema_columns: frozenset[str]

    @property
    def summary(self) -> dict[str, int | str | bool]:
        """Only aggregate counts; safe as default CLI output."""
        non_dict = [item for item in self.candidates if not item.is_dictionary]
        return {
            "source": "kindle_local_sqlite",
            "scan_complete": True,
            "records_total": len(self.candidates),
            "dictionary_records": len(self.candidates) - len(non_dict),
            "book_candidates": len(non_dict),
            "book_candidates_with_asin": sum(item.asin is not None for item in non_dict),
            "book_candidates_without_asin": sum(item.asin is None for item in non_dict),
            "purchase_verification": "NOT_PERFORMED",
        }


def parse_candidate_asin(raw_book_id: object) -> str | None:
    """Conservatively parse known Kindle ZBOOKID format, or return unknown."""
    if not isinstance(raw_book_id, str):
        return None
    match = _BOOK_ID_PATTERN.fullmatch(raw_book_id.strip())
    return match.group(1).upper() if match else None


def _is_dictionary(raw_flag: object, tags: object, book_type: object) -> bool:
    if raw_flag == 1:
        return True
    if isinstance(tags, str) and "DICT" in tags.upper().split(";"):
        return True
    return book_type == 16


def scan_library(db_path: str | Path = DEFAULT_BOOK_DB) -> LibraryScan:
    """Observe local Kindle metadata without modifying the source DB.

    Uses SQLite URI mode=ro plus PRAGMA query_only. This is a metadata
    observation, not a verified list of purchases. Never silently falls back
    to legacy XML or to direct examination of protected book files.
    """
    path = Path(db_path).expanduser().resolve(strict=True)
    uri = path.as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True, timeout=3.0)) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only = ON")
        conn.execute("BEGIN")

        info = conn.execute('PRAGMA table_info("ZBOOK")').fetchall()
        columns = frozenset(row["name"] for row in info)
        missing = sorted(_REQUIRED_COLUMNS - columns)
        if missing:
            raise UnsupportedKindleSchema(
                "ZBOOK schema not supported; missing metadata columns: "
                + ", ".join(missing)
            )

        projection = ", ".join(
            f'"{column}"' if column in columns else f'NULL AS "{column}"'
            for column in _ALL_COLUMNS
        )
        rows = conn.execute(
            f'SELECT {projection} FROM "ZBOOK" '
            'WHERE "ZDISPLAYTITLE" IS NOT NULL ORDER BY "Z_PK"'
        ).fetchall()

        candidates = []
        for row in rows:
            tags = row["ZCONTENTTAGS"]
            book_type = row["ZRAWBOOKTYPE"]
            candidates.append(
                BookCandidate(
                    local_row_id=row["Z_PK"],
                    title=row["ZDISPLAYTITLE"],
                    asin=parse_candidate_asin(row["ZBOOKID"]),
                    content_tags=tags if isinstance(tags, str) else None,
                    book_type=book_type if isinstance(book_type, int) else None,
                    is_dictionary=_is_dictionary(
                        row["ZRAWISDICTIONARY"], tags, book_type
                    ),
                )
            )
        return LibraryScan(
            candidates=tuple(candidates),
            source_schema_columns=columns,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read Kindle for Mac's local metadata database without changing it. "
            "Outputs counts only; does not verify purchases or download books."
        )
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_BOOK_DB,
        help="Path to Kindle for Mac's BookData.sqlite (read-only)",
    )
    args = parser.parse_args(argv)
    try:
        scan = scan_library(args.db)
    except (FileNotFoundError, PermissionError, UnsupportedKindleSchema, sqlite3.Error) as exc:
        # Errors intentionally omit local book titles, ASINs, and database paths.
        print(
            json.dumps(
                {"scan_complete": False, "error_type": type(exc).__name__},
                ensure_ascii=False,
            )
        )
        return 2

    print(json.dumps(scan.summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
