"""Reproducible, offline benchmark harness for adaptive planning/execution.

Cases use injected deterministic models, executors, and verifiers. This suite is
for regression and behavior measurement; it does not claim external model quality
or real-world task success. Results include raw per-case outcomes and aggregate
success, latency, replanning, and safety-gate metrics.
"""

from __future__ import annotations

import asyncio
import json
import math
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, override


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    category: str
    expected_terminal_reason: str
    description: str


DEFAULT_CASES = (
    BenchmarkCase(
        "single_step_success",
        "execution",
        "objective_completed",
        "One task executes and independently verifies.",
    ),
    BenchmarkCase(
        "dependency_chain",
        "dependencies",
        "objective_completed",
        "A dependent task starts only after its prerequisite succeeds.",
    ),
    BenchmarkCase(
        "verification_rejection",
        "verification",
        "failed_tasks_remain",
        "Executor returns but verifier rejects the result.",
    ),
    BenchmarkCase(
        "high_risk_approval_gate",
        "safety",
        "blocked_tasks_remain",
        "High-risk work is blocked without an approval callback.",
    ),
    BenchmarkCase(
        "dependency_failure",
        "recovery",
        "failed_tasks_remain",
        "Failure must not allow dependent work to execute.",
    ),
    BenchmarkCase(
        "checkpoint_written",
        "persistence",
        "objective_completed",
        "Successful run writes a parseable state checkpoint.",
    ),
)


async def run_benchmark_cases(
    cases: Iterable[BenchmarkCase], runner: Callable[[BenchmarkCase], Any]
) -> dict[str, Any]:
    """Run supplied cases sequentially and summarize observed outcomes.

    ``runner`` may be synchronous or asynchronous and must return a mapping with
    ``terminal_reason`` and optional ``elapsed_seconds``, ``replan_count``,
    ``safety_gate_triggered``, and ``details`` fields.
    """
    results: list[dict[str, Any]] = []
    for case in cases:
        started = time.monotonic()
        try:
            value = runner(case)
            if asyncio.iscoroutine(value):
                value = await value
            if not isinstance(value, dict) or "terminal_reason" not in value:
                raise TypeError(
                    "benchmark runner must return a mapping with terminal_reason"
                )
            duration = float(value.get("elapsed_seconds", time.monotonic() - started))
            observed = str(value["terminal_reason"])
            results.append(
                {
                    "case_id": case.case_id,
                    "category": case.category,
                    "expected_terminal_reason": case.expected_terminal_reason,
                    "observed_terminal_reason": observed,
                    "passed": observed == case.expected_terminal_reason,
                    "elapsed_seconds": max(0.0, duration),
                    "replan_count": int(value.get("replan_count", 0)),
                    "safety_gate_triggered": bool(
                        value.get("safety_gate_triggered", False)
                    ),
                    "details": value.get("details", ""),
                }
            )
        except Exception as exc:
            results.append(
                {
                    "case_id": case.case_id,
                    "category": case.category,
                    "expected_terminal_reason": case.expected_terminal_reason,
                    "observed_terminal_reason": "runner_error",
                    "passed": False,
                    "elapsed_seconds": max(0.0, time.monotonic() - started),
                    "replan_count": 0,
                    "safety_gate_triggered": False,
                    "details": f"{type(exc).__name__}: {exc}",
                }
            )
    durations = [r["elapsed_seconds"] for r in results]
    count = len(results)
    return {
        "suite": "terminus2-autonomous-regression-v1",
        "cases": results,
        "summary": {
            "case_count": count,
            "passed": sum(r["passed"] for r in results),
            "failed": sum(not r["passed"] for r in results),
            "pass_rate": sum(r["passed"] for r in results) / count if count else 0.0,
            "mean_elapsed_seconds": statistics.fmean(durations) if durations else 0.0,
            "median_elapsed_seconds": statistics.median(durations)
            if durations
            else 0.0,
            "total_replans": sum(r["replan_count"] for r in results),
            "safety_gate_triggers": sum(r["safety_gate_triggered"] for r in results),
        },
        "limitations": "Offline/injected regression evidence only; not a real-model benchmark or proof of real-world task success.",
    }


def write_benchmark_report(report: dict[str, Any], path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(target.suffix + ".tmp")
    temp.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    temp.replace(target)


async def run_default_regression_suite() -> dict[str, Any]:
    """Execute the bundled offline cases against the real autonomous loop.

    A deterministic ``BaseLLM`` test double emits each case's plan. The executor
    is a local in-memory stub, not a shell/tool integration; this measures loop
    behavior and safety gates only. Use real configured models and approved
    environments separately for empirical model/agent performance studies.
    """
    import json as _json
    import tempfile
    from pathlib import Path as _Path

    from harbor.agents.terminus_2.autonomous import (
        AutonomousAgent,
        AutonomousConfig,
        ExecutionResult,
    )
    from harbor.agents.terminus_2.task_planner import TaskStep
    from harbor.llms.base import BaseLLM, LLMResponse

    class CaseModel(BaseLLM):
        def __init__(self, content: str):
            self.content = content

        @override
        async def call(self, prompt: str, **kwargs: Any) -> LLMResponse:
            return LLMResponse(content=self.content)

        @override
        def get_model_context_limit(self) -> int:
            return 8192

        @override
        def get_model_output_limit(self) -> int | None:
            return 2048

    def make_plan(case_id: str) -> str:
        def step(step_id: str, **kwargs):
            return {
                "step_id": step_id,
                "title": step_id,
                "description": f"Test fixture: {step_id}",
                **kwargs,
            }

        if case_id == "dependency_chain":
            steps = [step("first"), step("second", depends_on=["first"])]
        elif case_id == "verification_rejection":
            steps = [step("verify-fail")]
        elif case_id == "high_risk_approval_gate":
            steps = [step("sensitive", risk="high")]
        elif case_id == "dependency_failure":
            steps = [step("fail"), step("dependent", depends_on=["fail"])]
        else:
            steps = [step("single")]
        return _json.dumps({"task": case_id, "steps": steps})

    async def execute_case(case: BenchmarkCase) -> dict[str, Any]:
        calls: list[str] = []

        async def executor(
            step: TaskStep, prior_outputs: Mapping[str, Mapping[str, object]]
        ) -> ExecutionResult:
            calls.append(step.step_id)
            if case.case_id == "dependency_failure" and step.step_id == "fail":
                raise RuntimeError("fixture failure")
            return ExecutionResult(
                {"verified": True, "step": step.step_id}, "in-memory fixture output"
            )

        def verifier(step, result):
            return (
                case.case_id != "verification_rejection"
                and result.output.get("verified") is True
            )

        checkpoint = None
        if case.case_id == "checkpoint_written":
            tmp = tempfile.TemporaryDirectory(prefix="harbor-benchmark-")
            checkpoint = str(_Path(tmp.name) / "checkpoint.json")
        else:
            tmp = None
        agent = AutonomousAgent(
            CaseModel(make_plan(case.case_id)),
            executor,
            verifier,
            config=AutonomousConfig(max_replans=0, checkpoint_path=checkpoint),
        )
        started = time.monotonic()
        try:
            report = await agent.run(case.case_id)
            safety = any(
                e.event in {"approval_required", "approval_denied"}
                for e in report.events
            )
            details = f"executed={calls}; statuses=" + ",".join(
                f"{s.step_id}:{s.status.value}" for s in report.plan.steps
            )
            if checkpoint and _Path(checkpoint).exists():
                details += "; checkpoint=written"
            return {
                "terminal_reason": report.terminal_reason,
                "elapsed_seconds": max(0.0, time.monotonic() - started),
                "replan_count": report.replan_count,
                "safety_gate_triggered": safety,
                "details": details,
            }
        finally:
            if tmp:
                tmp.cleanup()

    return await run_benchmark_cases(DEFAULT_CASES, execute_case)


async def run_repeated_default_campaign(repetitions: int = 5) -> dict[str, Any]:
    """Run the deterministic regression suite repeatedly and report stability.

    This campaign is intended to expose flaky behavior and timing variance in
    the local loop. It is not an estimate of external-model task success. Each
    repetition creates fresh fixtures and executes every case independently.
    """
    if (
        isinstance(repetitions, bool)
        or not isinstance(repetitions, int)
        or repetitions < 1
        or repetitions > 100
    ):
        raise ValueError("repetitions must be an integer from 1 through 100")
    trials: list[dict[str, Any]] = []
    for index in range(repetitions):
        report = await run_default_regression_suite()
        trials.append(
            {
                "repetition": index + 1,
                "summary": report["summary"],
                "cases": report["cases"],
            }
        )

    durations_by_case: dict[str, list[float]] = {
        case.case_id: [] for case in DEFAULT_CASES
    }
    pass_counts: dict[str, int] = {case.case_id: 0 for case in DEFAULT_CASES}
    for trial in trials:
        for result in trial["cases"]:
            case_id = result["case_id"]
            durations_by_case[case_id].append(float(result["elapsed_seconds"]))
            pass_counts[case_id] += int(bool(result["passed"]))

    def percentile(values: list[float], fraction: float) -> float:
        ordered = sorted(values)
        if not ordered:
            return 0.0
        # Nearest-rank percentile, documented to avoid interpolation ambiguity.
        index = max(0, min(len(ordered) - 1, math.ceil(fraction * len(ordered)) - 1))
        return ordered[index]

    per_case = {}
    for case in DEFAULT_CASES:
        values = durations_by_case[case.case_id]
        per_case[case.case_id] = {
            "pass_count": pass_counts[case.case_id],
            "repetitions": repetitions,
            "pass_rate": pass_counts[case.case_id] / repetitions,
            "latency_seconds": {
                "min": min(values),
                "median": statistics.median(values),
                "mean": statistics.fmean(values),
                "p95_nearest_rank": percentile(values, 0.95),
                "max": max(values),
            },
        }
    all_rates = [trial["summary"]["pass_rate"] for trial in trials]
    return {
        "campaign": "terminus2-phase7-repeatability-v1",
        "repetitions": repetitions,
        "case_count_per_repetition": len(DEFAULT_CASES),
        "total_case_runs": repetitions * len(DEFAULT_CASES),
        "summary": {
            "all_trials_passed": all(rate == 1.0 for rate in all_rates),
            "mean_trial_pass_rate": statistics.fmean(all_rates),
            "minimum_trial_pass_rate": min(all_rates),
            "maximum_trial_pass_rate": max(all_rates),
        },
        "per_case": per_case,
        "trials": trials,
        "measurement_notes": {
            "latency": "Wall-clock time measured locally per synthetic case; includes Python/runtime scheduling noise.",
            "percentile": "p95 uses nearest-rank selection; small sample sizes are coarse and not a confidence interval.",
            "scope": "Offline deterministic model/executor fixtures only; no external model quality or real-world success claim.",
        },
    }
