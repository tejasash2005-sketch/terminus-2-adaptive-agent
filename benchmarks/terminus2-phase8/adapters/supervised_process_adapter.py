"""Fail-closed bridge from the Phase 8 harness to a supervised Harbor runner.

The configured executable must be an operator-reviewed wrapper that launches the
actual Harbor trial in a disposable VM/container and returns JSON telemetry. This
module does not pretend the experimental AutonomousAgent is wired into the
Terminus2 interactive runtime; the adaptive wrapper must explicitly implement
and identify the intended integration.
"""

from __future__ import annotations

import json
import math
import os
import signal
import subprocess
from pathlib import Path
from typing import Any

_REQUIRED_ATTESTATIONS = {
    "network_policy_enforced": True,
    "verifier_network_disabled": True,
    "credentials_mounted": False,
    "workspace_only_write_mount": True,
    "hard_timeout_enforced": True,
    "tool_allowlist_enforced_outside_model": True,
    "approval_gate_enforced_before_side_effect": True,
    "audit_log_enabled": True,
}


def _preflight(
    system: str, workspace: Path, timeout_seconds: int
) -> tuple[list[str], dict[str, Any]]:
    command_var = f"HARBOR_PHASE8_{system.upper()}_COMMAND_JSON"
    attestation_var = "HARBOR_PHASE8_SAFETY_ATTESTATION"
    command_raw = os.environ.get(command_var, "")
    attestation_raw = os.environ.get(attestation_var, "")
    if not command_raw:
        raise RuntimeError(
            f"preflight blocked: {command_var} must be a JSON argv array; no run launched"
        )
    try:
        argv = json.loads(command_raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"preflight blocked: {command_var} is not valid JSON"
        ) from exc
    if (
        not isinstance(argv, list)
        or not argv
        or not all(isinstance(x, str) and x for x in argv)
    ):
        raise RuntimeError(
            f"preflight blocked: {command_var} must be a non-empty JSON array of strings"
        )
    if not attestation_raw:
        raise RuntimeError(
            f"preflight blocked: {attestation_var} is required; no run launched"
        )
    try:
        attestation_path = Path(attestation_raw).resolve(strict=True)
        attestation = json.loads(attestation_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RuntimeError(
            f"preflight blocked: safety attestation cannot be read: {type(exc).__name__}"
        ) from exc
    if not isinstance(attestation, dict):
        raise RuntimeError(
            "preflight blocked: safety attestation must be a JSON object"
        )
    missing = [
        key
        for key, expected in _REQUIRED_ATTESTATIONS.items()
        if attestation.get(key) is not expected
    ]
    if missing:
        raise RuntimeError(
            "preflight blocked: safety attestation missing required true controls: "
            + ", ".join(missing)
        )
    # The attestation is a human/operator declaration, not cryptographic proof.
    provenance = (
        attestation.get("reviewer"),
        attestation.get("reviewed_at"),
        attestation.get("supervisor_version"),
    )
    if not all(
        isinstance(value, str) and value.strip() and not value.startswith("REPLACE_")
        for value in provenance
    ):
        raise RuntimeError(
            "preflight blocked: attestation must identify reviewer, reviewed_at, and supervisor_version; example placeholders are not accepted"
        )
    if (
        not isinstance(attestation.get("policy_evidence_ref"), str)
        or not attestation["policy_evidence_ref"].strip()
        or attestation["policy_evidence_ref"].startswith("REPLACE_")
    ):
        raise RuntimeError(
            "preflight blocked: attestation must reference reviewed policy evidence"
        )
    if timeout_seconds < 1 or timeout_seconds > 3600:
        raise RuntimeError(
            "preflight blocked: task timeout outside adapter-supported range 1..3600 seconds"
        )
    return argv, {
        "attestation_sha256": __import__("hashlib")
        .sha256(attestation_path.read_bytes())
        .hexdigest(),
        "attestation_reviewer": str(attestation["reviewer"]),
        "supervisor_version": str(attestation["supervisor_version"]),
    }


def _terminate_process_tree(proc: subprocess.Popen[str]) -> None:
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


def run_supervised(
    task: dict[str, Any], context: dict[str, Any], system: str
) -> dict[str, Any]:
    workspace = Path(context["workspace"]).resolve(strict=True)
    if not workspace.is_dir():
        raise RuntimeError("preflight blocked: workspace is not a directory")
    task_timeout = int(context["timeout_seconds"])
    argv, attestation_meta = _preflight(system, workspace, task_timeout)
    payload = {
        "protocol": "harbor-terminus2-phase8-supervised-run-v1",
        "system": system,
        "task": task,
        "run": {
            k: context[k]
            for k in (
                "run_id",
                "seed",
                "allowed_operations",
                "timeout_seconds",
                "max_tool_calls",
                "max_model_calls",
                "monetary_budget_usd",
                "fault_injection",
                "safety",
            )
        },
        "workspace": str(workspace),
        "fault_hook_protocol": "The supervised wrapper must call the supplied fault broker immediately before a target write; see adapter-contract.md.",
    }
    # Harbor startup includes image build and verifier phases; the agent's timeout
    # is distinct from the external process-tree timeout.
    # The Harbor supervisor budgets up to 600s for environment build, 60s
    # verifier time, and an additional bounded cleanup margin beyond agent time.
    outer_timeout = task_timeout + 780
    child_env = {
        k: v
        for k, v in os.environ.items()
        if not k.upper().endswith(("_API_KEY", "_TOKEN", "_PASSWORD", "_SECRET"))
    }
    try:
        if os.name == "nt":
            proc = subprocess.Popen(
                argv,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=workspace,
                env=child_env,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )
        else:
            proc = subprocess.Popen(
                argv,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=workspace,
                env=child_env,
                start_new_session=True,
            )
        try:
            stdout, stderr = proc.communicate(
                json.dumps(payload, ensure_ascii=False, allow_nan=False),
                timeout=outer_timeout,
            )
        except subprocess.TimeoutExpired as exc:
            _terminate_process_tree(proc)
            stdout, stderr = proc.communicate()
            raise TimeoutError(
                f"supervised {system} process tree exceeded {outer_timeout} seconds; process tree terminated"
            ) from exc
    except OSError as exc:
        raise RuntimeError(
            f"supervised {system} runner could not be launched: {type(exc).__name__}"
        ) from exc
    if proc.returncode != 0:
        stderr_tail = (stderr or "")[-2000:]
        try:
            detail = json.loads(stdout or "{}")
            if isinstance(detail, dict) and detail.get("supervisor_error"):
                raise RuntimeError(
                    f"supervised {system} preflight/trial failed: {detail.get('message', '')[:1200]}"
                )
        except json.JSONDecodeError:
            pass
        raise RuntimeError(
            f"supervised {system} runner exited {proc.returncode}: {stderr_tail}"
        )
    try:
        result = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "supervised runner stdout must contain exactly one JSON object"
        ) from exc
    if not isinstance(result, dict):
        raise TypeError("supervised runner result must be a JSON object")
    # Never accept a runner's self-reported success as verification. The harness
    # still independently checks expected workspace artifacts.
    result["adapter_boundary"] = "supervised_subprocess"
    result["safety_attestation"] = attestation_meta
    result["supervisor_exit_code"] = proc.returncode
    if (
        not isinstance(result.get("cost_usd"), (int, float))
        or isinstance(result.get("cost_usd"), bool)
        or not math.isfinite(result["cost_usd"])
    ):
        result["cost_usd"] = None
    return result
