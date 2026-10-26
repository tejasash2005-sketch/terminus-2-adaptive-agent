"""Tests for model-backed planning and guarded autonomous execution."""

import json

import pytest

from harbor.agents.terminus_2.autonomous import (
    AutonomousAgent,
    AutonomousConfig,
    ExecutionResult,
    ModelBackedPlanner,
    ModelNotConfiguredError,
    ModelPlanningError,
)
from harbor.llms.base import BaseLLM, LLMResponse


class FakeModel(BaseLLM):
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    async def call(self, prompt: str, **kwargs) -> LLMResponse:
        self.calls += 1
        value = self.responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return LLMResponse(content=value)

    def get_model_context_limit(self):
        return 8192

    def get_model_output_limit(self):
        return 2048


def response(steps):
    return json.dumps({"task": "objective", "steps": steps})


def test_model_planner_uses_existing_base_llm_and_validates_plan():
    model = FakeModel(
        [
            response(
                [
                    {
                        "step_id": "a",
                        "title": "A",
                        "description": "Do A",
                        "success_criteria": ["verified"],
                    }
                ]
            )
        ]
    )
    import asyncio

    plan = asyncio.run(ModelBackedPlanner(model).plan("objective"))
    assert plan.task == "objective"
    assert plan.steps[0].step_id == "a"
    assert model.calls == 1


def test_missing_model_is_a_clear_configuration_error():
    import asyncio

    with pytest.raises(ModelNotConfiguredError, match="No Harbor BaseLLM"):
        asyncio.run(ModelBackedPlanner(None).plan("objective"))


@pytest.mark.parametrize(
    "payload",
    [
        "not json",
        json.dumps(
            {
                "task": "x",
                "steps": [
                    {
                        "step_id": "a",
                        "title": "A",
                        "description": "x",
                        "status": "succeeded",
                    }
                ],
            }
        ),
        json.dumps(
            {
                "task": "x",
                "steps": [
                    {
                        "step_id": "a",
                        "title": "A",
                        "description": "x",
                        "depends_on": ["missing"],
                    }
                ],
            }
        ),
        json.dumps(
            {
                "task": "x",
                "steps": [
                    {
                        "step_id": "a",
                        "title": "A",
                        "description": "x",
                        "depends_on": ["b"],
                    },
                    {
                        "step_id": "b",
                        "title": "B",
                        "description": "x",
                        "depends_on": ["a"],
                    },
                ],
            }
        ),
    ],
)
def test_planner_rejects_invalid_model_output(payload):
    import asyncio

    with pytest.raises(ModelPlanningError):
        asyncio.run(
            ModelBackedPlanner(FakeModel([payload]), max_attempts=1).plan("objective")
        )


def test_planner_retries_bounded_transient_failure():
    import asyncio

    valid = response([{"step_id": "a", "title": "A", "description": "Do A"}])
    model = FakeModel([RuntimeError("temporary"), valid])
    plan = asyncio.run(ModelBackedPlanner(model, max_attempts=2).plan("objective"))
    assert plan.steps[0].step_id == "a"
    assert model.calls == 2


def test_agent_executes_and_verifies_actual_result():
    import asyncio

    model = FakeModel(
        [
            response(
                [
                    {
                        "step_id": "a",
                        "title": "A",
                        "description": "Do A",
                        "success_criteria": ["evidence"],
                    }
                ]
            )
        ]
    )
    calls = []

    async def executor(step, outputs):
        calls.append(step.step_id)
        return ExecutionResult({"value": 7}, "observed output")

    agent = AutonomousAgent(
        model, executor, lambda step, result: result.output.get("value") == 7
    )
    report = asyncio.run(agent.run("objective"))
    assert report.succeeded
    assert report.terminal_reason == "objective_completed"
    assert calls == ["a"]
    assert report.outputs["a"]["value"] == 7


def test_failed_verification_does_not_claim_success():
    import asyncio

    model = FakeModel(
        [response([{"step_id": "a", "title": "A", "description": "Do A"}])]
    )

    async def executor(step, outputs):
        return ExecutionResult({"claimed": True}, "model says done")

    report = asyncio.run(
        AutonomousAgent(
            model, executor, lambda s, r: False, config=AutonomousConfig(max_replans=0)
        ).run("objective")
    )
    assert not report.succeeded
    assert report.plan.steps[0].status.value == "failed"
    assert report.terminal_reason == "failed_tasks_remain"


def test_dependency_failure_blocks_dependent_task():
    import asyncio

    model = FakeModel(
        [
            response(
                [
                    {"step_id": "a", "title": "A", "description": "Fail"},
                    {
                        "step_id": "b",
                        "title": "B",
                        "description": "Must not run",
                        "depends_on": ["a"],
                    },
                ]
            )
        ]
    )
    calls = []

    async def executor(step, outputs):
        calls.append(step.step_id)
        if step.step_id == "a":
            raise RuntimeError("failed")
        return ExecutionResult({}, "ok")

    report = asyncio.run(
        AutonomousAgent(
            model, executor, lambda s, r: True, config=AutonomousConfig(max_replans=0)
        ).run("objective")
    )
    assert calls == ["a"]
    assert {s.step_id: s.status.value for s in report.plan.steps} == {
        "a": "failed",
        "b": "blocked",
    }


def test_high_risk_step_requires_explicit_approval():
    import asyncio

    model = FakeModel(
        [
            response(
                [
                    {
                        "step_id": "danger",
                        "title": "Danger",
                        "description": "Sensitive",
                        "risk": "high",
                    }
                ]
            )
        ]
    )
    calls = []

    async def executor(step, outputs):
        calls.append(step.step_id)
        return ExecutionResult({}, "done")

    report = asyncio.run(
        AutonomousAgent(model, executor, lambda s, r: True).run("objective")
    )
    assert calls == []
    assert report.plan.steps[0].status.value == "blocked"
    assert report.terminal_reason == "blocked_tasks_remain"


def test_checkpoint_contains_real_plan_and_terminal_state(tmp_path):
    import asyncio

    path = tmp_path / "state" / "run.json"
    model = FakeModel(
        [response([{"step_id": "a", "title": "A", "description": "Do A"}])]
    )

    async def executor(step, outputs):
        return ExecutionResult({"real": 1}, "verified")

    report = asyncio.run(
        AutonomousAgent(
            model,
            executor,
            lambda s, r: True,
            config=AutonomousConfig(checkpoint_path=str(path)),
        ).run("objective")
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["execution_id"] == report.execution_id
    assert payload["terminal_reason"] == "objective_completed"
    assert payload["outputs"]["a"]["real"] == 1


def test_attempt_count_defaults_to_one_for_non_idempotent_safety():
    assert AutonomousConfig().max_attempts_per_step == 1


def test_resume_restores_checkpoint_without_reexecuting_successful_steps(tmp_path):
    import asyncio

    path = tmp_path / "checkpoint.json"
    valid = response([{"step_id": "a", "title": "A", "description": "Do A"}])
    model = FakeModel([valid])
    calls = []

    async def executor(step, outputs):
        calls.append(step.step_id)
        return ExecutionResult({"value": 3}, "verified")

    config = AutonomousConfig(checkpoint_path=str(path))
    first = asyncio.run(
        AutonomousAgent(model, executor, lambda s, r: True, config=config).run(
            "objective", execution_id="stable-id"
        )
    )
    assert first.succeeded and calls == ["a"]
    # A resumed agent does not need a model because the checkpoint is authoritative.
    resumed = asyncio.run(
        AutonomousAgent(None, executor, lambda s, r: True, config=config).run(
            "objective", resume_from=str(path)
        )
    )
    assert resumed.succeeded
    assert resumed.execution_id == "stable-id"
    assert calls == ["a"]


def test_resume_rejects_checkpoint_for_different_objective(tmp_path):
    import asyncio

    path = tmp_path / "checkpoint.json"
    path.write_text(json.dumps({"objective": "other"}), encoding="utf-8")

    async def executor(step, outputs):
        return ExecutionResult({}, "")

    agent = AutonomousAgent(None, executor, lambda s, r: True)
    with pytest.raises(Exception, match="does not match"):
        asyncio.run(agent.run("objective", resume_from=str(path)))


def test_bounded_attempt_retries_can_recover_transient_failure():
    import asyncio

    model = FakeModel(
        [response([{"step_id": "a", "title": "A", "description": "Do A"}])]
    )
    calls = []

    async def executor(step, outputs):
        calls.append(step.step_id)
        if len(calls) == 1:
            raise RuntimeError("transient")
        return ExecutionResult({"ok": True}, "observed")

    report = asyncio.run(
        AutonomousAgent(
            model,
            executor,
            lambda s, r: r.output.get("ok") is True,
            config=AutonomousConfig(max_attempts_per_step=2, max_replans=0),
        ).run("objective")
    )
    assert report.succeeded
    assert len(calls) == 2


def test_model_generated_operation_requires_explicit_allowlist():
    import asyncio

    payload = response(
        [
            {
                "step_id": "a",
                "title": "A",
                "description": "Do A",
                "metadata": {"operation": "delete_all"},
            }
        ]
    )
    with pytest.raises(ModelPlanningError, match="unsupported operation"):
        asyncio.run(
            ModelBackedPlanner(FakeModel([payload]), max_attempts=1).plan("objective")
        )
    plan = asyncio.run(
        ModelBackedPlanner(
            FakeModel([payload]), max_attempts=1, allowed_operations=("delete_all",)
        ).plan("objective")
    )
    assert plan.steps[0].metadata["operation"] == "delete_all"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_steps": 0},
        {"max_iterations": 1.5},
        {"max_attempts_per_step": True},
        {"max_replans": -1},
        {"timeout_seconds": float("nan")},
        {"max_elapsed_seconds": float("inf")},
        {"allowed_operations": ["read"]},
        {"allowed_operations": ("read", "read")},
    ],
)
def test_config_rejects_invalid_or_non_finite_limits(kwargs):
    with pytest.raises(ValueError):
        AutonomousConfig(**kwargs)


def test_execution_result_rejects_non_json_output_and_bad_evidence():
    with pytest.raises(ValueError, match="JSON-serializable"):
        ExecutionResult({"not_json": object()})
    with pytest.raises(ValueError, match="JSON-serializable"):
        ExecutionResult({"not_finite": float("nan")})
    with pytest.raises(TypeError, match="evidence"):
        ExecutionResult({}, evidence=123)


def test_executor_cannot_report_late_approval_and_be_counted_as_success():
    import asyncio

    model = FakeModel(
        [response([{"step_id": "a", "title": "A", "description": "Sensitive"}])]
    )

    async def executor(step, outputs):
        return ExecutionResult(
            {"changed": True}, "action claimed", requires_approval=True
        )

    report = asyncio.run(
        AutonomousAgent(
            model,
            executor,
            lambda s, r: True,
            config=AutonomousConfig(max_replans=0),
        ).run("objective")
    )
    assert not report.succeeded
    assert report.plan.steps[0].status.value == "failed"
    assert any(
        "approval requirement after invocation" in event.detail
        for event in report.events
    )


def test_resume_rejects_checkpoint_with_unknown_fields(tmp_path):
    import asyncio

    path = tmp_path / "checkpoint.json"
    path.write_text(
        json.dumps({"objective": "objective", "extra": "untrusted"}), encoding="utf-8"
    )

    async def executor(step, outputs):
        return ExecutionResult({}, "verified")

    with pytest.raises(Exception, match="missing or unsupported top-level fields"):
        asyncio.run(
            AutonomousAgent(None, executor, lambda s, r: True).run(
                "objective", resume_from=str(path)
            )
        )


def test_resume_rejects_success_status_without_output_evidence(tmp_path):
    import asyncio

    path = tmp_path / "checkpoint.json"
    checkpoint = {
        "execution_id": "id",
        "objective": "objective",
        "plan_version": 1,
        "parent_version": None,
        "plan": {
            "task": "objective",
            "steps": [
                {
                    "step_id": "a",
                    "title": "A",
                    "description": "Do A",
                    "depends_on": [],
                    "success_criteria": [],
                    "risk": "normal",
                    "metadata": {},
                    "status": "succeeded",
                }
            ],
        },
        "outputs": {},
        "events": [],
        "terminal_reason": "objective_completed",
        "elapsed_seconds": 0.1,
        "replan_count": 0,
        "updated_at": "2026-10-23T00:00:00+00:00",
    }
    path.write_text(json.dumps(checkpoint), encoding="utf-8")

    async def executor(step, outputs):
        return ExecutionResult({}, "verified")

    with pytest.raises(Exception, match="without recorded output"):
        asyncio.run(
            AutonomousAgent(None, executor, lambda s, r: True).run(
                "objective", resume_from=str(path)
            )
        )


def test_cancelled_execution_writes_terminal_cancelled_checkpoint(tmp_path):
    import asyncio

    path = tmp_path / "checkpoint.json"
    model = FakeModel(
        [response([{"step_id": "a", "title": "A", "description": "Do A"}])]
    )
    started = asyncio.Event()

    async def executor(step, outputs):
        started.set()
        await asyncio.Event().wait()

    async def scenario():
        agent = AutonomousAgent(
            model,
            executor,
            lambda s, r: True,
            config=AutonomousConfig(checkpoint_path=str(path)),
        )
        task = asyncio.create_task(agent.run("objective"))
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["terminal_reason"] == "cancelled"
    assert saved["plan"]["steps"][0]["status"] == "blocked"
    assert saved["events"][-1]["detail"] == "cancelled"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"timeout_seconds": float("nan")},
        {"timeout_seconds": float("inf")},
        {"max_attempts": True},
        {"max_steps": 1.5},
        {"allowed_operations": ["read"]},
        {"allowed_operations": ("read", "read")},
    ],
)
def test_model_planner_rejects_invalid_limits_and_allowlists(kwargs):
    with pytest.raises(ValueError):
        ModelBackedPlanner(None, **kwargs)
