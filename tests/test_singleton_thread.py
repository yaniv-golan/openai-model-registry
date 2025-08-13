"""Thread-safety tests for the `ModelRegistry` singleton."""

from __future__ import annotations

import threading
from typing import List

from openai_model_registry import get_registry


def test_singleton_thread_safety() -> None:  # noqa: D401
    """Ensure multiple threads receive the exact same registry instance."""
    instance_ids: List[int] = []

    def _get_instance() -> None:  # noqa: WPS430
        instance_ids.append(id(get_registry()))

    threads = [threading.Thread(target=_get_instance) for _ in range(50)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()

    # All retrieved ids must be identical.
    assert len(set(instance_ids)) == 1, "ModelRegistry is not thread-safe singleton"
