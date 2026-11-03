"""In-process cancellation flags for long-running C4 analysis jobs.

The UI sends a ``job_id`` with ``POST /api/c4/model`` and can stop the run via
``POST /api/c4/cancel``. Specialists check the flag between layers (and at other
safe yield points) and raise ``AnalysisCancelled``.
"""

from __future__ import annotations

import threading
from typing import Optional

_lock = threading.Lock()
_jobs: dict[str, threading.Event] = {}


class AnalysisCancelled(Exception):
    """Raised when the user stops an in-flight analysis job."""

    def __init__(self, job_id: str | None = None) -> None:
        self.job_id = job_id or ""
        super().__init__(
            f"Analysis cancelled by user{f' (job {self.job_id})' if self.job_id else ''}."
        )


def begin_job(job_id: str) -> None:
    if not job_id:
        return
    with _lock:
        _jobs[job_id] = threading.Event()


def cancel_job(job_id: str) -> bool:
    """Signal cancel. Returns True if a running job was found."""
    if not job_id:
        return False
    with _lock:
        event = _jobs.get(job_id)
        if event is None:
            return False
        event.set()
        return True


def is_cancelled(job_id: Optional[str]) -> bool:
    if not job_id:
        return False
    with _lock:
        event = _jobs.get(job_id)
        return bool(event and event.is_set())


def check_cancelled(job_id: Optional[str]) -> None:
    if is_cancelled(job_id):
        raise AnalysisCancelled(job_id)


def end_job(job_id: Optional[str]) -> None:
    if not job_id:
        return
    with _lock:
        _jobs.pop(job_id, None)
