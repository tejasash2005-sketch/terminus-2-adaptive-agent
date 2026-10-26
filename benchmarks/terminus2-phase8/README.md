# Terminus-2 Phase 8 empirical evaluation harness

## Status and scientific scope

This directory contains the **evaluation specification and harness**, not real-agent benchmark results. No baseline or adaptive-agent empirical campaign is included in this release because no production adapter, isolated execution environment, or real model-backed task run was supplied and verified. The deterministic manifest is a proposed local-workspace benchmark; passing harness unit tests is not evidence of agent effectiveness.

The harness is standard-library-only and does not replace or modify Harbor's agent runtime. It loads two adapter modules supplied by the experiment owner. Each must export `run_task(task: dict, context: dict) -> dict`. Adapters should invoke the frozen baseline and Phase 7 adaptive implementation through a separately tested, sandboxed executor and return measured telemetry. Do not use the included test doubles as benchmark agents.

## Files

- `manifest.json`: deterministic, frozen v2 100-case manifest, 20 cases in each of five categories, with explicit input files and task-specific oracle relationships.
- `preregistration.md`: recommended confirmatory protocol and decision rules.
- `adapter-contract.md`: adapter interface, telemetry, and isolation requirements.
- `../../scripts/terminus2_phase8_eval.py`: paired randomized runner, independent workspace oracles, JSONL event records, and analysis.
- `adapters/baseline_adapter.py` and `adapters/adaptive_adapter.py`: fail-closed subprocess adapters for reviewed, operator-configured Harbor runner wrappers.
- `adapters/supervised_process_adapter.py`: shared subprocess protocol, timeout, and safety-attestation preflight.
- `adapters/harbor_trial_supervisor.py`: generates a local Harbor task from the frozen manifest, invokes the actual `harbor trial start` CLI in a supervised process group, reads Harbor's `result.json` and telemetry, and exports collected artifacts for the harness's independent oracle.
- `adapters/safety-attestation.example.json`: checklist template only; replace every placeholder after independent review.
- `../../tests/unit/agents/terminus_2/test_phase8_eval.py`: harness and adapter preflight tests; they do not constitute empirical agent trials.

The manifest is versioned as `harbor-terminus2-phase8-manifest-v2`; its `content_sha256` hashes its canonical JSON content excluding that field. The manifest is checked before execution. Do not edit a frozen manifest after collecting results; create a new version and record the change instead.

## Connecting the actual Harbor runtime

The provided adapters connect the harness to a reviewed external runner process; they intentionally do not claim the standalone Phase 7 `AutonomousAgent` is already wired into stock `Terminus2.run`. The ordinary `Terminus2.run` path operates through Harbor's terminal/tmux loop, while `AutonomousAgent` separately requires an injected model, policy-enforcing executor, and independent verifier. The adaptive runner must explicitly bridge those APIs or implement a reviewed custom Harbor agent, and must report the exact revision, integration mode, and capabilities actually enabled. A wrapper that merely launches stock Terminus-2 is a baseline run, not an adaptive run.

Set `HARBOR_PHASE8_BASELINE_COMMAND_JSON`, `HARBOR_PHASE8_ADAPTIVE_COMMAND_JSON`, and `HARBOR_PHASE8_SAFETY_ATTESTATION` as described in `adapter-contract.md`. Commands are JSON argv arrays, not shell strings. Each runner receives a JSON payload on stdin and must emit exactly one JSON object on stdout; send diagnostics to stderr. The adapter strips API-key/token/password/secret environment variables from child environments, so hosted-model credentials must be supplied through an approved short-lived secret broker inside the isolated runner, never from the workspace. The safety attestation is recorded and checked as a human-reviewed declaration, not accepted as proof of actual isolation.

**Do not run the adapters against real models until an independent operator has inspected the runner code, verified container/VM policy enforcement and external hard timeouts, checked credential handling, and validated task-specific oracles.** The v2 supervisor structurally supports `routine`, `dependencies`, and `state_change`: dependency cases ship an explicit `source.json` input and preregistered output relationships; state-change cases ship the post-transition `state.json` plus an explicit before/after transition contract. `safety_denial` remains blocked because stock Terminus-2 exposes terminal/shell execution rather than a trusted operation allowlist, and `fail_first_write` remains blocked because the interactive shell loop is not wired to the Python fault broker. The manifest records these runnable/blocked categories explicitly. Blocked categories must not be counted as runs; this is intentional fail-closed behavior, not a successful test result.

The baseline is the frozen Terminus-2 runtime with native adaptive recovery explicitly disabled; the adaptive arm enables Terminus-2's native `adaptive_recovery` and a per-trial isolated SQLite knowledge store. It does **not** claim to activate the separate experimental `AutonomousAgent`, task planner, or orchestration layer. The `max_turns` setting is not a strict provider-call cap; output telemetry explicitly marks tool-call/model-call budgets unenforced by this supervisor. The supervisor's hard deadline budgets up to 600 seconds for environment build plus agent, verifier, and cleanup time; the outer adapter deadline is intentionally longer. The supervisor scrubs common secret-bearing environment keys, redacts broker-provided secrets in captured telemetry, validates model hostnames, compares verifier JSON semantically, and refuses to overwrite symlink artifact destinations. These controls do not replace independent review of OS/container enforcement. The revision/hash environment value is operator-supplied provenance and is not independently matched to the running source tree.

## Requirements before any agent run

1. Freeze baseline and adaptive source revisions and configuration hashes.
2. Use equivalent task snapshots, model/provider configuration, tools, limits, and verifier.
3. Run each adapter in a disposable VM/container with no credentials, network disabled by default, and only a dedicated workspace mounted writable.
4. Enforce process timeout, tool-call limits, token limits, and monetary limits in the external supervisor/executor. The harness passes budget values to adapters but cannot terminate a hung in-process adapter.
5. Validate that executor allowlists and approval gates are enforced before side effects. The harness is not a security sandbox.
6. Have an independent operator verify the environment and the task oracles before confirmatory runs.

## Commands

From the repository root in a normally installed Harbor environment:

```bash
python scripts/terminus2_phase8_eval.py write-manifest --output benchmarks/terminus2-phase8/manifest.json
python -m pytest tests/unit/agents/terminus_2/test_phase8_eval.py -q
python scripts/terminus2_phase8_eval.py run --manifest benchmarks/terminus2-phase8/manifest.json --baseline-adapter path/to/baseline_adapter.py --adaptive-adapter path/to/adaptive_adapter.py --output-dir artifacts/phase8-pilot --seeds 11 29 47 --pilot --inject-faults
python scripts/terminus2_phase8_eval.py analyze --results artifacts/phase8-pilot/results.jsonl --output artifacts/phase8-pilot/analysis.json --bootstrap-resamples 10000 --bootstrap-seed 20261023
```

Use a **new output directory for every run**. The runner refuses to overwrite an existing `results.jsonl`. The sample command is a pilot only. Under the current frozen runnable-category policy, only 60 of the 100 manifest cases are executable by this supervisor. After pilot review, freeze a confirmatory protocol, calculate sample size, and run the frozen runnable benchmark (60 tasks × 5 paired seeds × 2 systems = 600 assigned executions). The 40 blocked cases are specified but are not assigned executions. Avoid `--max-cases` except for harness smoke tests; capped runs are not confirmatory evidence.

`--inject-faults` enables a deterministic `context["consume_fault"](fault_type)` hook. For the recovery cases, the adapter's tool wrapper should call `consume_fault("fail_first_write")` immediately before the first target write and simulate a transient error when it returns true. The hook records injected events in JSONL. This tests recovery only if the actual executor path uses the hook; simply enabling the flag is not evidence that a fault was injected.

## Raw records and analysis

`results.jsonl` has one record per assigned execution and is flushed to disk after each record. It includes run/task/pair IDs, seed, system, adapter and manifest hashes, oracle results, terminal reason, latency, adapter-reported cost/token/tool telemetry, exception, and safety incidents. Unknown cost remains `null`; it is not silently set to zero. Adapter-reported telemetry must be distinguished from independently billed or externally metered values.

The analysis pairs baseline and adaptive executions, reports verified success differences and category summaries, cost and latency distributions, paired latency/cost deltas, cost per verified success when measurable, and a task-cluster percentile bootstrap confidence interval. The interval is descriptive and can be unstable with few task clusters. The script does not automatically certify a minimum practical improvement, statistical power, or safe release. Interpret it under the predeclared protocol.

The independent verifier reads resulting workspace files rather than trusting an agent's success claim. For safety cases it checks the expected explicit denial and absence of named forbidden side-effect files. This is intentionally a narrow local oracle; additional real Harbor tasks need task-specific external oracles. A malicious or compromised adapter can falsify its own returned trace, so safety evidence must also come from executor logs and OS/container audit records.

## Reproducibility and interpretation

Preserve `run-metadata.json`, raw JSONL, manifest and adapter hashes, environment lockfile, model/provider version metadata, sanitized external audit logs, and analysis output. Never publish credentials or sensitive arguments. A zero-incident test run is not proof of universal safety. Report all assigned runs; timeout, agent crash, budget exhaustion, and failed verification are failures, not exclusions. Only predeclared infrastructure failures unrelated to agent behavior can be marked invalid, with counts and reasons published.
