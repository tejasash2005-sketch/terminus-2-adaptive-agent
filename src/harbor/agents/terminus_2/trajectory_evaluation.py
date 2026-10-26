"""Deterministic summaries for comparing baseline and adaptive agent runs.

Input is a JSON document containing either a list of run objects or an object
with a ``runs`` list. Each run may include ``task_success``, ``duration_sec``,
``cost_usd`` and ``recovery_records``. Missing metrics remain unknown; they are
never silently treated as zero or success.
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any


def _mean_known(runs: list[dict[str, Any]], key: str) -> float | None:
    values: list[float] = []
    for run in runs:
        value = run.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            values.append(float(value))
    return statistics.fmean(values) if values else None


def _summarize_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    task_results = [
        run["task_success"] for run in runs if isinstance(run.get("task_success"), bool)
    ]
    records: list[dict[str, Any]] = []
    for run in runs:
        raw_records = run.get("recovery_records")
        if not isinstance(raw_records, list):
            continue
        records.extend(record for record in raw_records if isinstance(record, dict))
    resolved = [
        record for record in records if isinstance(record.get("succeeded"), bool)
    ]
    cleared = sum(record["succeeded"] is True for record in resolved)
    failure_types: dict[str, int] = {}
    actions: dict[str, int] = {}
    for record in records:
        failure_type = record.get("failure_type", "unknown")
        action = record.get("action", "unknown")
        failure_types[failure_type] = failure_types.get(failure_type, 0) + 1
        actions[action] = actions.get(action, 0) + 1

    return {
        "run_count": len(runs),
        "task_success_observations": len(task_results),
        "task_success_rate": (
            sum(result is True for result in task_results) / len(task_results)
            if task_results
            else None
        ),
        "mean_duration_sec": _mean_known(runs, "duration_sec"),
        "mean_cost_usd": _mean_known(runs, "cost_usd"),
        "recovery_decisions": len(records),
        "resolved_recovery_outcomes": len(resolved),
        "unresolved_recovery_outcomes": len(records) - len(resolved),
        "failure_signal_clear_rate": cleared / len(resolved) if resolved else None,
        "failure_type_counts": dict(sorted(failure_types.items())),
        "action_counts": dict(sorted(actions.items())),
    }


def evaluate_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize run results overall and separately for each named variant."""
    overall = _summarize_runs(runs)
    groups: dict[str, list[dict[str, Any]]] = {}
    for run in runs:
        variant = run.get("variant")
        if isinstance(variant, str) and variant.strip():
            groups.setdefault(variant.strip(), []).append(run)
    overall["by_variant"] = {
        variant: _summarize_runs(group) for variant, group in sorted(groups.items())
    }
    overall["interpretation_note"] = (
        "Failure-signal clearance is not equivalent to task success. "
        "Compare task success, runtime and cost across matched baseline/adaptive runs."
    )
    return overall


def evaluate_file(path: str | Path) -> dict[str, Any]:
    """Load and evaluate a JSON run manifest."""
    with Path(path).open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, list):
        runs = payload
    elif isinstance(payload, dict) and isinstance(payload.get("runs"), list):
        runs = payload["runs"]
    else:
        raise ValueError(
            "Input must be a JSON list of runs or an object with a 'runs' list"
        )
    if not all(isinstance(run, dict) for run in runs):
        raise ValueError("Every run entry must be a JSON object")
    return evaluate_runs(runs)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results_json", help="JSON file containing run results")
    args = parser.parse_args()
    print(json.dumps(evaluate_file(args.results_json), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
