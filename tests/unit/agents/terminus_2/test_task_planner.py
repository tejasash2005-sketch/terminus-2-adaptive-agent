import pytest

from harbor.agents.terminus_2.task_planner import (
    StepStatus,
    TaskPlanningError,
    TaskStep,
    build_plan,
    decompose_task,
    plan_from_dict,
    replan_after_failure,
    topological_order,
    transition_step,
)


def step(step_id, *, depends_on=(), title=None):
    return TaskStep(
        step_id=step_id,
        title=title or step_id.title(),
        description=f"Perform {step_id}",
        depends_on=tuple(depends_on),
        success_criteria=(f"{step_id} verified",),
    )


def test_topological_order_respects_dependencies_and_is_stable():
    plan = build_plan(
        "release", [step("test", depends_on=("build",)), step("build"), step("docs")]
    )
    assert [item.step_id for item in plan.ordered_steps()] == ["build", "docs", "test"]


def test_ready_steps_only_returns_steps_with_completed_dependencies():
    plan = build_plan(
        "release",
        [
            step("build"),
            step("test", depends_on=("build",)),
            step("ship", depends_on=("test",)),
        ],
    )
    assert [item.step_id for item in plan.ready_steps()] == ["build"]
    assert [item.step_id for item in plan.ready_steps({"build"})] == ["test"]
    assert [item.step_id for item in plan.ready_steps({"build", "test"})] == ["ship"]


def test_unknown_completed_step_is_rejected():
    plan = build_plan("release", [step("build")])
    with pytest.raises(TaskPlanningError, match="unknown completed"):
        plan.ready_steps({"ghost"})


def test_duplicate_step_ids_are_rejected():
    with pytest.raises(TaskPlanningError, match="duplicate step_id"):
        build_plan("task", [step("same"), step("same")])


def test_missing_dependency_is_rejected():
    with pytest.raises(TaskPlanningError, match="unknown step"):
        build_plan("task", [step("compile", depends_on=("configure",))])


def test_cycles_are_rejected():
    with pytest.raises(TaskPlanningError, match="cycle"):
        topological_order([step("a", depends_on=("b",)), step("b", depends_on=("a",))])


def test_self_dependency_and_duplicate_dependencies_are_rejected():
    with pytest.raises(TaskPlanningError, match="itself"):
        step("a", depends_on=("a",))
    with pytest.raises(TaskPlanningError, match="duplicate dependencies"):
        step("a", depends_on=("b", "b"))


def test_plan_from_dict_parses_json_compatible_payload():
    plan = plan_from_dict(
        {
            "task": "fix bug",
            "steps": [
                {
                    "step_id": "inspect",
                    "title": "Inspect",
                    "description": "Inspect issue",
                    "success_criteria": ["root cause known"],
                },
                {
                    "step_id": "fix",
                    "title": "Fix",
                    "description": "Apply fix",
                    "depends_on": ["inspect"],
                    "risk": "low",
                    "metadata": {"owner": "agent"},
                },
            ],
        }
    )
    assert plan.task == "fix bug"
    assert [item.step_id for item in plan.ordered_steps()] == ["inspect", "fix"]
    assert plan.steps[1].metadata["owner"] == "agent"


def test_plan_from_dict_rejects_invalid_field_types():
    with pytest.raises(TaskPlanningError, match=r"steps\[0\].depends_on"):
        plan_from_dict(
            {
                "task": "task",
                "steps": [
                    {
                        "step_id": "a",
                        "title": "A",
                        "description": "A",
                        "depends_on": "b",
                    }
                ],
            }
        )


def test_replan_adds_remediation_and_rewires_successors():
    plan = build_plan(
        "repair",
        [
            step("inspect"),
            step("fix", depends_on=("inspect",)),
            step("verify", depends_on=("fix",)),
            step("release", depends_on=("verify",)),
        ],
    )
    revised = replan_after_failure(
        plan,
        "fix",
        [
            step("diagnose", depends_on=("inspect",)),
            step("alternative_fix", depends_on=("diagnose",)),
        ],
    )
    assert revised.plan_version == 2
    assert revised.parent_version == 1
    assert next(s for s in revised.steps if s.step_id == "verify").depends_on == (
        "alternative_fix",
    )
    assert [s.step_id for s in revised.ready_steps({"inspect"})] == ["diagnose"]
    assert (
        next(s for s in revised.steps if s.step_id == "fix").status is StepStatus.FAILED
    )
    assert [s.step_id for s in revised.ordered_steps()].index("alternative_fix") < [
        s.step_id for s in revised.ordered_steps()
    ].index("verify")


def test_replan_rejects_unknown_failed_step_or_empty_remediation():
    plan = build_plan("repair", [step("inspect")])
    with pytest.raises(TaskPlanningError, match="unknown failed"):
        replan_after_failure(plan, "missing", [step("remediate")])
    with pytest.raises(TaskPlanningError, match="at least one"):
        replan_after_failure(plan, "inspect", [])


def test_replan_rejects_dependency_on_later_or_unrelated_step():
    plan = build_plan(
        "repair",
        [
            step("inspect"),
            step("fix", depends_on=("inspect",)),
            step("verify", depends_on=("fix",)),
        ],
    )
    with pytest.raises(TaskPlanningError, match="prerequisites"):
        replan_after_failure(plan, "fix", [step("remediate", depends_on=("verify",))])


def test_step_validation_requires_explicit_risk_and_nonblank_identity():
    with pytest.raises(TaskPlanningError, match="non-empty"):
        TaskStep(step_id=" ", title="T", description="D")
    with pytest.raises(TaskPlanningError, match="risk"):
        TaskStep(step_id="a", title="A", description="D", risk="critical")


def test_failed_plan_does_not_mutate_original_plan():
    plan = build_plan(
        "repair",
        [
            step("inspect"),
            step("fix", depends_on=("inspect",)),
            step("verify", depends_on=("fix",)),
        ],
    )
    revised = replan_after_failure(
        plan, "fix", [step("remediate", depends_on=("inspect",))]
    )
    assert len(plan.steps) == 3
    assert len(revised.steps) == 4
    assert plan.plan_version == 1


def test_step_status_values_are_stable_strings():
    assert StepStatus.SUCCEEDED.value == "succeeded"
    assert StepStatus.BLOCKED.value == "blocked"


def test_status_transitions_require_successful_dependencies():
    plan = build_plan("release", [step("build"), step("test", depends_on=("build",))])
    with pytest.raises(TaskPlanningError, match="dependencies succeed"):
        transition_step(plan, "test", StepStatus.IN_PROGRESS)
    plan = transition_step(plan, "build", StepStatus.IN_PROGRESS)
    plan = transition_step(plan, "build", StepStatus.SUCCEEDED)
    plan = transition_step(plan, "test", StepStatus.IN_PROGRESS)
    assert (
        next(item for item in plan.steps if item.step_id == "test").status
        is StepStatus.IN_PROGRESS
    )


def test_terminal_status_cannot_be_reset_without_replanning():
    plan = build_plan("release", [step("build")])
    plan = transition_step(plan, "build", StepStatus.IN_PROGRESS)
    plan = transition_step(plan, "build", StepStatus.FAILED)
    with pytest.raises(TaskPlanningError, match="invalid status transition"):
        transition_step(plan, "build", StepStatus.PENDING)


def test_transition_rejects_unknown_step():
    plan = build_plan("release", [step("build")])
    with pytest.raises(TaskPlanningError, match="unknown step"):
        transition_step(plan, "missing", StepStatus.IN_PROGRESS)


def test_decompose_task_validates_injected_planner_output():
    def proposer(task):
        assert task == "repair flaky test"
        return {
            "task": "ignore the original task",
            "steps": [
                {
                    "step_id": "reproduce",
                    "title": "Reproduce",
                    "description": "Reproduce the failure",
                },
                {
                    "step_id": "repair",
                    "title": "Repair",
                    "description": "Fix the cause",
                    "depends_on": ["reproduce"],
                },
            ],
        }

    plan = decompose_task("repair flaky test", proposer)
    assert plan.task == "repair flaky test"
    assert [item.step_id for item in plan.ordered_steps()] == ["reproduce", "repair"]


def test_decompose_task_rejects_oversized_or_malformed_proposals():
    with pytest.raises(TaskPlanningError, match="maximum"):
        decompose_task("task", lambda _: {"steps": [{}, {}]}, max_steps=1)
    with pytest.raises(TaskPlanningError, match="mapping"):
        decompose_task("task", lambda _: ["not", "a", "mapping"])
    with pytest.raises(TaskPlanningError, match="steps"):
        decompose_task("task", lambda _: {"steps": "not a list"})
