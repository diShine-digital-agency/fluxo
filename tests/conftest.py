"""Fluxo test configuration."""

from __future__ import annotations

from pathlib import Path

import pytest

DATA_DIR = Path(__file__).parent / "data"


@pytest.fixture
def sample_m3u_path() -> Path:
    return DATA_DIR / "sample.m3u"


@pytest.fixture
def sample_m3u_content(sample_m3u_path: Path) -> str:
    return sample_m3u_path.read_text(encoding="utf-8")


@pytest.fixture
def malformed_m3u_path() -> Path:
    return DATA_DIR / "sample_malformed.m3u"


@pytest.fixture
def malformed_m3u_content(malformed_m3u_path: Path) -> str:
    return malformed_m3u_path.read_text(encoding="utf-8")


@pytest.fixture
def sample_epg_path() -> Path:
    return DATA_DIR / "sample_epg.xml"


@pytest.fixture
def sample_epg_bytes(sample_epg_path: Path) -> bytes:
    return sample_epg_path.read_bytes()
