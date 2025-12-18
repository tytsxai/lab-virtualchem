"""Build/runtime metadata helpers.

This module provides a single place to read build information (timestamp, git
sha, build id) from environment variables so that startup logs and health
endpoints can report consistent metadata across entrypoints and packaged builds.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime

from src import __version__ as APP_VERSION


def _iso_from_epoch(value: str) -> str | None:
    """Convert an epoch seconds string to ISO-8601 UTC timestamp."""
    try:
        return datetime.fromtimestamp(int(value), tz=UTC).isoformat()
    except Exception:  # noqa: BLE001
        return None


def _read_build_time() -> str:
    """Read build timestamp from common CI/reproducible-build env vars."""
    explicit = (os.getenv("VCL_BUILD_TIME") or os.getenv("VCL_BUILD_TIMESTAMP") or "").strip()
    if explicit:
        return explicit

    sde = (os.getenv("SOURCE_DATE_EPOCH") or "").strip()
    if sde:
        parsed = _iso_from_epoch(sde)
        if parsed:
            return parsed
    return "unknown"


@dataclass(frozen=True)
class BuildInfo:
    """Normalized build metadata surfaced in logs and health probes."""

    version: str
    build_time: str
    build_sha: str
    build_id: str

    def as_dict(self) -> dict[str, str]:
        """Render metadata as a JSON-friendly dict."""
        return {
            "version": self.version,
            "build_time": self.build_time,
            "build_sha": self.build_sha,
            "build_id": self.build_id,
        }


def get_build_info() -> BuildInfo:
    """Return build metadata derived from environment variables."""
    build_sha = (
        (os.getenv("VCL_BUILD_SHA") or os.getenv("GIT_COMMIT") or os.getenv("GITHUB_SHA") or "")
        .strip()
        .lower()
    )
    build_id = (os.getenv("VCL_BUILD_ID") or os.getenv("GITHUB_RUN_ID") or "").strip()
    return BuildInfo(
        version=APP_VERSION,
        build_time=_read_build_time(),
        build_sha=build_sha or "unknown",
        build_id=build_id or "unknown",
    )


__all__ = ["BuildInfo", "get_build_info"]
