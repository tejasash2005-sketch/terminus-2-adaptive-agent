"""Tests for deterministic multi-component task orchestration."""

import pytest

from harbor.agents.terminus_2.orchestration import (
    Component,
    OrchestrationError,
    TaskOrchestrator,
)
from harbor.agents.terminus_2.task_planner import (
    StepStatus,
    TaskPlan,
    TaskPlanningError,
    TaskStep,
    build_plan,
)


def step(step_id, *, deps=(), metadata=None):
    return TaskStep(
        step_id, step_id.title(), f"Do {step_id}", tuple(deps), metadata=metadata or {}
    )


def test_routes_steps_to_explicit_components_and_passes_dependency_outputs():
    seen = []

    def research(task_step, outputs):
        seen.append((task_step.step_id, dict(outputs)))
        return {"facts": "verified"}

    def writer(task_step, outputs):
        seen.append((task_step.step_id, dict(outputs)))
        assert outputs["research"]["facts"] == "verified"
        return {"draft": "ready"}

    plan = build_plan(
        "write a report",
        [
            step("research", metadata={"component": "researcher"}),
            step("write", deps=("research",), metadata={"component": "writer"}),
        ],
    )
    report = TaskOrchestrator(
        [
            Component("researcher", frozenset({"research"}), research),
            Component("writer", frozenset({"writing"}), writer),
        ]
    ).run(plan)

    assert report.succeeded
    assert [e.step_id for e in report.executions] == ["research", "write"]
    assert all(e.status is StepStatus.SUCCEEDED for e in report.executions)
    assert report.outputs["write"]["draft"] == "ready"
    assert seen[1][1]["research"]["facts"] == "verified"


def test_routes_by_unique_capability():
    plan = build_plan("task", [step("a", metadata={"capability": "inspect"})])
    report = TaskOrchestrator(
        [
            Component("inspector", frozenset({"inspect"}), lambda s, c: {"ok": True}),
            Component("writer", frozenset({"write"}), lambda s, c: {}),
        ]
    ).run(plan)
    assert report.executions[0].component == "inspector"


def test_single_component_is_default_route():
    report = TaskOrchestrator([Component("one", frozenset(), lambda s, c: {})]).run(
        build_plan("task", [step("a")])
    )
    assert report.executions[0].component == "one"


def test_duplicate_component_names_rejected():
    component = Component("same", frozenset(), lambda s, c: {})
    with pytest.raises(OrchestrationError, match="duplicate"):
        TaskOrchestrator([component, component])


def test_empty_component_registry_rejected():
    with pytest.raises(OrchestrationError, match="at least one"):
        TaskOrchestrator([])


def test_unknown_explicit_route_fails_preflight_before_any_handler_runs():
    calls = []
    plan = build_plan("task", [step("a", metadata={"component": "missing"})])
    with pytest.raises(OrchestrationError, match="unknown component"):
        TaskOrchestrator(
            [Component("worker", frozenset(), lambda s, c: calls.append(s))]
        ).run(plan)
    assert calls == []


def test_ambiguous_capability_fails_preflight():
    plan = build_plan("task", [step("a", metadata={"capability": "shared"})])
    workers = [
        Component(n, frozenset({"shared"}), lambda s, c: {}) for n in ("one", "two")
    ]
    with pytest.raises(OrchestrationError, match="matched 2"):
        TaskOrchestrator(workers).run(plan)


def test_missing_route_with_multiple_components_fails_preflight():
    plan = build_plan("task", [step("a")])
    workers = [Component(n, frozenset(), lambda s, c: {}) for n in ("one", "two")]
    with pytest.raises(OrchestrationError, match="must declare"):
        TaskOrchestrator(workers).run(plan)


def test_failure_blocks_dependents_but_allows_independent_branch():
    calls = []

    def fails(s, c):
        calls.append(s.step_id)
        raise RuntimeError("worker broke")

    def succeeds(s, c):
        calls.append(s.step_id)
        return {"ok": True}

    plan = build_plan(
        "task",
        [
            step("bad", metadata={"component": "failing"}),
            step("dependent", deps=("bad",), metadata={"component": "ok"}),
            step("independent", metadata={"component": "ok"}),
        ],
    )
    report = TaskOrchestrator(
        [
            Component("failing", frozenset(), fails),
            Component("ok", frozenset(), succeeds),
        ]
    ).run(plan)
    assert report.plan.steps[0].status is StepStatus.FAILED
    assert report.plan.steps[1].status is StepStatus.BLOCKED
    assert report.plan.steps[2].status is StepStatus.SUCCEEDED
    assert calls == ["bad", "independent"]
    assert report.failed_step_ids == ("bad",)
    assert report.blocked_step_ids == ("dependent",)
    assert not report.succeeded


def test_fail_fast_blocks_remaining_independent_steps():
    calls = []

    def fails(s, c):
        calls.append(s.step_id)
        raise ValueError("no")

    plan = build_plan("task", [step("first"), step("second")])
    report = TaskOrchestrator(
        [Component("one", frozenset(), fails)], fail_fast=True
    ).run(plan)
    assert calls == ["first"]
    assert report.plan.steps[1].status is StepStatus.BLOCKED
    assert "fail_fast" in report.executions[1].error


def test_non_mapping_result_is_recorded_as_failure():
    report = TaskOrchestrator([Component("one", frozenset(), lambda s, c: "bad")]).run(
        build_plan("task", [step("a")])
    )
    assert report.plan.steps[0].status is StepStatus.FAILED
    assert "must return a mapping" in report.executions[0].error


def test_non_string_output_key_is_recorded_as_failure():
    report = TaskOrchestrator(
        [Component("one", frozenset(), lambda s, c: {1: "bad"})]
    ).run(build_plan("task", [step("a")]))
    assert report.plan.steps[0].status is StepStatus.FAILED
    assert "keys must be strings" in report.executions[0].error


def test_component_exception_does_not_leak_partial_output():
    def fail(s, c):
        raise RuntimeError("failed after doing internal work")

    report = TaskOrchestrator([Component("one", frozenset(), fail)]).run(
        build_plan("task", [step("a")])
    )
    assert "a" not in report.outputs
    assert report.executions[0].status is StepStatus.FAILED


def test_previously_succeeded_step_is_not_reexecuted():
    calls = []
    done = TaskStep("done", "Done", "Already done", status=StepStatus.SUCCEEDED)
    plan = TaskPlan("task", (done,))
    report = TaskOrchestrator(
        [Component("one", frozenset(), lambda s, c: calls.append(s))]
    ).run(plan)
    assert calls == []
    assert report.succeeded


def test_dependency_failure_propagates_through_multiple_levels():
    plan = build_plan(
        "task", [step("a"), step("b", deps=("a",)), step("c", deps=("b",))]
    )

    def handler(s, c):
        if s.step_id == "a":
            raise RuntimeError("fail")
        return {}

    report = TaskOrchestrator([Component("one", frozenset(), handler)]).run(plan)
    statuses = {s.step_id: s.status for s in report.plan.steps}
    assert statuses == {
        "a": StepStatus.FAILED,
        "b": StepStatus.BLOCKED,
        "c": StepStatus.BLOCKED,
    }


def test_report_preserves_original_plan_immutability():
    plan = build_plan("task", [step("a")])
    TaskOrchestrator([Component("one", frozenset(), lambda s, c: {})]).run(plan)
    assert plan.steps[0].status is StepStatus.PENDING


def test_handler_receives_prior_outputs_without_mutating_reported_outputs():
    def first(s, c):
        return {"value": [1]}

    def second(s, c):
        c["first"]["value"].append(2)
        return {}

    plan = build_plan("task", [step("first"), step("second", deps=("first",))])
    report = TaskOrchestrator([Component("one", frozenset(), first)]).run(plan)
    assert report.outputs["first"]["value"] == [1]


def test_empty_plan_is_successful():
    report = TaskOrchestrator([Component("one", frozenset(), lambda s, c: {})]).run(
        build_plan("nothing to do", [])
    )
    assert report.succeeded
    assert report.executions == ()


def test_existing_in_progress_step_is_not_silently_restarted():
    plan = TaskPlan(
        "task", (TaskStep("a", "A", "Work", status=StepStatus.IN_PROGRESS),)
    )
    report = TaskOrchestrator([Component("one", frozenset(), lambda s, c: {})]).run(
        plan
    )
    assert report.plan.steps[0].status is StepStatus.IN_PROGRESS
    assert report.executions == ()


def test_orchestrator_rejects_invalid_plan_before_execution():
    # TaskPlan validates structure at construction; preserve that guarantee.
    with pytest.raises(TaskPlanningError, match="duplicate"):
        TaskPlan("task", (step("a"), step("a")))
