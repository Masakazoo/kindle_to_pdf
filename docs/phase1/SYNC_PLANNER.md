# Pure sync planner — domain prototype

Related design: docs/phase0/ARCHITECTURE.md, DATA_MODEL.md, TEST_STRATEGY.md.

This module accepts only pre-verified facts and returns immutable decisions.
It **does not** contact Amazon or Google, scan Kindle data, or touch PDF files.

## Inputs
- Book identity (internal book_id)
- Purchase ownership: VERIFIED / UNVERIFIED / EXCLUDED
- Download option: AVAILABLE / UNAVAILABLE / UNKNOWN
- Local artifact: NONE / VALID_OFFICIAL / INVALID / UNVERIFIED_ORIGIN
- Drive object: VERIFIED_MATCH / CONFIRMED_ABSENT / INACCESSIBLE / CONFLICT
- Source health: COMPLETE / PARTIAL / FAILED, tracked separately for Amazon and Drive

## Outputs
- SKIP: verified remote match or explicit exclusion
- REVIEW: ambiguous purchase, inaccessible Drive, conflicts, partial source, invalid provenance
- UPLOAD: local official verified artifact and Drive confidently absent
- ACQUIRE_OFFICIAL: verified purchase, official DL available, no verified file, and healthy observations
- DEFER: verified purchase, official download unavailable and no previously obtained valid file

No DELETE or OVERWRITE action exists. The domain decision `ACQUIRE_OFFICIAL`
is **not authorization** to scrape Amazon; the adapter has a separate security
and policy gate in SPIKE-03.

If source listing is partial, lack of a file is not trusted. Same title does not
make two files identical. Confirmed remote matches must be verified by checksum
or equivalent independent content validation.

## How to test on Linux without Quartz/Flet

```bash
python -m pytest tests/test_sync_plan.py tests/test_library_scan.py
```

Production integration remains gated on Phase 1 field trials, SQLite migration
design, and Google Drive protocol tests. This PR does not change the Flet UI.
