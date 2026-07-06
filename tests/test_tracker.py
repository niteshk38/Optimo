"""Tracker tests — use a temporary SQLite file, no network."""

import csv

import pytest

from jobagent.models import Job
from jobagent.tracker import Tracker


@pytest.fixture()
def tracker(tmp_path):
    t = Tracker(tmp_path / "test.db")
    yield t
    t.close()


def _job():
    return Job(title="Backend Engineer", company="Acme", url="http://a", source="test")


def test_save_and_list(tracker):
    tracker.save_job(_job())
    rows = tracker.list()
    assert len(rows) == 1
    assert rows[0]["company"] == "Acme"
    assert rows[0]["status"] == "saved"


def test_save_is_idempotent(tracker):
    tracker.save_job(_job())
    tracker.save_job(_job())  # same job id -> INSERT OR IGNORE
    assert len(tracker.list()) == 1


def test_status_transition(tracker):
    job = _job()
    tracker.save_job(job)
    assert tracker.set_status(job.id, "applied") is True
    assert tracker.list(status="applied")[0]["job_id"] == job.id


def test_invalid_status_rejected(tracker):
    job = _job()
    tracker.save_job(job)
    with pytest.raises(ValueError):
        tracker.set_status(job.id, "banana")


def test_export_csv(tracker, tmp_path):
    tracker.save_job(_job())
    out = tracker.export_csv(tmp_path / "out.csv")
    with out.open() as fh:
        rows = list(csv.DictReader(fh))
    assert rows[0]["title"] == "Backend Engineer"
