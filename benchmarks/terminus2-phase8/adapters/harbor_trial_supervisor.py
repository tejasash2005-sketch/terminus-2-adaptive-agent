#!/usr/bin/env python3
"""Supervised real Harbor trial runner for Phase 8.

Consumes the JSON protocol emitted by supervised_process_adapter.py. It creates
an ephemeral Harbor task, runs `harbor trial start`, then extracts Harbor's own
result/telemetry. It deliberately blocks until explicit operator preflight has
been completed. It does not itself claim the Harbor container is a security
boundary; Docker/Harbor policy and the reviewed attestation must be verified.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

PROTOCOL = "harbor-terminus2-phase8-supervised-run-v1"
REQUIRED_ATTESTATION = {
    "network_policy_enforced": True,
    "verifier_network_disabled": True,
    "credentials_mounted": False,
    "workspace_only_write_mount": True,
    "hard_timeout_enforced": True,
    "tool_allowlist_enforced_outside_model": True,
    "approval_gate_enforced_before_side_effect": True,
    "audit_log_enabled": True,
}


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _attestation() -> tuple[dict[str, Any], str]:
    raw = os.environ.get("HARBOR_PHASE8_SAFETY_ATTESTATION", "")
    if not raw:
        raise RuntimeError(
            "preflight blocked: HARBOR_PHASE8_SAFETY_ATTESTATION is required"
        )
    path = Path(raw).resolve(strict=True)
    data = _json(path)
    if not isinstance(data, dict):
        raise RuntimeError("preflight blocked: safety attestation must be an object")
    missing = [
        key
        for key, expected in REQUIRED_ATTESTATION.items()
        if data.get(key) is not expected
    ]
    if missing:
        raise RuntimeError(
            "preflight blocked: attestation controls missing/false: "
            + ", ".join(missing)
        )
    for key in ("reviewer", "reviewed_at", "supervisor_version", "policy_evidence_ref"):
        value = data.get(key)
        if (
            not isinstance(value, str)
            or not value.strip()
            or value.startswith("REPLACE_")
        ):
            raise RuntimeError(
                f"preflight blocked: attestation {key} must be reviewed and non-placeholder"
            )
    return data, hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_slug(value: str) -> str:
    return (
        "".join(c if c.isalnum() or c in "-_" else "-" for c in value)[:80] or "trial"
    )


def _validate_hosts(hosts: list[str]) -> list[str]:
    """Reject malformed/ambiguous entries before writing Harbor config."""
    if not hosts:
        raise RuntimeError(
            "preflight blocked: at least one explicit model hostname is required"
        )
    validated: list[str] = []
    for raw in hosts:
        host = raw.strip().rstrip(".").lower()
        if not host or "*" in host or "/" in host or any(c.isspace() for c in host):
            raise RuntimeError(
                "preflight blocked: model allowlist entries must be exact hostnames or IP addresses"
            )
        try:
            ipaddress.ip_address(host)
        except ValueError:
            if len(host) > 253 or not all(
                re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
                for label in host.split(".")
            ):
                raise RuntimeError(f"preflight blocked: invalid model hostname {raw!r}")
        if host not in validated:
            validated.append(host)
    return validated


def _is_sensitive_env_key(key: str) -> bool:
    upper = key.upper()
    fragments = (
        "API_KEY",
        "TOKEN",
        "PASSWORD",
        "SECRET",
        "CREDENTIAL",
        "PRIVATE_KEY",
        "ACCESS_KEY",
        "CLIENT_KEY",
        "AUTH",
        "CERTIFICATE",
        "KUBECONFIG",
        "SSH_AUTH_SOCK",
        "DOCKER_CONFIG",
    )
    return any(fragment in upper for fragment in fragments) or upper in {
        "AWS_ACCESS_KEY_ID",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "AZURE_CLIENT_ID",
        "AZURE_TENANT_ID",
        "AZURE_CLIENT_CERTIFICATE_PATH",
    }


def _redact_secrets(value: Any, credentials: dict[str, str]) -> Any:
    """Redact broker-provided secret values recursively before writing telemetry."""
    if isinstance(value, str):
        for key, secret in credentials.items():
            if key.endswith(("API_KEY", "TOKEN", "SECRET", "PASSWORD")) and secret:
                value = value.replace(secret, "<redacted>")
        return value
    if isinstance(value, list):
        return [_redact_secrets(item, credentials) for item in value]
    if isinstance(value, dict):
        return {key: _redact_secrets(item, credentials) for key, item in value.items()}
    return value


def _write_task(task_dir: Path, task: dict[str, Any], allowed_hosts: list[str]) -> None:
    if task.get("oracle") == "safety_denial":
        # Stock Terminus-2 has a terminal/shell tool, not an OS-enforced operation
        # allowlist. Do not represent prompt-level refusal as a security boundary.
        raise RuntimeError(
            "preflight blocked: safety_denial cases require a separately reviewed OS-enforced command/side-effect policy adapter; stock terminal execution is not an operation allowlist"
        )
    if task.get("fault_injection"):
        # The frozen manifest fault hook is a Python executor hook. Stock Harbor's
        # interactive shell loop does not call that hook, so silently running these
        # tasks would not be a controlled fault-injection experiment.
        raise RuntimeError(
            "preflight blocked: this manifest case requires fail_first_write injection, but stock Terminus-2 shell execution is not wired to the Phase 8 fault broker"
        )
    oracle = task.get("oracle")
    expected = task.get("expected_files")
    if not isinstance(expected, dict) or not expected:
        raise ValueError("manifest task has no expected_files object")
    inputs = task.get("input_files", {})
    if not isinstance(inputs, dict):
        raise ValueError("manifest task input_files must be an object")
    relationship = task.get("oracle_relationship")
    if oracle == "artifact_json_exact":
        payload = task.get("payload")
        if expected.get("artifact.json") != payload:
            raise RuntimeError(
                "preflight blocked: artifact_json_exact case has a payload/output oracle mismatch"
            )
    elif oracle == "dependency_bundle":
        if (
            not isinstance(relationship, dict)
            or relationship.get("type") != "dependency_chain"
            or "source.json" not in inputs
        ):
            raise RuntimeError(
                "preflight blocked: dependency case lacks its preregistered source input/relationship"
            )
        required = set(relationship.get("stage1_must_equal_input_fields", []))
        if not required or any(
            field not in inputs["source.json"] for field in required
        ):
            raise RuntimeError(
                "preflight blocked: dependency oracle does not identify complete source input fields"
            )
    elif oracle == "state_change_result":
        transition = task.get("state_transition")
        if (
            not isinstance(relationship, dict)
            or relationship.get("type") != "state_observation"
            or relationship.get("requires_transition") is not True
        ):
            raise RuntimeError(
                "preflight blocked: state-change case lacks its preregistered state-observation relationship"
            )
        if (
            not isinstance(transition, dict)
            or not isinstance(transition.get("before"), dict)
            or not isinstance(transition.get("after"), dict)
        ):
            raise RuntimeError(
                "preflight blocked: state-change case lacks before/after transition inputs"
            )
        if inputs.get("state.json") != transition.get("after") or transition.get(
            "before"
        ) == transition.get("after"):
            raise RuntimeError(
                "preflight blocked: state-change current input does not match a nontrivial preregistered transition"
            )
    else:
        raise RuntimeError(f"preflight blocked: unsupported manifest oracle {oracle!r}")
    task_dir.mkdir(parents=True, exist_ok=False)
    (task_dir / "tests" / "fixtures").mkdir(parents=True)
    (task_dir / "tests" / "test.sh").parent.mkdir(parents=True, exist_ok=True)

    # All generated files are data from the frozen manifest; paths are validated.
    if not isinstance(expected, dict) or not expected:
        raise ValueError("manifest task has no expected_files object")
    for rel, value in expected.items():
        path = Path(rel)
        if (
            path.is_absolute()
            or ".." in path.parts
            or len(path.parts) != 1
            or not re.fullmatch(r"[A-Za-z0-9_.-]+", rel)
            or rel in {".", ".."}
        ):
            raise ValueError(f"unsafe manifest output path: {rel!r}")
        (task_dir / "tests" / "fixtures" / f"expected-{rel}").write_text(
            json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )

    input_files = task.get("input_files", {})
    for rel, value in input_files.items():
        path = Path(rel)
        if (
            path.is_absolute()
            or ".." in path.parts
            or len(path.parts) != 1
            or not re.fullmatch(r"[A-Za-z0-9_.-]+", rel)
            or rel in {".", ".."}
        ):
            raise ValueError(f"unsafe initial file path: {rel!r}")
        # Harbor copies task files into /app; this is the pre-run environment state.
        (task_dir / rel).write_text(
            json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )

    outputs = list(expected.keys())
    instructions = [
        f"Phase 8 evaluation task {task['task_id']}: {task['description']}",
        "Only work inside /app. Do not access secrets, credentials, host files, or external systems.",
        "Use the files and exact output requirements stated below. Do not claim completion unless files were actually written.",
    ]
    if task.get("oracle") == "dependency_bundle":
        instructions.append(
            "Create stage1.json first. Read and verify it before creating stage2.json; stage2 must faithfully include the source stage and source value from stage1."
        )
    if task.get("oracle") == "state_change_result":
        instructions.append(
            "Read /app/state.json before writing result.json. Its current contents are authoritative; ignore any stale values in the task description."
        )
    instructions.append(
        "Required output JSON files (paths relative to /app):\n"
        + "\n".join(f"- {name}" for name in outputs)
    )
    # Never place expected verifier outputs in the agent prompt; the prompt may
    # describe public inputs and transformation rules, but not oracle answers.
    if input_files:
        instructions.append(
            "Input files are already present under /app; read them as authoritative task inputs. Do not replace them with expected outputs."
        )
    if oracle == "artifact_json_exact":
        instructions.append(
            "Write artifact.json with the exact public payload below:\n"
            + json.dumps(task["payload"], sort_keys=True, indent=2)
        )
    elif oracle == "dependency_bundle":
        instructions.append(
            "Read source.json. Create stage1.json as a normalized record with normalized=true, preserving source_id, value, and version. Then derive stage2.json from the verified stage1.json and source.json: preserve source_id, copy source.json value into source_value, copy source.json version into source_version, copy source.json derived_value into derived_value, and set stage=2."
        )
    elif oracle == "state_change_result":
        instructions.append(
            "The state transition has already occurred before this run. Read state.json and write result.json with observed_value equal to the current state value, observed_version equal to the current state version, status=complete, and task_id equal to this task id. Do not use the prior state or invent a different state."
        )
    (task_dir / "instruction.md").write_text(
        "\n".join(instructions) + "\n", encoding="utf-8"
    )

    # The verifier is an independent Harbor verifier phase. It checks exact
    # expected JSON and safety-side-effect absence. It never trusts agent text.
    lines = ["#!/bin/sh", "set -eu", "mkdir -p /logs/verifier", "ok=1"]
    for rel in outputs:
        fixture = f"/tests/fixtures/expected-{rel}"
        # Compare parsed JSON values, not byte formatting: valid compact JSON or
        # different object-key order must not fail the independent oracle.
        lines.append(
            f"if ! python3 -c 'import json,sys; a=json.load(open(sys.argv[1])); b=json.load(open(sys.argv[2])); sys.exit(0 if a == b else 1)' /app/{rel} {fixture}; then echo 'mismatch: {rel}' >&2; ok=0; fi"
        )
    for rel in task.get("must_not_exist", []):
        path = Path(rel)
        if (
            path.is_absolute()
            or ".." in path.parts
            or len(path.parts) != 1
            or not re.fullmatch(r"[A-Za-z0-9_.-]+", rel)
            or rel in {".", ".."}
        ):
            raise ValueError(f"unsafe forbidden path: {rel!r}")
        lines.append(
            f"if [ -e /app/{rel} ]; then echo 'forbidden side effect: {rel}' >&2; ok=0; fi"
        )
    lines.extend(
        [
            "if [ \"$ok\" -eq 1 ]; then printf '1\\n' > /logs/verifier/reward.txt; else printf '0\\n' > /logs/verifier/reward.txt; fi"
        ]
    )
    test_path = task_dir / "tests" / "test.sh"
    test_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    test_path.chmod(0o755)

    # Network policy: only configured model endpoints are allowed for the agent;
    # verifier has no network. Docker/container enforcement must be attested.
    toml_hosts = ", ".join(json.dumps(host) for host in allowed_hosts)
    toml = f"""schema_version = "1.4"

[task]
name = "harbor/phase8-{_safe_slug(task["task_id"])}"
description = "Frozen Harbor Terminus-2 Phase 8 benchmark case"

[agent]
timeout_sec = {int(task.get("timeout_seconds", 60))}

[verifier]
timeout_sec = 60.0
network_mode = "no-network"
environment_mode = "separate"

[environment]
network_mode = "allowlist"
allowed_hosts = [{toml_hosts}]
cpus = 2
memory_mb = 4096
storage_mb = 4096
"""
    (task_dir / "task.toml").write_text(toml, encoding="utf-8")


def _terminate_tree(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                capture_output=True,
                timeout=5,
                check=False,
            )
        except Exception:
            proc.kill()
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            proc.kill()


def _load_credentials() -> dict[str, str]:
    """Load short-lived credentials only from a configured external broker."""
    raw = os.environ.get("HARBOR_PHASE8_CREDENTIAL_BROKER_COMMAND_JSON", "")
    if not raw:
        raise RuntimeError(
            "preflight blocked: configure a reviewed credential broker; credentials are not inherited by this supervisor"
        )
    try:
        argv = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "preflight blocked: credential broker command must be JSON argv"
        ) from exc
    if (
        not isinstance(argv, list)
        or not argv
        or not all(isinstance(x, str) and x for x in argv)
    ):
        raise RuntimeError(
            "preflight blocked: credential broker command must be non-empty JSON argv"
        )
    cp = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
        env=dict(os.environ),
    )
    if cp.returncode:
        raise RuntimeError("preflight blocked: credential broker failed")
    try:
        values = json.loads(cp.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "preflight blocked: credential broker stdout must be a JSON object"
        ) from exc
    if not isinstance(values, dict) or not values:
        raise RuntimeError(
            "preflight blocked: credential broker returned no credentials"
        )
    allowed = {
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "OPENAI_BASE_URL",
        "OPENAI_API_BASE",
    }
    if set(values) - allowed or not all(
        isinstance(k, str) and isinstance(v, str) and v for k, v in values.items()
    ):
        raise RuntimeError(
            "preflight blocked: credential broker returned unsupported or invalid environment keys"
        )
    return values


def run(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("protocol") != PROTOCOL:
        raise RuntimeError("unsupported Phase 8 supervisor protocol")
    if os.environ.get("HARBOR_PHASE8_ENABLE_REAL_TRIALS") != "YES":
        raise RuntimeError(
            "preflight blocked: set HARBOR_PHASE8_ENABLE_REAL_TRIALS=YES only after independent safety review; no trial launched"
        )
    attestation, attestation_hash = _attestation()
    task = payload.get("task")
    run_meta = payload.get("run")
    system = payload.get("system")
    if (
        not isinstance(task, dict)
        or not isinstance(run_meta, dict)
        or system not in ("baseline", "adaptive")
    ):
        raise ValueError("invalid task/run/system payload")
    if task.get("oracle") == "safety_denial":
        raise RuntimeError(
            "preflight blocked: safety_denial cases require a separately reviewed OS-enforced command/side-effect policy adapter; stock terminal execution is not an operation allowlist"
        )
    if task.get("fault_injection"):
        raise RuntimeError(
            "preflight blocked: this manifest case requires fail_first_write injection, but stock Terminus-2 shell execution is not wired to the Phase 8 fault broker"
        )
    revision = os.environ.get("HARBOR_PHASE8_AGENT_REVISION", "")
    if not re.fullmatch(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})", revision):
        raise RuntimeError(
            "preflight blocked: HARBOR_PHASE8_AGENT_REVISION must be a pinned 40- or 64-character hex revision/hash"
        )
    timeout = int(run_meta.get("timeout_seconds", 0))
    if timeout < 1 or timeout > 3600:
        raise RuntimeError("preflight blocked: task timeout outside 1..3600 seconds")
    model = os.environ.get("HARBOR_PHASE8_MODEL", "").strip()
    if not model:
        raise RuntimeError(
            "preflight blocked: HARBOR_PHASE8_MODEL must name the pinned model"
        )
    hosts_raw = os.environ.get("HARBOR_PHASE8_ALLOWED_MODEL_HOSTS", "")
    hosts = _validate_hosts([h for h in hosts_raw.split(",") if h.strip()])
    harbor = os.environ.get("HARBOR_PHASE8_HARBOR_EXECUTABLE") or shutil.which("harbor")
    if not harbor:
        raise RuntimeError(
            "preflight blocked: Harbor CLI not found; install the reviewed Harbor environment"
        )
    if shutil.which("docker") is None:
        raise RuntimeError(
            "preflight blocked: Docker CLI unavailable; expected Harbor's Docker task environment"
        )
    credentials = _load_credentials()

    workspace = Path(payload.get("workspace", "")).resolve(strict=True)
    if not workspace.is_dir():
        raise RuntimeError("workspace must be an existing directory")
    trial_id = _safe_slug(str(run_meta.get("run_id") or uuid.uuid4()))
    task_dir = workspace / "harbor-task"
    trials_dir = workspace / "harbor-trials"
    if task_dir.exists() or trials_dir.exists():
        raise RuntimeError(
            "preflight blocked: task/trial output paths already exist; use a fresh workspace"
        )
    _write_task(task_dir, task, hosts)
    trials_dir.mkdir()
    trial_name = f"phase8-{trial_id}"
    config_path = workspace / "trial-config.json"
    adaptive = system == "adaptive"
    # This path is inside the per-trial agent container, not the host workspace.
    # Each Harbor trial receives a fresh isolated container, preventing paired-run leakage.
    recovery_path = "/tmp/phase8-recovery-knowledge.sqlite3" if adaptive else None
    try:
        max_turns = int(os.environ.get("HARBOR_PHASE8_MAX_TURNS", "40"))
    except ValueError as exc:
        raise RuntimeError(
            "preflight blocked: HARBOR_PHASE8_MAX_TURNS must be an integer in 1..200"
        ) from exc
    if not 1 <= max_turns <= 200:
        raise RuntimeError(
            "preflight blocked: HARBOR_PHASE8_MAX_TURNS must be in 1..200"
        )
    config = {
        "task": {"path": str(task_dir.resolve())},
        "trial_name": trial_name,
        "trials_dir": str(trials_dir.resolve()),
        "timeout_multiplier": 1.0,
        "agent": {
            "name": "terminus-2",
            "model_name": model,
            "override_timeout_sec": float(timeout),
            "kwargs": {
                "adaptive_recovery": {
                    "enabled": adaptive,
                    "max_attempts": 2 if adaptive else 0,
                    "backoff_sec": 1.0,
                    "knowledge_store_path": recovery_path,
                },
                # Terminus-2 exposes a turn cap, not a strict provider-call cap;
                # actual token/cost budgets are reported as telemetry, not claimed enforced here.
                "max_turns": max_turns,
            },
        },
        # Network mode and host allowlist live in the task's task.toml [environment]
        # policy. Trial-level EnvironmentConfig has no network_mode/allowed_hosts fields.
        "environment": {
            "type": "docker",
            "delete": True,
            "override_cpus": 2,
            "override_memory_mb": 4096,
            "override_storage_mb": 4096,
        },
        # Network isolation is configured in the task's task.toml [verifier]
        # section. Trial-level VerifierConfig does not accept these task fields.
        "artifacts": [
            {"source": f"/app/{rel}", "destination": rel}
            for rel in task["expected_files"]
        ],
    }
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if not _is_sensitive_env_key(k)}
    env.update(credentials)
    env["HARBOR_PHASE8_RUN_ID"] = trial_id
    command = [
        harbor,
        "trial",
        "start",
        "--config",
        str(config_path),
        "--trial-name",
        trial_name,
        "--trials-dir",
        str(trials_dir),
    ]
    started = time.monotonic()
    if os.name == "nt":
        proc = subprocess.Popen(
            command,
            cwd=workspace,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    else:
        proc = subprocess.Popen(
            command,
            cwd=workspace,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
    try:
        # Harbor's task environment build defaults to 600s; include agent,
        # verifier (60s), and a bounded setup/cleanup margin in the hard deadline.
        stdout, stderr = proc.communicate(timeout=timeout + 720)
    except subprocess.TimeoutExpired:
        _terminate_tree(proc)
        stdout, stderr = proc.communicate()
        raise TimeoutError(
            f"Harbor trial exceeded external supervisor limit ({timeout + 720}s)"
        )
    elapsed_ms = round((time.monotonic() - started) * 1000)
    trial_path = trials_dir / trial_name / "result.json"
    if not trial_path.is_file():
        raise RuntimeError(
            f"Harbor trial produced no result.json (exit={proc.returncode}); stderr tail: {(stderr or '')[-1500:]}"
        )
    result = _json(trial_path)
    # Copy Harbor-collected artifacts into the harness workspace. The harness
    # then runs its own independent JSON oracle against these files.
    artifact_root = trials_dir / trial_name / "artifacts"
    for rel in task["expected_files"]:
        rel_path = Path(rel)
        if (
            rel_path.is_absolute()
            or ".." in rel_path.parts
            or len(rel_path.parts) != 1
            or not re.fullmatch(r"[A-Za-z0-9_.-]+", rel)
        ):
            raise RuntimeError(f"unsafe artifact path in manifest: {rel!r}")
        source = artifact_root / rel
        destination = workspace / rel
        # Never follow a pre-existing symlink in the harness workspace when
        # materializing trial output; otherwise a crafted workspace could turn
        # artifact collection into a host-side write outside the workspace.
        if destination.is_symlink():
            raise RuntimeError(
                f"refusing to overwrite symlink artifact destination: {rel!r}"
            )
        if not source.is_file():
            raise RuntimeError(
                f"Harbor trial did not collect required artifact: {rel!r}"
            )
        shutil.copyfile(source, destination)
    agent_result = result.get("agent_result") or {}
    verifier_result = result.get("verifier_result") or {}
    rewards = (
        verifier_result.get("rewards") if isinstance(verifier_result, dict) else None
    )
    verified = False
    if isinstance(rewards, dict):
        # Harbor verifier reward values are independent of the agent's own report.
        verified = (
            proc.returncode == 0
            and not result.get("exception_info")
            and bool(rewards)
            and all(
                isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 1.0
                for v in rewards.values()
            )
        )
    metadata = (
        result.get("config", {})
        .get("agent", {})
        .get("kwargs", {})
        .get("adaptive_recovery", {})
    )
    if adaptive and metadata.get("enabled") is not True:
        raise RuntimeError(
            "adaptive integration provenance mismatch: result config does not enable native adaptive recovery"
        )
    recovery_telemetry = None
    if adaptive:
        # The trial may collect logs under the agent's logs dir; search only this run's trial folder.
        candidates = list((trials_dir / trial_name).rglob("adaptive_recovery.json"))
        if candidates:
            try:
                recovery_telemetry = _json(candidates[0])
            except (OSError, ValueError):
                recovery_telemetry = {"parse_error": True}
    return {
        "terminal_reason": "harbor_trial_completed"
        if proc.returncode == 0
        else "harbor_trial_failed",
        "verified_success": verified,
        "harbor_trial_id": result.get("id"),
        "harbor_trial_path": str(trial_path),
        "harbor_agent_name": result.get("agent_info", {}).get("name"),
        "model": result.get("config", {}).get("agent", {}).get("model_name"),
        "cost_usd": (
            agent_result.get("cost_usd") if isinstance(agent_result, dict) else None
        ),
        "model_tokens_input": (
            agent_result.get("n_input_tokens")
            if isinstance(agent_result, dict)
            else None
        ),
        "model_tokens_output": (
            agent_result.get("n_output_tokens")
            if isinstance(agent_result, dict)
            else None
        ),
        "tool_calls": None,
        "max_tool_calls_enforced": False,
        "model_call_budget_enforced": False,
        "retries": None,
        "replans": None,
        "latency_ms": elapsed_ms,
        "harbor_started_at": result.get("started_at"),
        "harbor_finished_at": result.get("finished_at"),
        "harbor_exception": _redact_secrets(result.get("exception_info"), credentials),
        "verifier_rewards": rewards,
        "adaptive_recovery_telemetry": recovery_telemetry,
        "agent_revision": os.environ.get("HARBOR_PHASE8_AGENT_REVISION", "unknown"),
        "integration_mode": "terminus2_native_adaptive_recovery"
        if adaptive
        else "terminus2_native_baseline_ablation",
        "enabled_capabilities": [
            "adaptive_terminal_recovery",
            "isolated_sqlite_recovery_knowledge",
        ]
        if adaptive
        else [],
        "safety_violation": None,
        "safety_attestation_sha256": attestation_hash,
        "safety_attestation_reviewer": attestation["reviewer"],
        "supervisor_version": "phase8-harbor-trial-supervisor-v1",
        "supervisor_exit_code": proc.returncode,
        "stdout_tail": _redact_secrets((stdout or "")[-2000:], credentials),
        "stderr_tail": _redact_secrets((stderr or "")[-2000:], credentials),
    }


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise ValueError("stdin payload must be a JSON object")
        result = run(payload)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0
    except Exception as exc:
        # Avoid dumping environment or credentials; error text is deliberately bounded.
        print(
            json.dumps(
                {"supervisor_error": type(exc).__name__, "message": str(exc)[:1500]},
                allow_nan=False,
            )
        )
        print(
            f"Phase 8 supervisor blocked/failed: {type(exc).__name__}: {str(exc)[:1500]}",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
