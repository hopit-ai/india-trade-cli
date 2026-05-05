"""Shared filesystem paths for Vibe Trading runtime data."""

from __future__ import annotations

import os
from pathlib import Path


def app_data_dir() -> Path:
    """
    Return the writable app data directory.

    Defaults to ~/.trading_platform for desktop/CLI compatibility. Tests,
    CI, and containers can override this with TRADING_PLATFORM_HOME.
    """
    override = os.environ.get("TRADING_PLATFORM_HOME") or os.environ.get("TRADING_PLATFORM_DATA")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".trading_platform"


def app_data_path(*parts: str) -> Path:
    """Return a path inside the writable app data directory."""
    return app_data_dir().joinpath(*parts)


def pdf_output_dir() -> Path:
    """Return the directory used for primary PDF downloads/exports."""
    override = os.environ.get("TRADING_PLATFORM_PDF_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / "Desktop"
