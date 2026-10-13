"""Deterministic, side-effect-free decisions for manual Kindle/Drive sync.

This is a policy-only planner. It does not verify ownership, download content,
call Google APIs, or touch the local Kindle database. All inputs must be
observed and validated by adapters before they reach this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class Ownership(str, Enum):
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    EXCLUDED = "EXCLUDED"


class DownloadAvailability(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


class ArtifactStatus(str, Enum):
    NONE = "NONE"
    VALID_OFFICIAL = "VALID_OFFICIAL"
    INVALID = "INVALID"
    UNVERIFIED_ORIGIN = "UNVERIFIED_ORIGIN"


class DriveStatus(str, Enum):
    VERIFIED_MATCH = "VERIFIED_MATCH"
    CONFIRMED_ABSENT = "CONFIRMED_ABSENT"
    INACCESSIBLE = "INACCESSIBLE"
    CONFLICT = "CONFLICT"


class SourceHealth(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class SyncAction(str, Enum):
    SKIP = "SKIP"
    UPLOAD = "UPLOAD"
    ACQUIRE_OFFICIAL = "ACQUIRE_OFFICIAL"
    DEFER = "DEFER"
    REVIEW = "REVIEW"


class PlanReason(str, Enum):
    EXCLUDED = "EXCLUDED"
    PURCHASE_UNVERIFIED = "PURCHASE_UNVERIFIED"
    ALREADY_SYNCED = "ALREADY_SYNCED"
    DRIVE_ACCESS_UNKNOWN = "DRIVE_ACCESS_UNKNOWN"
    DRIVE_CONFLICT = "DRIVE_CONFLICT"
    DRIVE_SCAN_UNHEALTHY = "DRIVE_SCAN_UNHEALTHY"
    OFFICIAL_FILE_READY = "OFFICIAL_FILE_READY"
    ARTIFACT_INVALID = "ARTIFACT_INVALID"
    ARTIFACT_ORIGIN_UNVERIFIED = "ARTIFACT_ORIGIN_UNVERIFIED"
    AMAZON_SCAN_UNHEALTHY = "AMAZON_SCAN_UNHEALTHY"
    OFFICIAL_DOWNLOAD_AVAILABLE = "OFFICIAL_DOWNLOAD_AVAILABLE"
    OFFICIAL_DOWNLOAD_UNAVAILABLE = "OFFICIAL_DOWNLOAD_UNAVAILABLE"
    OFFICIAL_DOWNLOAD_UNKNOWN = "OFFICIAL_DOWNLOAD_UNKNOWN"


@dataclass(frozen=True, slots=True)
class SourceSnapshot:
    amazon: SourceHealth
    drive: SourceHealth


@dataclass(frozen=True, slots=True)
class BookSyncFacts:
    book_id: str
    ownership: Ownership
    download: DownloadAvailability
    artifact: ArtifactStatus
    drive: DriveStatus

    def __post_init__(self):
        if not self.book_id.strip():
            raise ValueError("book_id must be a stable nonempty identifier")


@dataclass(frozen=True, slots=True)
class PlannedBookAction:
    book_id: str
    action: SyncAction
    reason: PlanReason


def plan_book(book: BookSyncFacts, sources: SourceSnapshot) -> PlannedBookAction:
    """Plan a *non-destructive* action for one book.

    The only mutating output is UPLOAD to a previously verified-absent target.
    ACQUIRE_OFFICIAL is a conditional intent, not permission to automate a
    browser. Any non-approved official download adapter must refuse to act.
    """
    def result(action: SyncAction, reason: PlanReason) -> PlannedBookAction:
        return PlannedBookAction(book_id=book.book_id, action=action, reason=reason)

    if book.ownership is Ownership.EXCLUDED:
        return result(SyncAction.SKIP, PlanReason.EXCLUDED)
    if book.ownership is not Ownership.VERIFIED:
        return result(SyncAction.REVIEW, PlanReason.PURCHASE_UNVERIFIED)

    # VERIFIED_MATCH means a directly verified Drive file, not title similarity.
    if book.drive is DriveStatus.VERIFIED_MATCH:
        return result(SyncAction.SKIP, PlanReason.ALREADY_SYNCED)
    if book.drive is DriveStatus.CONFLICT:
        return result(SyncAction.REVIEW, PlanReason.DRIVE_CONFLICT)
    if book.drive is DriveStatus.INACCESSIBLE:
        return result(SyncAction.REVIEW, PlanReason.DRIVE_ACCESS_UNKNOWN)
    if sources.drive is not SourceHealth.COMPLETE:
        # Without a complete Drive observation, absence cannot be trusted.
        return result(SyncAction.REVIEW, PlanReason.DRIVE_SCAN_UNHEALTHY)

    if book.artifact is ArtifactStatus.INVALID:
        return result(SyncAction.REVIEW, PlanReason.ARTIFACT_INVALID)
    if book.artifact is ArtifactStatus.UNVERIFIED_ORIGIN:
        return result(SyncAction.REVIEW, PlanReason.ARTIFACT_ORIGIN_UNVERIFIED)

    # Previously obtained, validated official files can still be uploaded even
    # if Amazon's current download option is now unavailable.
    if book.artifact is ArtifactStatus.VALID_OFFICIAL:
        return result(SyncAction.UPLOAD, PlanReason.OFFICIAL_FILE_READY)

    if sources.amazon is not SourceHealth.COMPLETE:
        return result(SyncAction.REVIEW, PlanReason.AMAZON_SCAN_UNHEALTHY)
    if book.download is DownloadAvailability.AVAILABLE:
        return result(SyncAction.ACQUIRE_OFFICIAL, PlanReason.OFFICIAL_DOWNLOAD_AVAILABLE)
    if book.download is DownloadAvailability.UNAVAILABLE:
        return result(SyncAction.DEFER, PlanReason.OFFICIAL_DOWNLOAD_UNAVAILABLE)
    return result(SyncAction.REVIEW, PlanReason.OFFICIAL_DOWNLOAD_UNKNOWN)


def plan_sync(
    books: Iterable[BookSyncFacts], sources: SourceSnapshot
) -> tuple[PlannedBookAction, ...]:
    """Return stable, duplicate-free actions; no deletes or overwrites."""
    by_id: dict[str, BookSyncFacts] = {}
    for book in books:
        if book.book_id in by_id:
            raise ValueError("duplicate book_id in planning input")
        by_id[book.book_id] = book
    return tuple(
        plan_book(by_id[book_id], sources) for book_id in sorted(by_id)
    )
