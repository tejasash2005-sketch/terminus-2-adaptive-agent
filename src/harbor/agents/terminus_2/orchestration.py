"""Deterministic multi-component orchestration for validated task plans.

Components are injected callables. This module provides routing, dependency-gated
execution, isolated per-step inputs, result recording, and failure propagation;
it does not create agents, call models, execute shell commands, or infer success.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import copy
from time import monotonic
from typing import Callable, Mapping

from harbor.agents.terminus_2.task_planner import (
    StepStatus,
    TaskPlan,
    TaskStep,
    transition_step,
)


class OrchestrationError(ValueError):
    """Raised when component registration or step routing is invalid."""


@dataclass(frozen=True)
class Component:
    """A named worker with declared capabilities and an injected handler.

    The handler receives the step and a read-only-by-contract snapshot of prior
    successful outputs, and returns a mapping of string artifact names to values.
    Side effects remain the handler's responsibility.
    """

    name: str
    capabilities: frozenset[str]
    handler: Callable[
        [TaskStep, Mapping[str, Mapping[str, object]]], Mapping[str, object]
    ]

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise OrchestrationError("component name must be a non-empty string")
        if not callable(self.handler):
            raise OrchestrationError("component handler must be callable")
        if any(
            not isinstance(cap, str) or not cap.strip() for cap in self.capabilities
        ):
            raise OrchestrationError("component capabilities must be non-empty strings")


@dataclass(frozen=True)
class StepExecution:
    step_id: str
    component: str | None
    status: StepStatus
    output: Mapping[str, object] = field(default_factory=dict)
    error: str | None = None
    duration_seconds: float = 0.0


@dataclass(frozen=True)
class OrchestrationReport:
    task: str
    plan: TaskPlan
    executions: tuple[StepExecution, ...]
    outputs: Mapping[str, Mapping[str, object]]

    @property
    def succeeded(self) -> bool:
        return all(step.status is StepStatus.SUCCEEDED for step in self.plan.steps)

    @property
    def failed_step_ids(self) -> tuple[str, ...]:
        return tuple(
            e.step_id for e in self.executions if e.status is StepStatus.FAILED
        )

    @property
    def blocked_step_ids(self) -> tuple[str, ...]:
        return tuple(
            e.step_id for e in self.executions if e.status is StepStatus.BLOCKED
        )


class TaskOrchestrator:
    """Run ready plan steps through explicitly registered components.

    Routing is explicit when ``step.metadata['component']`` is present;
    otherwise ``step.metadata['capability']`` requests a capability. If neither
    is present, the sole registered component is used; multiple candidates are
    considered an error rather than silently guessing. Independent branches
    continue after a failure unless ``fail_fast=True``.
    """

    def __init__(
        self,
        components: tuple[Component, ...] | list[Component],
        *,
        fail_fast: bool = False,
    ):
        by_name: dict[str, Component] = {}
        for component in components:
            if component.name in by_name:
                raise OrchestrationError(f"duplicate component name: {component.name}")
            by_name[component.name] = component
        if not by_name:
            raise OrchestrationError("at least one component must be registered")
        self._components = by_name
        self._fail_fast = fail_fast

    def _select(self, step: TaskStep) -> Component:
        explicit = step.metadata.get("component")
        if explicit is not None:
            try:
                return self._components[explicit]
            except KeyError as exc:
                raise OrchestrationError(
                    f"step {step.step_id!r} requests unknown component {explicit!r}"
                ) from exc
        capability = step.metadata.get("capability")
        if capability is not None:
            matches = [
                c for c in self._components.values() if capability in c.capabilities
            ]
        elif len(self._components) == 1:
            return next(iter(self._components.values()))
        else:
            raise OrchestrationError(
                f"step {step.step_id!r} must declare metadata['component'] or ['capability']"
            )
        if len(matches) != 1:
            names = ", ".join(c.name for c in matches) or "none"
            raise OrchestrationError(
                f"step {step.step_id!r} capability {capability!r} matched {len(matches)} components: {names}"
            )
        return matches[0]

    def run(self, plan: TaskPlan) -> OrchestrationReport:
        """Execute the plan synchronously and return all recorded step outcomes."""
        current = plan
        executions: list[StepExecution] = []
        outputs: dict[str, Mapping[str, object]] = {}
        stop_after_failure = False

        # Preflight every route before any handler can cause a side effect.
        selected = {step.step_id: self._select(step) for step in current.steps}

        while True:
            by_id = {step.step_id: step for step in current.steps}
            pending = [
                s for s in current.ordered_steps() if s.status is StepStatus.PENDING
            ]
            if not pending:
                break
            progress = False
            for step in pending:
                dependencies = [by_id[d].status for d in step.depends_on]
                if any(
                    status in {StepStatus.FAILED, StepStatus.BLOCKED}
                    for status in dependencies
                ):
                    current = transition_step(current, step.step_id, StepStatus.BLOCKED)
                    executions.append(
                        StepExecution(
                            step.step_id,
                            selected[step.step_id].name,
                            StepStatus.BLOCKED,
                            error="dependency did not succeed",
                        )
                    )
                    progress = True
                    continue
                if not all(status is StepStatus.SUCCEEDED for status in dependencies):
                    continue
                if stop_after_failure:
                    current = transition_step(current, step.step_id, StepStatus.BLOCKED)
                    executions.append(
                        StepExecution(
                            step.step_id,
                            selected[step.step_id].name,
                            StepStatus.BLOCKED,
                            error="blocked by fail_fast after an earlier failure",
                        )
                    )
                    progress = True
                    continue
                current = transition_step(current, step.step_id, StepStatus.IN_PROGRESS)
                worker = selected[step.step_id]
                started = monotonic()
                try:
                    result = worker.handler(step, copy.deepcopy(outputs))
                    if not isinstance(result, Mapping):
                        raise TypeError("component handler must return a mapping")
                    output = copy.deepcopy(dict(result))
                    if any(not isinstance(key, str) for key in output):
                        raise TypeError("component output keys must be strings")
                except (
                    Exception
                ) as exc:  # component failures become explicit step outcomes
                    current = transition_step(current, step.step_id, StepStatus.FAILED)
                    executions.append(
                        StepExecution(
                            step.step_id,
                            worker.name,
                            StepStatus.FAILED,
                            error=f"{type(exc).__name__}: {exc}",
                            duration_seconds=max(0.0, monotonic() - started),
                        )
                    )
                    stop_after_failure = self._fail_fast
                else:
                    outputs[step.step_id] = output
                    current = transition_step(
                        current, step.step_id, StepStatus.SUCCEEDED
                    )
                    executions.append(
                        StepExecution(
                            step.step_id,
                            worker.name,
                            StepStatus.SUCCEEDED,
                            output=output,
                            duration_seconds=max(0.0, monotonic() - started),
                        )
                    )
                progress = True
            if not progress:
                # A valid acyclic plan should not reach this branch unless a
                # caller supplied non-pending statuses that cannot be advanced.
                break

        return OrchestrationReport(plan.task, current, tuple(executions), dict(outputs))
