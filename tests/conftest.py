"""Shared fixtures. Every test runs with no network and no model."""

from __future__ import annotations

import socket
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SAMPLES = REPO / "samples"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Fail loudly if anything tries to open a socket."""

    def guard(*args, **kwargs):  # pragma: no cover
        raise RuntimeError("network access attempted during tests")

    monkeypatch.setattr(socket, "create_connection", guard)
    monkeypatch.setattr(socket.socket, "connect", guard)


@pytest.fixture(autouse=True)
def repo_cwd(monkeypatch):
    monkeypatch.chdir(REPO)


@pytest.fixture
def intake():
    from ttx.common import read_yaml

    return read_yaml(SAMPLES / "intake_valley_regional.yaml")


@pytest.fixture
def estate():
    from ttx.seed_engine import load_sample_estate

    return load_sample_estate(SAMPLES / "synthetic_estate.json")


@pytest.fixture
def sample_pack():
    from ttx.common import read_json

    return read_json(SAMPLES / "exercise_pack_sample.json")


@pytest.fixture
def org_plan():
    from ttx.common import read_json

    return read_json(SAMPLES / "org_plan_sample.json")
