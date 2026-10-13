"""Deterministic no-network tests for the sync policy."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kindle_to_pdf.sync_plan import (  # noqa: E402
    ArtifactStatus,
    BookSyncFacts,
    DownloadAvailability,
    DriveStatus,
    Ownership,
    PlanReason,
    SourceHealth,
    SourceSnapshot,
    SyncAction,
    plan_book,
    plan_sync,
)


OK = SourceSnapshot(amazon=SourceHealth.COMPLETE, drive=SourceHealth.COMPLETE)


def facts(
    book_id="test-book",
    ownership=Ownership.VERIFIED,
    download=DownloadAvailability.AVAILABLE,
    artifact=ArtifactStatus.NONE,
    drive=DriveStatus.CONFIRMED_ABSENT,
):
    return BookSyncFacts(
        book_id=book_id,
        ownership=ownership,
        download=download,
        artifact=artifact,
        drive=drive,
    )


@pytest.mark.parametrize(
    ("kwargs", "action", "reason"),
    [
        ({"ownership": Ownership.UNVERIFIED}, SyncAction.REVIEW, PlanReason.PURCHASE_UNVERIFIED),
        ({"ownership": Ownership.EXCLUDED}, SyncAction.SKIP, PlanReason.EXCLUDED),
        ({"drive": DriveStatus.VERIFIED_MATCH}, SyncAction.SKIP, PlanReason.ALREADY_SYNCED),
        ({"drive": DriveStatus.INACCESSIBLE}, SyncAction.REVIEW, PlanReason.DRIVE_ACCESS_UNKNOWN),
        ({"drive": DriveStatus.CONFLICT}, SyncAction.REVIEW, PlanReason.DRIVE_CONFLICT),
        ({"artifact": ArtifactStatus.VALID_OFFICIAL}, SyncAction.UPLOAD, PlanReason.OFFICIAL_FILE_READY),
        ({"artifact": ArtifactStatus.INVALID}, SyncAction.REVIEW, PlanReason.ARTIFACT_INVALID),
        ({"artifact": ArtifactStatus.UNVERIFIED_ORIGIN}, SyncAction.REVIEW, PlanReason.ARTIFACT_ORIGIN_UNVERIFIED),
        ({}, SyncAction.ACQUIRE_OFFICIAL, PlanReason.OFFICIAL_DOWNLOAD_AVAILABLE),
        ({"download": DownloadAvailability.UNAVAILABLE}, SyncAction.DEFER, PlanReason.OFFICIAL_DOWNLOAD_UNAVAILABLE),
        ({"download": DownloadAvailability.UNKNOWN}, SyncAction.REVIEW, PlanReason.OFFICIAL_DOWNLOAD_UNKNOWN),
    ],
)
def test_policy_branches(kwargs, action, reason):
    decision = plan_book(facts(**kwargs), OK)
    assert decision.action is action
    assert decision.reason is reason


def test_partial_drive_listing_cannot_prove_absence():
    sources = SourceSnapshot(amazon=SourceHealth.COMPLETE, drive=SourceHealth.PARTIAL)
    assert plan_book(facts(artifact=ArtifactStatus.VALID_OFFICIAL), sources).action is SyncAction.REVIEW
    assert plan_book(facts(), sources).reason is PlanReason.DRIVE_SCAN_UNHEALTHY


def test_failed_amazon_source_blocks_new_download():
    sources = SourceSnapshot(amazon=SourceHealth.FAILED, drive=SourceHealth.COMPLETE)
    decision = plan_book(facts(), sources)
    assert decision.action is SyncAction.REVIEW
    assert decision.reason is PlanReason.AMAZON_SCAN_UNHEALTHY


def test_legitimate_previous_official_file_may_upload_if_current_download_is_unavailable():
    decision = plan_book(
        facts(artifact=ArtifactStatus.VALID_OFFICIAL, download=DownloadAvailability.UNAVAILABLE),
        OK,
    )
    assert decision.action is SyncAction.UPLOAD


def test_source_failure_does_not_invalidate_directly_verified_drive_match():
    sources = SourceSnapshot(amazon=SourceHealth.FAILED, drive=SourceHealth.PARTIAL)
    assert plan_book(facts(drive=DriveStatus.VERIFIED_MATCH), sources).action is SyncAction.SKIP


def test_stable_order_and_no_duplicate_actions():
    result = plan_sync([facts("z"), facts("a"), facts("m")], OK)
    assert [item.book_id for item in result] == ["a", "m", "z"]


def test_duplicate_book_identity_rejected():
    with pytest.raises(ValueError, match="duplicate book_id"):
        plan_sync([facts("same"), facts("same")], OK)


def test_empty_book_id_rejected():
    with pytest.raises(ValueError, match="book_id"):
        facts(book_id="   ")


def test_no_destructive_actions_exist():
    assert set(SyncAction) == {
        SyncAction.SKIP,
        SyncAction.UPLOAD,
        SyncAction.ACQUIRE_OFFICIAL,
        SyncAction.DEFER,
        SyncAction.REVIEW,
    }
