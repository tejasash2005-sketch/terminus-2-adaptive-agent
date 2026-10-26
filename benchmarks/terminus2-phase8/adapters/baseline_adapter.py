"""Phase 8 baseline adapter: delegates to an operator-configured Harbor runner."""

from __future__ import annotations
from typing import Any
from supervised_process_adapter import run_supervised


def run_task(task: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    return run_supervised(task, context, "baseline")
