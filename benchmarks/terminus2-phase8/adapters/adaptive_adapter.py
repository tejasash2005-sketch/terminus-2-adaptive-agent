"""Phase 8 adaptive adapter: delegates to a reviewed adaptive Harbor runner.

The runner must explicitly declare the tested revision and the Phase 7 features
actually wired into the execution path. This adapter does not infer integration
from the existence of the standalone AutonomousAgent module.
"""

from __future__ import annotations
from typing import Any
from supervised_process_adapter import run_supervised


def run_task(task: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    result = run_supervised(task, context, "adaptive")
    required = ("agent_revision", "integration_mode", "enabled_capabilities")
    missing = [key for key in required if not result.get(key)]
    if missing:
        raise RuntimeError(
            "adaptive runner result missing integration provenance: "
            + ", ".join(missing)
        )
    if not isinstance(result["enabled_capabilities"], list) or not all(
        isinstance(x, str) for x in result["enabled_capabilities"]
    ):
        raise TypeError("enabled_capabilities must be a list of strings")
    result["adaptive_integration_provenance_validated"] = True
    return result
