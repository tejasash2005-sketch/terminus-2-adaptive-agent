# Terminus-2 Adaptive Terminal Intelligence

This extension adds conservative failure classification, recovery guidance, optional
persistent outcome memory, and a deterministic run-results evaluator. It does not
automatically repeat terminal commands: a timeout may occur after a command has
already changed the environment.

## Components

- `failure_classifier.py` classifies explicit timeout, context-limit, output-limit,
  and missing-dependency signals. Unrecognized terminal output is not treated as a
  failure by `classify_command_result`.
- `adaptive_recovery.py` selects a conservative strategy and defines per-run outcome
  records. `succeeded` means the failure signal was absent from the next observed
  command result; it does **not** mean the overall task succeeded.
- `terminus_2.py` supplies guidance to the next model turn, records whether the
  failure signal cleared, and writes `adaptive_recovery.json` beside the trajectory.
- `recovery_knowledge.py` is an opt-in SQLite store. Configure
  `adaptive_recovery.knowledge_store_path` to persist categorical outcomes across
  runs. It intentionally does not store raw prompts or terminal output. After two
  recorded failures for the same failure-type/strategy pair, the agent selects STOP
  rather than recommending the same strategy again.
- `trajectory_evaluation.py` summarizes run results without treating missing metrics
  as zero and keeps task success separate from failure-signal clearance.

## Configuration

The Terminus-2 `adaptive_recovery` option accepts:

- `enabled` (default `true`): enable failure guidance and outcome records.
- `max_attempts` (default `2`): attempt-limit helper setting. The agent does not
  automatically re-run terminal commands.
- `backoff_sec` (default `1.0`): delay helper setting for a caller that explicitly
  implements retry orchestration; it is not a delay applied to ordinary commands.
- `knowledge_store_path` (default unset): opt into cross-run SQLite history by
  providing a writable file path.

For example, supply `adaptive_recovery` in agent options with
`knowledge_store_path: "recovery-knowledge.sqlite3"` to enable persistence. Keep the
database in a suitable writable location and protect it according to the project's
data-handling requirements.

## Recovery telemetry

Each run writes `adaptive_recovery.json` as a JSON list. Records contain the failure
category, selected action, observed outcome, timestamp, and a categorical evidence
label. Raw terminal output is not stored in recovery telemetry.

The outcome is deliberately conservative:

- `succeeded: true`: the following command result had no recognized failure signal.
- `succeeded: false`: a recognized failure signal remained in the following result.
- `succeeded: null`: no following command result was available before the run ended.

These outcomes measure signal clearance, not task correctness.

## Evaluating experiments

Create a JSON file with matched baseline and adaptive runs. Record task success from
the task verifier, elapsed time and cost from the run, and recovery records when
available. Example:

```json
{
  "runs": [
    {
      "variant": "baseline",
      "task_success": true,
      "duration_sec": 42.1,
      "cost_usd": 0.12,
      "recovery_records": []
    },
    {
      "variant": "adaptive",
      "task_success": true,
      "duration_sec": 39.8,
      "cost_usd": 0.13,
      "recovery_records": [
        {
          "failure_type": "command_timeout",
          "action": "inspect_terminal_state",
          "succeeded": true
        }
      ]
    }
  ]
}
```

Run the summary utility with:

```console
python -m harbor.agents.terminus_2.trajectory_evaluation results.json
```

Use the same task set, environment image, model, budget and success verifier for
both variants. Report repeated-run variance and the number of runs. The evaluator
summarizes supplied evidence; it does not create benchmark results or infer task
success from terminal text.

## Development phase status

1. **Adaptive failure recovery:** classifier, conservative decision selection,
   next-turn guidance, and signal-clearance records are implemented. Automated
   command retries are intentionally not performed.
2. **Trajectory-based evaluation:** the JSON run-results evaluator is implemented.
   A benchmark campaign with measured baseline/adaptive results must still be run.
3. **Persistent recovery knowledge:** optional SQLite outcome storage and a
   repeated-failure stop guard are implemented.
4. **Task planning and decomposition:** validated plans, deterministic dependency ordering, guarded status transitions, injected decomposition, and remediation primitives are implemented in `task_planner.py`.
5. **Multi-component agent orchestration:** synchronous component routing and dependency-aware dispatch are implemented in `orchestration.py`; this is separate from the newer async autonomous loop.
6. **Model-backed autonomous execution and benchmark suite:** an opt-in `BaseLLM`-backed planner, injected executor/verifier loop, approval gate, bounded remediation, JSON checkpoints/resume, and six deterministic offline regression cases are implemented. An external-model empirical campaign and production environment integration still remain to be run.
7. **Portfolio packaging and release validation:** strict configuration and checkpoint checks, JSON-safe execution results, cancellation-state checkpointing, atomic unique checkpoint staging, and a repeated offline regression campaign are implemented. Full dependency-backed tests, lint, platform CI, and any real-model evaluation must be verified in a provisioned environment before calling the release fully validated.

Do not describe phases 4–6 as fully validated or production-ready until their
implementation checks and empirical experiments are complete. Preserve Harbor's
upstream license and attribution when redistributing this project.

## Phase 4: task planning and decomposition

`task_planner.py` adds a deterministic planning primitive that can be used by an
orchestrator without coupling planning to command execution or a specific model.
A caller supplies a task statement and small steps with explicit dependencies,
observable success criteria, a coarse risk label, and optional string metadata. The
`decompose_task` adapter can call an injected proposer (such as a model-backed or
human-reviewed planner) and validates its structured output, including a configurable
step-count limit, before accepting it.

The planner validates unique IDs, dependency references, self-dependencies, and
cycles; returns a stable topological order; and identifies steps whose dependencies
have completed. Step status transitions are immutable and checked: work cannot
start until its dependencies are marked successful, and terminal statuses cannot
be silently reset. After a failure, `replan_after_failure` marks the failed step,
adds caller-authored remediation steps, and rewires direct successors to wait for
the last remediation step. It does not execute remediation, claim the original step
succeeded, or infer that a task is correct; callers must verify each step's stated
success criteria before progressing.

Example:

```python
from harbor.agents.terminus_2.task_planner import TaskStep, build_plan

plan = build_plan(
    "fix and verify a regression",
    [
        TaskStep("inspect", "Inspect failure", "Reproduce and isolate the failure", success_criteria=("cause identified",)),
        TaskStep("fix", "Implement fix", "Apply the smallest safe change", depends_on=("inspect",), success_criteria=("patch applied",)),
        TaskStep("verify", "Run checks", "Run targeted tests and relevant lint", depends_on=("fix",), success_criteria=("checks pass",)),
    ],
)
for step in plan.ready_steps():
    print(step.step_id, step.title)
```

This phase provides validated injected decomposition and safe replan primitives, not a built-in model client.

## Phase 5: multi-component orchestration

`orchestration.py` adds `TaskOrchestrator`, `Component`, and `OrchestrationReport` as
an opt-in orchestration layer over validated `TaskPlan` objects. Components are
registered by unique name with declared capabilities and an injected handler. A
step can route explicitly with `metadata={"component": "researcher"}` or request a
capability with `metadata={"capability": "research"}`. Capability routing must
resolve to exactly one component; when multiple components are registered, a step
without routing metadata is rejected. All routes are preflighted before any handler
is called, preventing a later routing mistake from occurring after earlier side effects.

The dispatcher runs synchronously in deterministic topological order. A step starts
only after all dependencies have succeeded. Handlers receive the step and a deep-copied
snapshot of outputs from earlier successful steps, and return a mapping of output
artifacts. Each success or failure is recorded with component name, duration, and
output or error. A failed step blocks its descendants while independent branches may
continue; `fail_fast=True` instead blocks remaining pending work after the first
failure. Handler exceptions and invalid return values become explicit failed outcomes.
The original plan remains unchanged because status transitions return new plans.

Example:

```python
from harbor.agents.terminus_2.orchestration import Component, TaskOrchestrator
from harbor.agents.terminus_2.task_planner import TaskStep, build_plan

plan = build_plan("inspect and summarize", [
    TaskStep("inspect", "Inspect", "Collect evidence", metadata={"component": "reader"}),
    TaskStep("summarize", "Summarize", "Summarize evidence", depends_on=("inspect",),
             metadata={"component": "writer"}),
])

orchestrator = TaskOrchestrator([
    Component("reader", frozenset({"research"}), lambda step, outputs: {"facts": "..."}),
    Component("writer", frozenset({"writing"}), lambda step, outputs: {"summary": "..."}),
])
report = orchestrator.run(plan)
print(report.succeeded, report.failed_step_ids, report.blocked_step_ids)
```

This is a deterministic orchestration primitive, not a parallel agent runtime or
an automatic integration into Terminus-2's interactive command loop. It does not
create LLM clients, execute generated shell commands, verify domain-specific success
criteria, or automatically replan after failures. Component handlers must enforce
their own tool/shell safety policy and report success only when their checks pass.

## Phase 6: model-backed autonomous planning, execution, and regression benchmarks

`autonomous.py` adds an opt-in async control loop built on Harbor's existing
`BaseLLM` interface and Phase 4's `TaskPlan`/`TaskStep` validation. The caller
passes a configured Harbor model instance; model construction, provider selection,
credentials, and authentication remain the responsibility of Harbor's normal
configuration path. If no model is supplied for a new run, planning fails with
`ModelNotConfiguredError` instead of claiming AI planning occurred.

The planner requests JSON, checks the allowed schema fields, and then validates
IDs, dependencies, cycles, risks, and step-count limits using `task_planner.py`.
The asynchronous execution loop invokes only an injected executor and verifier.
It does not convert model text to shell commands. Executors must use the existing
environment/tool permission and sandbox systems, validate operation arguments,
and return `ExecutionResult` only with actual observed output/evidence. Verification
must be independent enough for the operation (for example, a test result or a
state query); model text alone is not proof. High-risk steps are blocked unless an
approval callback is configured and approves the step. Execution attempts default
to one because retrying after a timeout can duplicate side effects.

Example (the executor is intentionally application-specific):

```python
from harbor.agents.terminus_2.autonomous import (
    AutonomousAgent, AutonomousConfig, ExecutionResult,
)

async def executor(step, prior_outputs):
    # Dispatch only allow-listed operations through your existing Harbor tool or
    # environment abstraction. Never execute step.description as shell/code.
    result = await safe_application_dispatch(step, prior_outputs)
    return ExecutionResult(output=result.output, evidence=result.evidence)

async def verifier(step, result):
    return await independently_check_success(step, result)

agent = AutonomousAgent(
    configured_harbor_llm, executor, verifier,
    config=AutonomousConfig(checkpoint_path="run-state.json"),
)
report = await agent.run("Investigate the regression and verify a safe fix")
print(report.terminal_reason, report.succeeded)
```

The loop captures step events, outputs, verification outcomes, elapsed time, and
replanning decisions. Bounded remediation planning uses Phase 4's
`replan_after_failure` and does not change a failed task into a success. An
originally failed step therefore remains visible in the final report; the caller
must interpret the outcome and may need a domain-specific recovery policy. Limits
cover plan size, iterations, attempts, elapsed time, and number of replans. The
loop is sequential; it does not claim parallel execution.

When `checkpoint_path` is configured, each state update is written atomically as
JSON with execution ID, objective, versioned plan and statuses, completed outputs,
events, terminal reason, elapsed time, and replan count. Resume with
`await agent.run(objective, resume_from="run-state.json")`. Successful work is
restored and not repeated. Any step saved as `in_progress` is restored as
`blocked`, because a crash may have occurred after a side effect but before its
result was checkpointed; inspect the environment before manually recovering it.
Checkpoint files may contain application outputs and should be stored with
appropriate access controls. Checkpoint resume validates the objective but is not
a distributed lock or a guarantee of exactly-once side effects.

### Benchmark suite

`benchmark_suite.py` provides six deterministic offline regression cases for a
single step, dependency chain, failed verification, high-risk approval gate,
dependency failure, and checkpoint writing. Run it from a provisioned Harbor
checkout using the project's configured Python environment:

```python
import asyncio
from harbor.agents.terminus_2.benchmark_suite import (
    run_default_regression_suite, write_benchmark_report,
)

report = asyncio.run(run_default_regression_suite())
write_benchmark_report(report, "artifacts/terminus2-phase6-benchmark.json")
print(report["summary"])
```

The suite executes the actual autonomous loop against deterministic fake-model
responses and an in-memory executor. It measures regression behavior and safety
gates, **not** external model quality or real-world task success. For an empirical
study, define a fixed task corpus and independent verifiers, compare baseline and
adaptive variants on the same environment/model/budget, record repeated runs,
latency, costs and failures, and publish raw results plus variance. No external
model campaign or performance improvement is claimed by this implementation.


## Phase 7: release hardening and repeatability analysis

Phase 7 hardens `autonomous.py` at boundaries where malformed configuration,
non-JSON execution results, or edited/corrupt checkpoint files could otherwise
create ambiguous state. Resource limits must be finite and correctly typed.
Execution outputs must be JSON-safe rather than being silently converted to strings
when saved. Checkpoint restoration validates the shape, task statuses, output
references, and dependency consistency; a task marked successful must have a
recorded output and successful prerequisites. A task that was `in_progress` when a
process stopped is restored as `blocked`, not replayed automatically, because its
side effects are uncertain. Checkpoint staging uses a unique temporary file and an
atomic replacement in the destination directory.

Cancellation during an executor call records the affected task as blocked, writes a
`cancelled` terminal checkpoint, and re-raises cancellation to the caller. The
executor still owns actual sandboxing, authorization, idempotency, and side-effect
reconciliation; these cannot be guaranteed by the generic orchestrator alone.

The repeatability campaign is run with:

```console
uv run python scripts/run_terminus2_benchmark_campaign.py --repetitions 10 --output artifacts/terminus2-phase7-campaign.json
```

It runs the six deterministic offline cases repeatedly and reports each case's pass
count and min/median/mean/p95/max latency. The p95 uses nearest-rank selection; with
small samples it is coarse and is not a confidence interval. These measurements
include local scheduler and machine noise and do not demonstrate real-model quality.

Use `scripts/validate_terminus2_archive.py` to check release ZIP structure, required files, unsafe paths, duplicate entries, and accidental cache/VCS inclusion. See [`benchmarks/terminus2-phase7/README.md`](../benchmarks/terminus2-phase7/README.md)
for focused test, lint, benchmark, and release checklist commands. The full suite and
Ruff must be run in a fully provisioned environment; the absence of those results
must not be represented as a passing release gate.
