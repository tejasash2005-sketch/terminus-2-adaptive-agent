"""Deterministic task decomposition and dependency-aware replanning.

This module plans work but does not execute commands or call an LLM. Callers
provide task steps and explicit dependencies; execution remains the caller's
responsibility. A failed step can be followed by remediation steps, and its
successors are rewired to wait for remediation rather than the failed step.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Callable, Iterable, Mapping, Sequence


class TaskPlanningError(ValueError):
    """Raised when a plan is ambiguous, incomplete, or cyclic."""


class StepStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class TaskStep:
    """A small, verifiable unit of work in a task plan.

    ``success_criteria`` should describe observable checks, not vague goals.
    Steps contain no executable shell command; an agent or caller interprets
    the description and performs work under its own safety policy.
    """

    step_id: str
    title: str
    description: str
    depends_on: tuple[str, ...] = ()
    success_criteria: tuple[str, ...] = ()
    risk: str = "normal"
    metadata: Mapping[str, str] = field(default_factory=dict)
    status: StepStatus = StepStatus.PENDING

    def __post_init__(self) -> None:
        for name in ("step_id", "title", "description"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise TaskPlanningError(f"{name} must be a non-empty string")
        if self.step_id.strip() != self.step_id:
            raise TaskPlanningError(
                "step_id must not have leading or trailing whitespace"
            )
        if len(set(self.depends_on)) != len(self.depends_on):
            raise TaskPlanningError(f"step {self.step_id!r} has duplicate dependencies")
        if self.step_id in self.depends_on:
            raise TaskPlanningError(f"step {self.step_id!r} cannot depend on itself")
        if self.risk not in {"low", "normal", "high"}:
            raise TaskPlanningError("risk must be 'low', 'normal', or 'high'")


@dataclass(frozen=True)
class TaskPlan:
    """Validated, dependency-ordered task plan."""

    task: str
    steps: tuple[TaskStep, ...]
    plan_version: int = 1
    parent_version: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.task, str) or not self.task.strip():
            raise TaskPlanningError("task must be a non-empty string")
        if self.plan_version < 1:
            raise TaskPlanningError("plan_version must be positive")
        if self.parent_version is not None and self.parent_version >= self.plan_version:
            raise TaskPlanningError("parent_version must be less than plan_version")
        validate_plan(self.steps)

    def ordered_steps(self) -> tuple[TaskStep, ...]:
        """Return a deterministic topological order, preserving input order on ties."""
        return topological_order(self.steps)

    def ready_steps(self, completed: Iterable[str] = ()) -> tuple[TaskStep, ...]:
        """Return steps whose dependencies are all in ``completed``."""
        done = set(completed)
        ids = {step.step_id for step in self.steps}
        unknown = done - ids
        if unknown:
            raise TaskPlanningError(
                f"unknown completed step(s): {', '.join(sorted(unknown))}"
            )
        return tuple(
            step
            for step in self.ordered_steps()
            if step.status is StepStatus.PENDING
            and step.step_id not in done
            and set(step.depends_on).issubset(done)
        )


def validate_plan(steps: Sequence[TaskStep]) -> None:
    """Validate unique IDs, dependency references, and acyclic structure."""
    seen: set[str] = set()
    for step in steps:
        if step.step_id in seen:
            raise TaskPlanningError(f"duplicate step_id: {step.step_id}")
        seen.add(step.step_id)
    for step in steps:
        missing = set(step.depends_on) - seen
        if missing:
            raise TaskPlanningError(
                f"step {step.step_id!r} depends on unknown step(s): {', '.join(sorted(missing))}"
            )
    topological_order(steps)


def topological_order(steps: Sequence[TaskStep]) -> tuple[TaskStep, ...]:
    """Return a stable topological order or raise for missing edges/cycles."""
    by_id: dict[str, TaskStep] = {}
    for step in steps:
        if step.step_id in by_id:
            raise TaskPlanningError(f"duplicate step_id: {step.step_id}")
        by_id[step.step_id] = step
    for step in steps:
        missing = set(step.depends_on) - by_id.keys()
        if missing:
            raise TaskPlanningError(
                f"step {step.step_id!r} depends on unknown step(s): {', '.join(sorted(missing))}"
            )

    input_order = {step.step_id: index for index, step in enumerate(steps)}
    remaining = {step.step_id: set(step.depends_on) for step in steps}
    result: list[TaskStep] = []
    while remaining:
        ready = sorted(
            (
                step_id
                for step_id, dependencies in remaining.items()
                if not dependencies
            ),
            key=input_order.__getitem__,
        )
        if not ready:
            cyclic = ", ".join(sorted(remaining))
            raise TaskPlanningError(f"dependency cycle detected among: {cyclic}")
        for step_id in ready:
            result.append(by_id[step_id])
            del remaining[step_id]
        for dependencies in remaining.values():
            dependencies.difference_update(ready)
    return tuple(result)


def build_plan(task: str, steps: Iterable[TaskStep]) -> TaskPlan:
    """Build and validate a plan from caller-authored task steps."""
    return TaskPlan(task=task, steps=tuple(steps))


def plan_from_dict(payload: Mapping[str, object]) -> TaskPlan:
    """Parse a simple JSON-compatible plan payload with strict field checks."""
    task = payload.get("task")
    raw_steps = payload.get("steps")
    if not isinstance(task, str):
        raise TaskPlanningError("plan field 'task' must be a string")
    if not isinstance(raw_steps, list):
        raise TaskPlanningError("plan field 'steps' must be a list")
    steps: list[TaskStep] = []
    for index, raw in enumerate(raw_steps):
        if not isinstance(raw, dict):
            raise TaskPlanningError(f"steps[{index}] must be an object")
        step_id = raw.get("step_id")
        title = raw.get("title")
        description = raw.get("description")
        dependencies = raw.get("depends_on", [])
        criteria = raw.get("success_criteria", [])
        risk = raw.get("risk", "normal")
        metadata = raw.get("metadata", {})
        if (
            not isinstance(step_id, str)
            or not isinstance(title, str)
            or not isinstance(description, str)
        ):
            raise TaskPlanningError(
                f"steps[{index}] requires string step_id, title, and description"
            )
        if not isinstance(dependencies, list):
            raise TaskPlanningError(
                f"steps[{index}].depends_on must be a list of strings"
            )
        dependency_ids: list[str] = []
        for dependency in dependencies:
            if not isinstance(dependency, str):
                raise TaskPlanningError(
                    f"steps[{index}].depends_on must be a list of strings"
                )
            dependency_ids.append(dependency)
        if not isinstance(criteria, list):
            raise TaskPlanningError(
                f"steps[{index}].success_criteria must be a list of strings"
            )
        success_criteria: list[str] = []
        for criterion in criteria:
            if not isinstance(criterion, str):
                raise TaskPlanningError(
                    f"steps[{index}].success_criteria must be a list of strings"
                )
            success_criteria.append(criterion)
        if not isinstance(risk, str):
            raise TaskPlanningError(f"steps[{index}].risk must be a string")
        if not isinstance(metadata, dict):
            raise TaskPlanningError(
                f"steps[{index}].metadata must contain only string keys and values"
            )
        string_metadata: dict[str, str] = {}
        for key, value in metadata.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise TaskPlanningError(
                    f"steps[{index}].metadata must contain only string keys and values"
                )
            string_metadata[key] = value
        steps.append(
            TaskStep(
                step_id=step_id,
                title=title,
                description=description,
                depends_on=tuple(dependency_ids),
                success_criteria=tuple(success_criteria),
                risk=risk,
                metadata=string_metadata,
            )
        )
    return build_plan(task, steps)


def decompose_task(
    task: str,
    proposer: Callable[[str], Mapping[str, object]],
    *,
    max_steps: int = 32,
) -> TaskPlan:
    """Ask an injected planner to propose structured steps, then validate them.

    The proposer may be backed by an LLM, a rules engine, or a human-reviewed
    service. This module does not choose a model or execute generated commands.
    The original task statement remains authoritative, and malformed or overly
    large plans are rejected before a caller can execute any step.
    """
    if not isinstance(task, str) or not task.strip():
        raise TaskPlanningError("task must be a non-empty string")
    if max_steps < 1:
        raise TaskPlanningError("max_steps must be positive")
    proposed = proposer(task)
    if not isinstance(proposed, Mapping):
        raise TaskPlanningError("decomposer must return a mapping")
    raw_steps = proposed.get("steps")
    if not isinstance(raw_steps, list):
        raise TaskPlanningError("decomposer result must contain a 'steps' list")
    if len(raw_steps) > max_steps:
        raise TaskPlanningError(
            f"decomposer returned {len(raw_steps)} steps; configured maximum is {max_steps}"
        )
    payload = dict(proposed)
    payload["task"] = task
    return plan_from_dict(payload)


def transition_step(plan: TaskPlan, step_id: str, new_status: StepStatus) -> TaskPlan:
    """Return a new plan with a validated status transition for one step.

    A step can start only after all dependencies succeeded. Terminal states are
    immutable; a failed step requires an explicit replan instead of being reset
    silently to pending.
    """
    by_id = {step.step_id: step for step in plan.steps}
    if step_id not in by_id:
        raise TaskPlanningError(f"unknown step: {step_id}")
    current = by_id[step_id]
    allowed = {
        StepStatus.PENDING: {StepStatus.IN_PROGRESS, StepStatus.BLOCKED},
        StepStatus.IN_PROGRESS: {
            StepStatus.SUCCEEDED,
            StepStatus.FAILED,
            StepStatus.BLOCKED,
        },
        StepStatus.SUCCEEDED: set(),
        StepStatus.FAILED: set(),
        StepStatus.BLOCKED: set(),
    }
    if new_status not in allowed[current.status]:
        raise TaskPlanningError(
            f"invalid status transition for {step_id!r}: {current.status.value} -> {new_status.value}"
        )
    if new_status is StepStatus.IN_PROGRESS:
        unresolved = [
            dependency
            for dependency in current.depends_on
            if by_id[dependency].status is not StepStatus.SUCCEEDED
        ]
        if unresolved:
            raise TaskPlanningError(
                f"step {step_id!r} cannot start before dependencies succeed: {', '.join(unresolved)}"
            )
    updated = tuple(
        replace(step, status=new_status) if step.step_id == step_id else step
        for step in plan.steps
    )
    return TaskPlan(
        task=plan.task,
        steps=updated,
        plan_version=plan.plan_version,
        parent_version=plan.parent_version,
    )


def replan_after_failure(
    plan: TaskPlan,
    failed_step_id: str,
    remediation_steps: Iterable[TaskStep],
) -> TaskPlan:
    """Insert remediation steps and gate the failed step's direct successors.

    Remediation steps may depend only on existing steps that precede the failed
    step or on earlier remediation steps. The final remediation step becomes a
    dependency of the failed step's former successors. This does not mark the
    failed work as successful; callers must decide whether remediation made
    continuation safe and verify each step's criteria.
    """
    by_id = {step.step_id: step for step in plan.steps}
    if failed_step_id not in by_id:
        raise TaskPlanningError(f"unknown failed step: {failed_step_id}")
    additions = tuple(remediation_steps)
    if not additions:
        raise TaskPlanningError("at least one remediation step is required")
    existing_ids = set(by_id)
    added_ids: set[str] = set()
    failed = by_id[failed_step_id]
    allowed_base = set(failed.depends_on)
    for step in additions:
        if step.step_id in existing_ids or step.step_id in added_ids:
            raise TaskPlanningError(
                f"remediation step ID already exists: {step.step_id}"
            )
        added_ids.add(step.step_id)
        for dependency in step.depends_on:
            if dependency not in allowed_base and dependency not in added_ids:
                raise TaskPlanningError(
                    f"remediation step {step.step_id!r} must depend only on failed-step prerequisites "
                    "or earlier remediation steps"
                )
    final_remediation_id = additions[-1].step_id
    rewritten: list[TaskStep] = []
    for step in plan.steps:
        if step.step_id == failed_step_id:
            step = replace(step, status=StepStatus.FAILED)
        if step.step_id != failed_step_id and failed_step_id in step.depends_on:
            dependencies = tuple(
                final_remediation_id if dependency == failed_step_id else dependency
                for dependency in step.depends_on
            )
            step = replace(step, depends_on=dependencies)
        rewritten.append(step)
    revised_steps = tuple(rewritten) + additions
    return TaskPlan(
        task=plan.task,
        steps=revised_steps,
        plan_version=plan.plan_version + 1,
        parent_version=plan.plan_version,
    )
