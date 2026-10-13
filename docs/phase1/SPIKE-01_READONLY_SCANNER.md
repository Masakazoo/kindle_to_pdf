# SPIKE-01 — Kindle local metadata scanner (read-only prototype)

Status: **implementation prototype, NOT verified on a real Kindle account or Mac**.
Related: [Issue #4](https://github.com/Masakazoo/kindle_to_pdf/issues/4).

## Usage

On a Mac with Kindle for Mac installed:

```bash
uv run python -m kindle_to_pdf.library_scan
```

Optional local-only path:

```bash
uv run python -m kindle_to_pdf.library_scan --db "/path/to/BookData.sqlite"
```

**Default output contains only summary counts**, not titles or ASINs. Read-only by construction (SQLite `mode=ro` and `PRAGMA query_only = ON`). The actual BookData.sqlite is NOT copied, migrated, modified or committed.

Example (synthetic):

```json
{
  "book_candidates": 2,
  "book_candidates_with_asin": 1,
  "book_candidates_without_asin": 1,
  "dictionary_records": 1,
  "purchase_verification": "NOT_PERFORMED",
  "records_total": 3,
  "scan_complete": true,
  "source": "kindle_local_sqlite"
}
```

The prototype reads `ZBOOK` columns `Z_PK`, `ZDISPLAYTITLE`, `ZBOOKID`, plus optional `ZRAWISDICTIONARY`, `ZCONTENTTAGS`, `ZRAWBOOKTYPE`. It recognizes only a conservative known `ZBOOKID` pattern (`A:B0CG5853SR-0`). Unknown IDs stay unknown. Dictionaries are flagged; no record is assumed to be purchased.

### Unknowns / gates before production use

- No real Kindle application DB has been accessed in this investigation.
- Does the SQLite table include all purchases or only locally known/downloaded books?
- Is parsing ASIN from ZBOOKID sufficient for all content types and editions? (Probably not; compare with metadata inside `ZSYNCMETADATAATTRIBUTES` using a safe, compatible decoder after PoC.)
- Can Kindle Unlimited, Prime Reading, samples, and refunded items be distinguished by the available metadata? **No such evidence is used by this module.**
- Is the local DB's journal/WAL state readable without interfering with Kindle? Test on Mac; never modify Kindle's private DB.

### Acceptance

1. Synthetic schema tests pass on macOS CI and do not mutate source DB.
2. Run the command on the user's Mac and retain only anonymized counts.
3. Compare anonymized counts to manually observed Amazon purchased book inventory. Report source version, coverage %, ASIN detection rate and missing cases.
4. Do not mark Issue #4 GO until (2) and (3) have been tested.

External inspiration (not copied): [rok-git/listKindleBooks2](https://github.com/rok-git/listKindleBooks2).
