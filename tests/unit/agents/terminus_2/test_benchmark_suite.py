import asyncio
import json

import pytest

from harbor.agents.terminus_2.benchmark_suite import (
    DEFAULT_CASES,
    BenchmarkCase,
    run_benchmark_cases,
    write_benchmark_report,
)


def test_default_suite_has_distinct_core_safety_and_execution_cases():
    assert len(DEFAULT_CASES) >= 5
    assert {c.category for c in DEFAULT_CASES} >= {
        "execution",
        "dependencies",
        "verification",
        "safety",
    }


def test_benchmark_report_summarizes_expected_outcomes():
    async def run():
        return await run_benchmark_cases(
            [
                BenchmarkCase("pass", "test", "ok", "works"),
                BenchmarkCase("fail", "test", "ok", "fails"),
            ],
            lambda case: {
                "terminal_reason": "ok" if case.case_id == "pass" else "wrong",
                "elapsed_seconds": 0.2,
            },
        )

    report = asyncio.run(run())
    assert report["summary"]["case_count"] == 2
    assert report["summary"]["passed"] == 1
    assert report["summary"]["pass_rate"] == 0.5
    assert report["limitations"]


def test_runner_errors_become_explicit_failed_cases():
    report = asyncio.run(
        run_benchmark_cases([BenchmarkCase("bad", "test", "ok", "bad")], lambda case: 4)
    )
    assert report["cases"][0]["observed_terminal_reason"] == "runner_error"
    assert report["summary"]["failed"] == 1


def test_report_write_is_parseable_and_atomic(tmp_path):
    path = tmp_path / "report.json"
    report = asyncio.run(run_benchmark_cases([], lambda case: {}))
    write_benchmark_report(report, path)
    assert json.loads(path.read_text())["summary"]["case_count"] == 0
    assert not path.with_suffix(".json.tmp").exists()


def test_default_regression_suite_executes_real_agent_loop():
    from harbor.agents.terminus_2.benchmark_suite import run_default_regression_suite

    report = asyncio.run(run_default_regression_suite())
    assert report["summary"]["case_count"] == len(DEFAULT_CASES)
    assert report["summary"]["passed"] == len(DEFAULT_CASES)
    assert report["summary"]["safety_gate_triggers"] >= 1
    assert all(case["details"] for case in report["cases"])


def test_repeated_campaign_reports_all_runs_and_latency_distribution():
    from harbor.agents.terminus_2.benchmark_suite import run_repeated_default_campaign

    report = asyncio.run(run_repeated_default_campaign(3))
    assert report["repetitions"] == 3
    assert report["total_case_runs"] == 3 * len(DEFAULT_CASES)
    assert report["summary"]["all_trials_passed"] is True
    assert len(report["trials"]) == 3
    for case in DEFAULT_CASES:
        metrics = report["per_case"][case.case_id]
        assert metrics["pass_count"] == 3
        assert (
            metrics["latency_seconds"]["min"]
            <= metrics["latency_seconds"]["median"]
            <= metrics["latency_seconds"]["max"]
        )
        assert (
            metrics["latency_seconds"]["p95_nearest_rank"]
            <= metrics["latency_seconds"]["max"]
        )
    assert "not a confidence interval" in report["measurement_notes"]["percentile"]


@pytest.mark.parametrize("repetitions", [0, -1, 101, True, 1.5])
def test_repeated_campaign_rejects_invalid_repetition_count(repetitions):
    from harbor.agents.terminus_2.benchmark_suite import run_repeated_default_campaign

    with pytest.raises(ValueError, match="repetitions"):
        asyncio.run(run_repeated_default_campaign(repetitions))
