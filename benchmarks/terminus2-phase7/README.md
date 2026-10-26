# Terminus-2 Phase 7 release validation

Phase 7 adds strict autonomous-run configuration validation, JSON-safe execution
results, strict checkpoint restore validation, crash-safe unique temporary files,
cancellation checkpointing, and a repeated offline regression campaign.

## Run focused tests

From a fully installed Harbor checkout (including development dependencies):

```bash
uv run pytest tests/unit/agents/terminus_2/test_task_planner.py tests/unit/agents/terminus_2/test_orchestration.py tests/unit/agents/terminus_2/test_autonomous.py tests/unit/agents/terminus_2/test_benchmark_suite.py -q
uv run ruff check src/harbor/agents/terminus_2 tests/unit/agents/terminus_2 scripts/run_terminus2_benchmark_campaign.py
uv run python scripts/run_terminus2_benchmark_campaign.py --repetitions 10 --output artifacts/terminus2-phase7-campaign.json
```

The benchmark command runs six deterministic synthetic cases ten times (60 case
runs). It records per-case pass counts and min/median/mean/p95/max wall-clock
latency. The p95 is nearest-rank and should not be interpreted as a confidence
interval. Timing is machine-dependent and synthetic; it is not an external model
comparison or evidence of real-world task success.

## Archive validation

After creating the release ZIP, validate its CRCs, required files, duplicate and unsafe paths, and accidental cache/VCS inclusion:

```bash
uv run python scripts/validate_terminus2_archive.py dist/harbor-terminus2-adaptive-phase7.zip
```

The validator is intentionally conservative and checks archive structure only; it does not prove that the code works on every platform.

## Release checklist

- [ ] Focused tests pass in a normally installed Harbor environment.
- [ ] Ruff passes without auto-fixing unrelated upstream code.
- [ ] Existing Terminus-2 unit tests pass.
- [ ] The repeated campaign has no failed cases; retain its JSON report.
- [ ] Run the appropriate platform CI and broader suite; classify known platform,
      optional-dependency, Docker, and network-dependent failures separately.
- [ ] Verify ZIP integrity and required files before publishing.
- [ ] Do not report a real-model empirical result until an external model is run in
      a controlled, permissioned environment with repeatable task-level scoring.

This checklist is not a claim that all release checks have passed in every environment.
