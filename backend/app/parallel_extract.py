"""Parallel fan-out helpers for Component / Code layer extraction.

Context and Container stay single-pass. Component work is split per parent
container; Code work is split per parent component. Workers run in a thread
pool so deterministic AST work (and scoped LLM calls) overlap.
"""

from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")
R = TypeVar("R")

DEFAULT_MAX_WORKERS = 8


def max_workers(item_count: int) -> int:
    """Bound parallelism by work-item count and optional env override."""
    raw = os.getenv("C4_PARALLEL_WORKERS", "").strip()
    configured = DEFAULT_MAX_WORKERS
    if raw.isdigit():
        configured = max(1, int(raw))
    return max(1, min(configured, item_count, DEFAULT_MAX_WORKERS))


def map_parallel(
    fn: Callable[[T], R],
    items: list[T],
    *,
    label: str = "extract",
) -> list[R]:
    """Map ``fn`` over ``items``, preserving input order.

    Falls back to sequential execution when there is at most one item (or when
    ``C4_PARALLEL_WORKERS=1``) so tests and tiny repos stay simple.
    """
    if not items:
        return []
    workers = max_workers(len(items))
    if workers == 1 or len(items) == 1:
        return [fn(item) for item in items]

    logger.debug(
        "parallel %s: %d items with %d workers", label, len(items), workers
    )
    results: list[R | None] = [None] * len(items)
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix=f"c4-{label}") as pool:
        futures = {pool.submit(fn, item): idx for idx, item in enumerate(items)}
        for fut in as_completed(futures):
            idx = futures[fut]
            results[idx] = fut.result()
    return [results[i] for i in range(len(items))]  # type: ignore[misc]
