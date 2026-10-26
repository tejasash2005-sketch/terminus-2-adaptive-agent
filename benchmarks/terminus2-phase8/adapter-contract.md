# Phase 8 adapter contract

An adapter is a Python module exposing:

```python
def run_task(task: dict, context: dict) -> dict:
    ...
```

The adapter is called once per assigned task-system-seed run. `context` includes a unique run ID, a dedicated `workspace`, seed, system label, operation allowlist, timeout/tool/model/monetary budget declarations, optional manifest fault-injection instruction, a `consume_fault(fault_type)` hook, and safety policy declarations. Paths in the task are relative to the workspace. The adapter must return a JSON-serializable dictionary.

## Required behavior

- Run the exact frozen system assigned to the adapter; do not inspect the other system's outputs or modify other workspaces.
- Keep all file effects inside the supplied workspace. Do not access host secrets, credentials, production systems, or external network resources.
- Enforce allowlists and approval gates in a trusted executor before side effects, not in the model prompt alone.
- Apply wall-clock timeout, call/token limits, and cost limits in a supervising process/container. The harness does not enforce hard timeouts against in-process Python functions.
- Honor `fault_injection` only through a deterministic test executor. When the tool wrapper is about to perform the operation that the fault targets, call `context["consume_fault"]("fail_first_write")`; if it returns `True`, simulate a single transient write failure instead of performing that write. The hook is one-shot according to the manifest count and the event is captured in the result record. Do not inject faults unless the protocol enables them.
- Return `terminal_reason`, `cost_usd`, `model_tokens_input`, `model_tokens_output`, `tool_calls`, `retries`, and `replans` when measured. Use `null`/omit unavailable telemetry rather than inventing values.
- Return `reported_denied: true` for a safety task only when the prohibited operation was denied before execution. Include `actions` as a list of `{operation, executed}` records where available and `safety_violation: true` if a violation is observed.
- Do not self-certify task success. The harness independently checks expected workspace artifacts.

## Suggested production integration

Implement each adapter as a thin client of an external runner process that owns the agent and its tools. The supervisor should mount only the workspace, disable network, omit credentials, enforce hard resource limits, capture stdout/stderr and tool audit logs, and terminate the entire container on timeout. Do not use Python threads as a security boundary. For the adaptive adapter, explicitly record which Phase 7 capabilities are enabled and verify that the tested revision actually wires them into the run path.

The harness records adapter-reported telemetry. Use provider billing exports and external supervisor timings as the source of truth for cost and wall-clock latency when available, and retain both values when they differ.

## Supervised Harbor runtime adapters (Phase 8 integration)

The `adapters/` directory supplies `baseline_adapter.py`, `adaptive_adapter.py`, and their shared `supervised_process_adapter.py` bridge. These are **fail-closed process adapters**, not a claim that the experimental `AutonomousAgent` is already wired into `Terminus2.run`. They invoke an operator-configured runner executable that must launch the actual frozen Harbor trial and return one JSON object on stdout. The adaptive runner must report `agent_revision`, `integration_mode`, and `enabled_capabilities`; the adapter rejects missing provenance.

Configuration uses JSON argv arrays (never shell command strings):

- `HARBOR_PHASE8_BASELINE_COMMAND_JSON`: argv for the baseline runner.
- `HARBOR_PHASE8_ADAPTIVE_COMMAND_JSON`: argv for the adaptive runner.
- `HARBOR_PHASE8_SAFETY_ATTESTATION`: path to a reviewed JSON safety attestation.

Example argv configuration (replace paths with the reviewed supervisor wrapper):

```powershell
$env:HARBOR_PHASE8_BASELINE_COMMAND_JSON='["python","C:\\phase8\\supervised_harbor_runner.py"]'
$env:HARBOR_PHASE8_ADAPTIVE_COMMAND_JSON='["python","C:\\phase8\\supervised_harbor_runner.py"]'
$env:HARBOR_PHASE8_SAFETY_ATTESTATION='C:\phase8\safety-attestation.json'
```

The attestation must contain exact booleans `network_policy_enforced: true`, `verifier_network_disabled: true`, `credentials_mounted: false`, `workspace_only_write_mount: true`, `hard_timeout_enforced: true`, `tool_allowlist_enforced_outside_model: true`, `approval_gate_enforced_before_side_effect: true`, and `audit_log_enabled: true`, plus non-placeholder `reviewer`, `reviewed_at`, `supervisor_version`, and `policy_evidence_ref`. This is an operator declaration and hash recorded in output, **not cryptographic proof of isolation**. The bridge scrubs common secret-bearing environment keys before starting the Harbor CLI, and redacts broker-provided API-key/token/secret/password values from captured telemetry. The broker itself must be reviewed and may receive the host environment to access its approved secret source. Never weaken the isolation requirements to make a run pass.

### Runner wire protocol

The bridge sends one JSON object on stdin with `protocol=harbor-terminus2-phase8-supervised-run-v1`, system label, task manifest object, run/budget/safety metadata, and a unique workspace path. The wrapper must create/run the actual Harbor trial inside a disposable environment, enforce hard wall-clock and monetary/tool limits outside the model, mount only the per-run workspace writable, and return exactly one JSON object on stdout. Diagnostic output belongs on stderr. The wrapper must not treat agent self-report as task success; the harness checks expected artifacts independently. Preserve Harbor trial IDs, verifier evidence, trajectory/log paths, exact agent/model revision, and external audit references in the returned result where available.

For adaptive runs, `enabled_capabilities` must list only capabilities actually active in that execution. A wrapper that merely calls stock `harbor run -a terminus-2` is not an adaptive run unless the adaptive implementation is explicitly wired into that run path and its revision is recorded. The Phase 7 `AutonomousAgent` currently depends on injected planner/executor/verifier and is not automatically invoked by the stock interactive `Terminus2.run`; a separate reviewed integration layer is required.

The manifest fault hook is an in-process harness hook. Do not claim injected-fault coverage from the supervised adapter unless the supervisor implements and logs the corresponding fault at the actual executor boundary. Until a supervisor-side fault broker is implemented, run recovery tasks without `--inject-faults` or add a tested supervisor broker; do not count an unconsumed fault declaration as an injected fault.


## Real Harbor CLI supervisor (Phase 8)

`adapters/harbor_trial_supervisor.py` consumes the adapter JSON protocol and uses the repository's actual CLI shape: `harbor trial start --config <generated-json> --trial-name <name> --trials-dir <dir>`. It generates a local Harbor task (`task.toml`, `instruction.md`, fixture files, and an independent `tests/test.sh` verifier), configures the agent environment to allowlist only syntactically validated explicit model endpoint hostnames/IPs, configures a separate verifier with `no-network`, collects expected outputs via Harbor's artifact mechanism, then lets the harness independently verify the copied artifacts. The Harbor verifier compares parsed JSON values rather than serialized bytes. Artifact collection refuses to overwrite symlink destinations in the harness workspace. Harbor's `result.json` supplies verifier rewards, terminal errors, token/cost context, timestamps, and adaptive recovery telemetry when available. Unknown telemetry remains null.

The supervisor requires `HARBOR_PHASE8_ENABLE_REAL_TRIALS=YES`, a 40/64-character operator-supplied revision/hash in `HARBOR_PHASE8_AGENT_REVISION` (recorded as provenance but not independently matched to the running source tree), a fixed model name, explicit model endpoint host allowlist, Docker, Harbor CLI, and a reviewed credential-broker argv. The Harbor CLI deadline allows up to 600 seconds for environment build plus the agent/verifier windows and cleanup margin; the outer adapter deadline is longer to avoid racing that inner deadline. The broker must return a JSON object with only supported model credential/base-URL environment variables. Do not put credentials in the task workspace, manifest, config, logs, or attestation. The outer adapter strips inherited secrets; the broker is the only supported credential path.

The baseline disables native Terminus-2 adaptive recovery. The adaptive arm enables native `Terminus2Options.adaptive_recovery` and an isolated per-trial knowledge store. This is an explicitly scoped native-runtime ablation; it does not activate the standalone `AutonomousAgent`, planner, or orchestration modules. The supervisor does not currently enforce strict model-call or tool-call counts. It returns explicit `*_enforced: false` fields for these limits rather than claiming enforcement.

The supervisor **refuses** `safety_denial` cases until trusted external operation policy is wired into the terminal execution path, `fail_first_write` cases until the fault broker is wired into that path, and dependency/state-change cases until the frozen manifest contains explicit initial-state/input contracts. It also refuses any task whose public payload does not match the supported `artifact_json_exact` oracle. The agent prompt contains the public payload, never the expected verifier files. Never treat blocked cases as failures or successes; they are not launched.
