import json

import pytest

from harbor.agents.terminus_2.trajectory_evaluation import evaluate_file, evaluate_runs


def test_evaluator_distinguishes_task_success_from_failure_signal_clearance():
    result = evaluate_runs(
        [
            {
                "task_success": True,
                "duration_sec": 10,
                "cost_usd": 0.25,
                "recovery_records": [
                    {
                        "failure_type": "command_timeout",
                        "action": "inspect_terminal_state",
                        "succeeded": True,
                    }
                ],
            },
            {
                "task_success": False,
                "duration_sec": 20,
                "cost_usd": 0.5,
                "recovery_records": [
                    {
                        "failure_type": "command_timeout",
                        "action": "inspect_terminal_state",
                        "succeeded": None,
                    }
                ],
            },
        ]
    )
    assert result["task_success_rate"] == 0.5
    assert result["mean_duration_sec"] == 15
    assert result["mean_cost_usd"] == 0.375
    assert result["failure_signal_clear_rate"] == 1.0
    assert result["unresolved_recovery_outcomes"] == 1


def test_evaluator_keeps_missing_metrics_unknown():
    result = evaluate_runs([{}])
    assert result["task_success_rate"] is None
    assert result["mean_duration_sec"] is None
    assert result["mean_cost_usd"] is None
    assert result["failure_signal_clear_rate"] is None


def test_evaluator_reads_json_run_manifest(tmp_path):
    path = tmp_path / "runs.json"
    path.write_text(json.dumps({"runs": [{"task_success": True}]}), encoding="utf-8")
    assert evaluate_file(path)["task_success_rate"] == 1.0


def test_evaluator_rejects_invalid_manifest(tmp_path):
    path = tmp_path / "runs.json"
    path.write_text('{"results": []}', encoding="utf-8")
    with pytest.raises(ValueError, match="runs"):
        evaluate_file(path)


def test_evaluator_ignores_non_list_recovery_records():
    result = evaluate_runs([{"recovery_records": None}])
    assert result["recovery_decisions"] == 0
    assert result["failure_signal_clear_rate"] is None


def test_evaluator_reports_baseline_and_adaptive_variants_separately():
    result = evaluate_runs(
        [
            {"variant": "baseline", "task_success": False, "duration_sec": 20},
            {"variant": "adaptive", "task_success": True, "duration_sec": 15},
        ]
    )
    assert result["by_variant"]["baseline"]["task_success_rate"] == 0.0
    assert result["by_variant"]["adaptive"]["task_success_rate"] == 1.0
    assert result["by_variant"]["adaptive"]["mean_duration_sec"] == 15.0
