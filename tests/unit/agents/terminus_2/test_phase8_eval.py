"""Unit tests for the standalone Phase 8 evaluation harness; no empirical run."""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "scripts" / "terminus2_phase8_eval.py"
spec = importlib.util.spec_from_file_location("terminus2_phase8_eval", SCRIPT)
phase8 = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = phase8
spec.loader.exec_module(phase8)


def test_manifest_is_deterministic_and_has_100_cases():
    a, b = phase8.build_manifest(), phase8.build_manifest()
    assert a == b
    assert a["case_count"] == 100
    assert {
        c: sum(x["category"] == c for x in a["cases"]) for c in phase8.CATEGORIES
    } == {c: 20 for c in phase8.CATEGORIES}
    phase8.validate_manifest(a)
    without_hash = dict(a)
    claimed = without_hash.pop("content_sha256")
    assert (
        phase8.hashlib.sha256(phase8.canonical_json(without_hash)).hexdigest()
        == claimed
    )


def test_manifest_rejects_unsafe_allowlist():
    manifest = phase8.build_manifest()
    manifest["cases"][0]["allowed_operations"].append("shell")
    try:
        phase8.validate_manifest(manifest)
    except ValueError as exc:
        assert "unsafe operation" in str(exc)
    else:
        raise AssertionError("unsafe operation allowlist accepted")


def test_independent_verifier_checks_artifacts(tmp_path):
    task = phase8.build_manifest()["cases"][0]
    good = {
        "task_id": task["task_id"],
        "record_number": 1,
        "status": "complete",
        "checksum_input": "terminus2:routine:1",
    }
    phase8.write_json(tmp_path / "artifact.json", good)
    assert phase8.verify_case(task, tmp_path, {})["passed"]
    phase8.write_json(tmp_path / "artifact.json", {"status": "agent claims success"})
    result = phase8.verify_case(task, tmp_path, {"verified_success": True})
    assert not result["passed"]
    assert "content mismatch: artifact.json" in result["errors"]


def test_verifier_detects_safety_side_effect_and_requires_denial(tmp_path):
    task = next(
        x for x in phase8.build_manifest()["cases"] if x["category"] == "safety"
    )
    for name, value in task["expected_files"].items():
        phase8.write_json(tmp_path / name, value)
    phase8.write_json(tmp_path / "credential_dump.json", {"fake": True})
    result = phase8.verify_case(task, tmp_path, {"reported_denied": False})
    assert not result["passed"]
    assert any("forbidden side effect" in e for e in result["errors"])
    assert any("did not report" in e for e in result["errors"])


def test_safe_child_blocks_traversal(tmp_path):
    for value in ("../escape.json", "/tmp/escape.json"):
        try:
            phase8.safe_child(tmp_path, value)
        except ValueError:
            pass
        else:
            raise AssertionError(f"unsafe path accepted: {value}")


def test_analysis_pairs_runs_and_reports_cluster_ci():
    rows = []
    for task_id, b, a in (
        ("routine-001", True, False),
        ("routine-002", False, True),
        ("routine-003", True, True),
    ):
        for system, success in (("baseline", b), ("adaptive", a)):
            rows.append(
                {
                    "pair_key": f"{task_id}::seed-11",
                    "task_id": task_id,
                    "category": "routine",
                    "system": system,
                    "verified_success": success,
                    "latency_ms": 100 if system == "baseline" else 120,
                    "cost_usd": 0.1,
                    "safety_incidents": [],
                    "run_id": f"{task_id}-{system}",
                }
            )
    report = phase8.analyze(rows, repetitions=200, seed=7)
    assert report["pair_count"] == 3
    assert report["success"]["difference_percentage_points"] == 0
    ci = report["success"]["cluster_bootstrap_95_ci_percentage_points"]
    assert ci["resamples"] == 200 and ci["clusters"] == 3
    assert ci["lower_95"] <= 0 <= ci["upper_95"]
    assert ci["lower_95"] == -100.0
    assert ci["upper_95"] == 100.0


def test_analysis_does_not_claim_comparison_without_pairs():
    report = phase8.analyze(
        [
            {
                "pair_key": "x",
                "task_id": "x",
                "system": "baseline",
                "verified_success": True,
            }
        ]
    )
    assert report["pair_count"] == 0
    assert "No complete" in report["note"]


def test_runner_smoke_writes_paired_jsonl_and_analysis(tmp_path):

    adapter = tmp_path / "fixture_adapter.py"
    adapter.write_text(
        """import json\nfrom pathlib import Path\ndef run_task(task, context):\n    root = Path(context["workspace"])\n    for name, value in task.get("expected_files", {}).items():\n        path = root / name\n        path.parent.mkdir(parents=True, exist_ok=True)\n        path.write_text(json.dumps(value), encoding="utf-8")\n    return {"terminal_reason": "fixture_only", "reported_denied": True, "cost_usd": 0.0, "tool_calls": 1, "retries": 0, "actions": []}\n""",
        encoding="utf-8",
    )
    manifest_path = tmp_path / "manifest.json"
    phase8.write_json(manifest_path, phase8.build_manifest())
    out = tmp_path / "run"
    command = [
        sys.executable,
        str(SCRIPT),
        "run",
        "--manifest",
        str(manifest_path),
        "--baseline-adapter",
        str(adapter),
        "--adaptive-adapter",
        str(adapter),
        "--output-dir",
        str(out),
        "--seeds",
        "11",
        "--max-cases",
        "1",
        "--random-seed",
        "4",
    ]
    result = __import__("subprocess").run(
        command, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    rows = [json.loads(x) for x in (out / "results.jsonl").read_text().splitlines()]
    assert len(rows) == 2
    assert {r["system"] for r in rows} == {"baseline", "adaptive"}
    assert all(r["verified_success"] for r in rows)
    report_path = out / "analysis.json"
    result = __import__("subprocess").run(
        [
            sys.executable,
            str(SCRIPT),
            "analyze",
            "--results",
            str(out / "results.jsonl"),
            "--output",
            str(report_path),
            "--bootstrap-resamples",
            "100",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(report_path.read_text())
    assert report["pair_count"] == 1
    assert report["success"]["difference_percentage_points"] == 0
    # This fixture-only test proves runner plumbing, not agent performance.


def test_fault_injection_hook_is_one_shot_and_logged(tmp_path):
    task = next(
        x for x in phase8.build_manifest()["cases"] if x["category"] == "recovery"
    )

    def adapter(task, context):
        assert context["consume_fault"]("fail_first_write") is True
        assert context["consume_fault"]("fail_first_write") is False
        for name, value in task["expected_files"].items():
            phase8.write_json(Path(context["workspace"]) / name, value)
        return {"terminal_reason": "objective_completed", "cost_usd": 0.0}

    row = phase8.run_one(
        task, "baseline", adapter, "fixture-hash", 11, tmp_path, {}, True
    )
    assert row["verified_success"]
    assert len(row["fault_events"]) == 1
    assert row["fault_events"][0]["type"] == "fail_first_write"


def _load_supervised_adapter(name: str):
    import importlib.util

    adapter_path = ROOT / "benchmarks" / "terminus2-phase8" / "adapters" / name
    bridge_path = adapter_path.parent / "supervised_process_adapter.py"
    bridge_spec = importlib.util.spec_from_file_location(
        "supervised_process_adapter", bridge_path
    )
    bridge = importlib.util.module_from_spec(bridge_spec)
    assert bridge_spec and bridge_spec.loader
    sys.modules[bridge_spec.name] = bridge
    bridge_spec.loader.exec_module(bridge)
    spec = importlib.util.spec_from_file_location(f"test_{name[:-3]}", adapter_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module, bridge


def test_supervised_adapter_fails_closed_without_command_or_attestation(
    monkeypatch, tmp_path
):
    module, bridge = _load_supervised_adapter("baseline_adapter.py")
    monkeypatch.delenv("HARBOR_PHASE8_BASELINE_COMMAND_JSON", raising=False)
    monkeypatch.delenv("HARBOR_PHASE8_SAFETY_ATTESTATION", raising=False)
    task = phase8.build_manifest()["cases"][0]
    context = {"workspace": str(tmp_path), "timeout_seconds": 60}
    try:
        module.run_task(task, context)
    except RuntimeError as exc:
        assert "preflight blocked" in str(exc)
        assert "no run launched" in str(exc)
    else:
        raise AssertionError(
            "adapter should fail closed without reviewed runner configuration"
        )


def test_supervised_adapter_requires_all_attested_controls(monkeypatch, tmp_path):
    module, bridge = _load_supervised_adapter("baseline_adapter.py")
    attestation = tmp_path / "attestation.json"
    attestation.write_text(json.dumps({"network_disabled": True}), encoding="utf-8")
    monkeypatch.setenv(
        "HARBOR_PHASE8_BASELINE_COMMAND_JSON",
        json.dumps([sys.executable, "-c", "print('{}')"]),
    )
    monkeypatch.setenv("HARBOR_PHASE8_SAFETY_ATTESTATION", str(attestation))
    try:
        bridge._preflight("baseline", tmp_path, 60)
    except RuntimeError as exc:
        assert "missing required true controls" in str(exc)
    else:
        raise AssertionError("incomplete safety attestation should block execution")


def test_supervised_adaptive_adapter_requires_integration_provenance(
    monkeypatch, tmp_path
):
    module, bridge = _load_supervised_adapter("adaptive_adapter.py")
    attestation = {
        "network_policy_enforced": True,
        "verifier_network_disabled": True,
        "credentials_mounted": False,
        "workspace_only_write_mount": True,
        "hard_timeout_enforced": True,
        "tool_allowlist_enforced_outside_model": True,
        "approval_gate_enforced_before_side_effect": True,
        "audit_log_enabled": True,
        "reviewer": "test-reviewer",
        "reviewed_at": "2026-10-23T00:00:00Z",
        "supervisor_version": "test-1",
        "policy_evidence_ref": "test-evidence-reference",
    }
    attestation_path = tmp_path / "attestation.json"
    attestation_path.write_text(json.dumps(attestation), encoding="utf-8")
    child = tmp_path / "runner.py"
    child.write_text(
        "import json; print(json.dumps({'terminal_reason':'objective_completed'}))",
        encoding="utf-8",
    )
    monkeypatch.setenv(
        "HARBOR_PHASE8_ADAPTIVE_COMMAND_JSON", json.dumps([sys.executable, str(child)])
    )
    monkeypatch.setenv("HARBOR_PHASE8_SAFETY_ATTESTATION", str(attestation_path))
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    task = phase8.build_manifest()["cases"][0]
    context = {
        "workspace": str(workspace),
        "timeout_seconds": 60,
        "run_id": "r",
        "seed": 11,
        "allowed_operations": [],
        "max_tool_calls": 10,
        "max_model_calls": 10,
        "monetary_budget_usd": 1.0,
        "fault_injection": None,
        "safety": {
            "network_allowed": False,
            "credentials_available": False,
            "external_side_effects_allowed": False,
        },
    }
    try:
        module.run_task(task, context)
    except RuntimeError as exc:
        assert "missing integration provenance" in str(exc)
    else:
        raise AssertionError(
            "adaptive adapter must require revision/integration/capability provenance"
        )


def test_supervised_adapter_rejects_example_attestation_placeholders(
    monkeypatch, tmp_path
):
    _, bridge = _load_supervised_adapter("baseline_adapter.py")
    attestation = {
        "network_policy_enforced": True,
        "verifier_network_disabled": True,
        "credentials_mounted": False,
        "workspace_only_write_mount": True,
        "hard_timeout_enforced": True,
        "tool_allowlist_enforced_outside_model": True,
        "approval_gate_enforced_before_side_effect": True,
        "audit_log_enabled": True,
        "reviewer": "REPLACE_WITH_REVIEWER",
        "reviewed_at": "REPLACE_WITH_ISO8601_TIMESTAMP",
        "supervisor_version": "REPLACE_WITH_PINNED_VERSION",
        "policy_evidence_ref": "REPLACE_WITH_EVIDENCE",
    }
    path = tmp_path / "attestation.json"
    path.write_text(json.dumps(attestation), encoding="utf-8")
    monkeypatch.setenv(
        "HARBOR_PHASE8_BASELINE_COMMAND_JSON",
        json.dumps([sys.executable, "-c", "print('{}')"]),
    )
    monkeypatch.setenv("HARBOR_PHASE8_SAFETY_ATTESTATION", str(path))
    try:
        bridge._preflight("baseline", tmp_path, 60)
    except RuntimeError as exc:
        assert "placeholders are not accepted" in str(exc)
    else:
        raise AssertionError("example attestation placeholders must not pass preflight")


def test_supervised_baseline_adapter_invokes_process_and_returns_telemetry(
    monkeypatch, tmp_path
):
    module, bridge = _load_supervised_adapter("baseline_adapter.py")
    attestation = {
        "network_policy_enforced": True,
        "verifier_network_disabled": True,
        "credentials_mounted": False,
        "workspace_only_write_mount": True,
        "hard_timeout_enforced": True,
        "tool_allowlist_enforced_outside_model": True,
        "approval_gate_enforced_before_side_effect": True,
        "audit_log_enabled": True,
        "reviewer": "test-reviewer",
        "reviewed_at": "2026-10-23T00:00:00Z",
        "supervisor_version": "test-1",
        "policy_evidence_ref": "test-evidence-reference",
    }
    attestation_path = tmp_path / "attestation.json"
    attestation_path.write_text(json.dumps(attestation), encoding="utf-8")
    child = tmp_path / "runner.py"
    child.write_text(
        "import json; print(json.dumps({'terminal_reason':'objective_completed','cost_usd':0.2,'actions':[]}))",
        encoding="utf-8",
    )
    monkeypatch.setenv(
        "HARBOR_PHASE8_BASELINE_COMMAND_JSON", json.dumps([sys.executable, str(child)])
    )
    monkeypatch.setenv("HARBOR_PHASE8_SAFETY_ATTESTATION", str(attestation_path))
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    task = phase8.build_manifest()["cases"][0]
    context = {
        "workspace": str(workspace),
        "timeout_seconds": 60,
        "run_id": "r",
        "seed": 11,
        "allowed_operations": [],
        "max_tool_calls": 10,
        "max_model_calls": 10,
        "monetary_budget_usd": 1.0,
        "fault_injection": None,
        "safety": {
            "network_allowed": False,
            "credentials_available": False,
            "external_side_effects_allowed": False,
        },
    }
    result = module.run_task(task, context)
    assert result["adapter_boundary"] == "supervised_subprocess"
    assert result["cost_usd"] == 0.2
    assert result["safety_attestation"]["attestation_reviewer"] == "test-reviewer"


def _load_harbor_supervisor():
    path = (
        ROOT
        / "benchmarks"
        / "terminus2-phase8"
        / "adapters"
        / "harbor_trial_supervisor.py"
    )
    spec = importlib.util.spec_from_file_location("harbor_trial_supervisor_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_harbor_supervisor_generates_harbor_task_and_independent_verifier(tmp_path):
    supervisor = _load_harbor_supervisor()
    task = next(
        c for c in phase8.build_manifest()["cases"] if c["task_id"] == "routine-001"
    )
    task_dir = tmp_path / "task"
    supervisor._write_task(task_dir, task, ["api.example.test"])
    assert 'network_mode = "allowlist"' in (task_dir / "task.toml").read_text()
    assert 'network_mode = "no-network"' in (task_dir / "task.toml").read_text()
    test_script = (task_dir / "tests" / "test.sh").read_text()
    assert "python3 -c" in test_script
    assert "json.load" in test_script
    assert (task_dir / "tests" / "fixtures" / "expected-artifact.json").is_file()
    import tomllib
    import subprocess
    import shutil

    parsed = tomllib.loads((task_dir / "task.toml").read_text())
    assert parsed["environment"]["allowed_hosts"] == ["api.example.test"]
    assert parsed["verifier"]["network_mode"] == "no-network"
    assert parsed["verifier"]["environment_mode"] == "separate"
    if shutil.which("sh"):
        syntax = subprocess.run(
            ["sh", "-n", str(task_dir / "tests" / "test.sh")],
            capture_output=True,
            text=True,
        )
        assert syntax.returncode == 0, syntax.stderr


def test_harbor_supervisor_blocks_real_trials_without_explicit_opt_in(monkeypatch):
    supervisor = _load_harbor_supervisor()
    monkeypatch.delenv("HARBOR_PHASE8_ENABLE_REAL_TRIALS", raising=False)
    try:
        supervisor.run({"protocol": supervisor.PROTOCOL})
    except RuntimeError as exc:
        assert "no trial launched" in str(exc)
    else:
        raise AssertionError("supervisor must require explicit real-trial opt-in")


def test_harbor_supervisor_blocks_unsupported_safety_and_fault_cases(tmp_path):
    supervisor = _load_harbor_supervisor()
    manifest = phase8.build_manifest()
    safety = next(c for c in manifest["cases"] if c["category"] == "safety")
    recovery = next(c for c in manifest["cases"] if c["category"] == "recovery")
    for task, message in ((safety, "OS-enforced"), (recovery, "fault broker")):
        try:
            supervisor._write_task(
                tmp_path / task["task_id"], task, ["api.example.test"]
            )
        except RuntimeError as exc:
            assert message in str(exc)
        else:
            raise AssertionError(
                f"unsupported case {task['task_id']} should fail closed"
            )


def test_harbor_supervisor_validates_exact_model_hosts_and_deduplicates():
    supervisor = _load_harbor_supervisor()
    assert supervisor._validate_hosts(["API.Example.Test", "api.example.test."]) == [
        "api.example.test"
    ]
    for invalid in (
        ["*.example.test"],
        ["example.test/path"],
        ["bad host"],
        ["-bad.example"],
    ):
        try:
            supervisor._validate_hosts(invalid)
        except RuntimeError as exc:
            assert "preflight blocked" in str(exc)
        else:
            raise AssertionError(f"unsafe model host allowlist accepted: {invalid!r}")


def test_harbor_supervisor_scrubs_non_obvious_secret_environment_keys():
    supervisor = _load_harbor_supervisor()
    for key in (
        "OPENAI_API_KEY",
        "AWS_SECRET_ACCESS_KEY",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "AZURE_CLIENT_CERTIFICATE_PATH",
        "SSH_AUTH_SOCK",
        "DOCKER_CONFIG",
        "CUSTOM_AUTH_HEADER",
    ):
        assert supervisor._is_sensitive_env_key(key), key
    for key in ("PATH", "SYSTEMROOT", "HARBOR_PHASE8_MODEL", "LANG"):
        assert not supervisor._is_sensitive_env_key(key), key


def test_harbor_supervisor_trial_config_does_not_put_task_verifier_fields_in_trial_verifier():
    supervisor = _load_harbor_supervisor()
    source = (
        ROOT
        / "benchmarks"
        / "terminus2-phase8"
        / "adapters"
        / "harbor_trial_supervisor.py"
    ).read_text()
    # Harbor's trial-level VerifierConfig has no network_mode/environment_mode/timeout_sec
    # fields; those are correctly represented in generated task.toml instead.
    assert '"verifier": {"network_mode"' not in source
    assert (
        '"environment": {"type": "docker", "delete": True, "network_mode"' not in source
    )
    assert 'network_mode = "no-network"' in source
    assert 'environment_mode = "separate"' in source
    assert callable(supervisor._write_task)


def test_harbor_supervisor_generated_task_config_validates_against_harbor_schema(
    tmp_path,
):
    import importlib.metadata
    import tomllib

    # The isolated test environment may not have the full Harbor distribution
    # metadata or optional TOML/shortuuid dependencies, so provide only the
    # minimal compatibility shims needed to exercise Harbor's real TaskConfig.
    real_version = importlib.metadata.version
    importlib.metadata.version = lambda name: (
        "0.0.0" if name == "harbor" else real_version(name)
    )
    shortuuid = types.ModuleType("shortuuid")
    shortuuid.ShortUUID = type("ShortUUID", (), {})
    toml_module = types.ModuleType("toml")
    toml_module.loads = tomllib.loads
    toml_module.dumps = lambda value: ""
    old_shortuuid = sys.modules.get("shortuuid")
    old_toml = sys.modules.get("toml")
    sys.modules["shortuuid"] = shortuuid
    sys.modules["toml"] = toml_module
    try:
        sys.path.insert(0, str(ROOT / "src"))
        from harbor.models.task.config import TaskConfig

        supervisor = _load_harbor_supervisor()
        manifest = phase8.build_manifest()
        runnable = [
            c
            for c in manifest["cases"]
            if c["category"]
            in manifest["runnable_category_policy"][
                "runnable_with_current_harbor_supervisor"
            ]
        ]
        assert len(runnable) == 60
        for task in runnable:
            task_dir = tmp_path / task["task_id"]
            supervisor._write_task(task_dir, task, ["api.example.test"])
            config = TaskConfig.model_validate_toml(
                (task_dir / "task.toml").read_text(encoding="utf-8")
            )
            assert config.task is not None
            assert config.task.name == f"harbor/phase8-{task['task_id']}"
            assert config.environment.network_mode.value == "allowlist"
            assert config.verifier.network_mode.value == "no-network"
            assert config.verifier.environment_mode.value == "separate"
    finally:
        if old_shortuuid is None:
            sys.modules.pop("shortuuid", None)
        else:
            sys.modules["shortuuid"] = old_shortuuid
        if old_toml is None:
            sys.modules.pop("toml", None)
        else:
            sys.modules["toml"] = old_toml
        importlib.metadata.version = real_version


def test_harbor_supervisor_task_toml_has_agent_and_separate_offline_verifier(tmp_path):
    import tomllib

    supervisor = _load_harbor_supervisor()
    task = next(
        c for c in phase8.build_manifest()["cases"] if c["category"] == "routine"
    )
    task_dir = tmp_path / "task"
    supervisor._write_task(task_dir, task, ["api.example.test"])
    parsed = tomllib.loads((task_dir / "task.toml").read_text(encoding="utf-8"))
    assert parsed["schema_version"] == "1.4"
    assert parsed["environment"]["network_mode"] == "allowlist"
    assert parsed["environment"]["allowed_hosts"] == ["api.example.test"]
    assert parsed["verifier"]["network_mode"] == "no-network"
    assert parsed["verifier"]["environment_mode"] == "separate"
    assert parsed["verifier"]["timeout_sec"] == 60.0
    assert parsed["agent"]["timeout_sec"] == task["timeout_seconds"]


def test_harbor_supervisor_redacts_broker_secrets_from_telemetry():
    supervisor = _load_harbor_supervisor()
    secret = "sk-test-sensitive-value"
    payload = {
        "stdout": f"provider returned {secret}",
        "items": [f"{secret} was rejected"],
    }
    redacted = supervisor._redact_secrets(payload, {"OPENAI_API_KEY": secret})
    assert secret not in json.dumps(redacted)
    assert "<redacted>" in json.dumps(redacted)


def test_harbor_supervisor_never_exposes_oracle_expected_files_in_prompt(tmp_path):
    supervisor = _load_harbor_supervisor()
    task = next(
        c for c in phase8.build_manifest()["cases"] if c["task_id"] == "routine-001"
    )
    task_dir = tmp_path / "task"
    supervisor._write_task(task_dir, task, ["api.example.test"])
    instruction = (task_dir / "instruction.md").read_text(encoding="utf-8")
    assert json.dumps(task["payload"], sort_keys=True, indent=2) in instruction
    source = (
        ROOT
        / "benchmarks"
        / "terminus2-phase8"
        / "adapters"
        / "harbor_trial_supervisor.py"
    ).read_text()
    assert (
        "for name, value in expected.items():\n        instructions.append"
        not in source
    )
    assert "expected outputs" in source and "agent prompt" in source


def test_harbor_supervisor_instructions_match_dependency_and_state_oracles(tmp_path):
    supervisor = _load_harbor_supervisor()
    manifest = phase8.build_manifest()
    dependency = next(
        c for c in manifest["cases"] if c["oracle"] == "dependency_bundle"
    )
    state = next(c for c in manifest["cases"] if c["oracle"] == "state_change_result")
    for task in (dependency, state):
        task_dir = tmp_path / task["task_id"]
        supervisor._write_task(task_dir, task, ["api.example.test"])
        instruction = (task_dir / "instruction.md").read_text(encoding="utf-8")
        assert task["task_id"] in instruction
        for value in task["expected_files"].values():
            if task["oracle"] != "artifact_json_exact":
                assert json.dumps(value, sort_keys=True, indent=2) not in instruction
    dependency_instruction = (
        tmp_path / dependency["task_id"] / "instruction.md"
    ).read_text(encoding="utf-8")
    assert "normalized=true" in dependency_instruction
    assert "copy source.json derived_value into derived_value" in dependency_instruction
    state_instruction = (tmp_path / state["task_id"] / "instruction.md").read_text(
        encoding="utf-8"
    )
    assert "observed_value" in state_instruction
    assert "observed_version" in state_instruction
    assert "status=complete" in state_instruction


def test_harbor_supervisor_generates_dependency_and_state_tasks_with_explicit_inputs(
    tmp_path,
):
    supervisor = _load_harbor_supervisor()
    manifest = phase8.build_manifest()
    dependency = next(
        c for c in manifest["cases"] if c["oracle"] == "dependency_bundle"
    )
    state_change = next(
        c for c in manifest["cases"] if c["oracle"] == "state_change_result"
    )
    for task in (dependency, state_change):
        task_dir = tmp_path / task["task_id"]
        supervisor._write_task(task_dir, task, ["api.example.test"])
        instruction = (task_dir / "instruction.md").read_text(encoding="utf-8")
        for output_value in task["expected_files"].values():
            assert json.dumps(output_value, sort_keys=True, indent=2) not in instruction
        for rel in task["input_files"]:
            assert (task_dir / rel).is_file()
        for rel in task["expected_files"]:
            assert (task_dir / "tests" / "fixtures" / f"expected-{rel}").is_file()


def test_phase8_manifest_v2_reports_runnable_categories_honestly():
    manifest = phase8.build_manifest()
    phase8.validate_manifest(manifest)
    assert manifest["schema_version"] == "harbor-terminus2-phase8-manifest-v2"
    policy = manifest["runnable_category_policy"]
    assert policy["runnable_with_current_harbor_supervisor"] == [
        "routine",
        "dependencies",
        "state_change",
    ]
    assert set(policy["blocked_with_current_harbor_supervisor"]) == {
        "recovery",
        "safety",
    }
    assert all(
        "input_files" in c and "oracle_relationship" in c
        for c in manifest["cases"]
        if c["category"] in {"dependencies", "state_change"}
    )


def test_phase8_manifest_dependency_and_state_oracles_match_inputs():
    manifest = phase8.build_manifest()
    dependency = next(c for c in manifest["cases"] if c["category"] == "dependencies")
    assert (
        dependency["expected_files"]["stage1.json"]["source_id"]
        == dependency["input_files"]["source.json"]["source_id"]
    )
    assert (
        dependency["expected_files"]["stage2.json"]["source_value"]
        == dependency["input_files"]["source.json"]["value"]
    )
    assert (
        dependency["expected_files"]["stage2.json"]["derived_value"]
        == dependency["input_files"]["source.json"]["derived_value"]
    )
    state = next(c for c in manifest["cases"] if c["category"] == "state_change")
    assert state["input_files"]["state.json"] == state["state_transition"]["after"]
    assert state["state_transition"]["before"] != state["state_transition"]["after"]


def test_phase8_independent_oracles_enforce_dependency_and_state_relationships(
    tmp_path,
):
    manifest = phase8.build_manifest()
    dependency = next(c for c in manifest["cases"] if c["category"] == "dependencies")
    workspace = tmp_path / "dependency"
    workspace.mkdir()
    for rel, value in dependency["input_files"].items():
        (workspace / rel).write_text(json.dumps(value), encoding="utf-8")
    (workspace / "stage1.json").write_text(
        json.dumps(dependency["expected_files"]["stage1.json"]), encoding="utf-8"
    )
    (workspace / "stage2.json").write_text(
        json.dumps(dependency["expected_files"]["stage2.json"]), encoding="utf-8"
    )
    assert phase8.verify_case(dependency, workspace, {})["passed"]
    bad = json.loads((workspace / "stage2.json").read_text())
    bad["source_value"] = "tampered"
    (workspace / "stage2.json").write_text(json.dumps(bad), encoding="utf-8")
    assert not phase8.verify_case(dependency, workspace, {})["passed"]

    state = next(c for c in manifest["cases"] if c["category"] == "state_change")
    state_ws = tmp_path / "state"
    state_ws.mkdir()
    (state_ws / "state.json").write_text(
        json.dumps(state["input_files"]["state.json"]), encoding="utf-8"
    )
    (state_ws / "result.json").write_text(
        json.dumps(state["expected_files"]["result.json"]), encoding="utf-8"
    )
    assert phase8.verify_case(state, state_ws, {})["passed"]
    bad_result = json.loads((state_ws / "result.json").read_text())
    bad_result["observed_version"] = 1
    (state_ws / "result.json").write_text(json.dumps(bad_result), encoding="utf-8")
    assert not phase8.verify_case(state, state_ws, {})["passed"]


def test_phase8_runner_defaults_to_preregistered_runnable_categories(
    monkeypatch, tmp_path
):
    manifest = phase8.build_manifest()
    phase8.validate_manifest(manifest)
    runnable = set(
        manifest["runnable_category_policy"]["runnable_with_current_harbor_supervisor"]
    )
    assert manifest["runnable_case_count"] == sum(
        c["category"] in runnable for c in manifest["cases"]
    )
    assert manifest["runnable_case_count"] == 60
    assert {
        c["category"] for c in manifest["cases"] if c["category"] not in runnable
    } == {"recovery", "safety"}


def test_phase8_manifest_hash_includes_runnable_case_count():
    manifest = phase8.build_manifest()
    phase8.validate_manifest(manifest)
    claimed = manifest["content_sha256"]
    copy = dict(manifest)
    copy.pop("content_sha256")
    assert claimed == phase8.hashlib.sha256(phase8.canonical_json(copy)).hexdigest()
    copy["runnable_case_count"] += 1
    assert claimed != phase8.hashlib.sha256(phase8.canonical_json(copy)).hexdigest()


def test_harbor_supervisor_requires_collected_artifacts(tmp_path):
    supervisor = _load_harbor_supervisor()
    manifest = phase8.build_manifest()
    task = next(c for c in manifest["cases"] if c["category"] == "routine")
    task_dir = tmp_path / "task"
    supervisor._write_task(task_dir, task, ["api.example.test"])
    # The generated verifier fixture is present, but this test specifically
    # guards the supervisor's post-trial artifact contract by inspecting source.
    source = (
        ROOT
        / "benchmarks"
        / "terminus2-phase8"
        / "adapters"
        / "harbor_trial_supervisor.py"
    ).read_text()
    assert "Harbor trial did not collect required artifact" in source
    assert "exceeded external supervisor limit ({timeout + 720}s)" in source
