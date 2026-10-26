# Harbor Terminus engineering audit report

> **Historical snapshot (2026-10-24).** This report describes the initial, pre-refresh audit state. The later approved default dependency refresh and completed Windows test evidence are reconciled in `FINAL_RELEASE_REVIEW.md`. Its statement that no dependency constraints or lock versions changed is true only for that initial audit interval, not for the subsequent refresh. Its OSV counts describe the pre-refresh lock. The comparison appendix is a tree-vs-upstream-tag comparison, not Git-authoritative authorship or status.

> **Subsequent maintainer confirmation.** The maintainer has confirmed that the embedded PostHog project belongs to Harbor and is intended to remain in this release. This records maintainer confirmation, not independent technical verification against PostHog project settings; the ownership findings below describe the state at the time of the initial audit.

Generated: 2026-10-24T20:41:18+05:30
OS: Windows-11-10.0.26200-SP0
Python on PATH: 3.13.17
Project Python: 3.13.17 in the existing .venv; .python-version specifies 3.13 and pyproject requires Python 3.12+.
Tools: uv 0.13.5; pytest 9.0.2; Ruff 0.15.17; ty 0.0.49; pip-audit 2.10.1; Git 2.55.0.windows.5; Docker client 29.9.2.

## Executive status

NOT READY for public publication at the time of this historical audit. The locked dependency inventory had OSV advisory matches, the full unit suite did not complete, type checking remained blocked by missing dependencies, telemetry ownership/visibility was unverified at that time, and the exact source archive revision was unknown. Lint, formatting, package builds, lock consistency, import, and static parsers passed as recorded below. The subsequent maintainer confirmation of PostHog ownership is recorded above.

## Scope, boundaries, and provenance

All writable project operations occurred inside the repository. A separate protected workspace was not inspected or modified. At the time of this 2026-10-24 audit, the extracted repository had no `.git` directory; Git was not initialized, and no staging, commit, push, release, or publication occurred. Git was initialized later; see `FINAL_RELEASE_REVIEW.md` and `PROVENANCE.md` for the later repository state and provenance limits.

README and project metadata identify upstream harbor-framework/harbor. Its v0.24.0 tag was queried read-only and cloned temporarily under ignored .uv-cache. It resolves to commit b53b8134e1241686dca7759af188f987ecc48e8b, matching pyproject version 0.24.0, but there is no evidence this ZIP came from that exact commit. The temporary checkout was clean and used only as a comparison reference.

Comparison excludes Git metadata, dependency/cache directories, virtual environments, and audit temp directories: active 3655 files; tag 3421 files; 238 current-only paths; 314 byte-different common paths (2 line-ending-only); 4 baseline-only paths. These are differences from the upstream tag, not actual Git untracked/tracked statuses. Actual statuses cannot be determined without workspace Git metadata.

The prior 23 formatted Python files were compared with this candidate tag: 22 are absent from the tag and the remaining terminus_2.py differs substantially. The tag cannot isolate formatting-only or earlier audit edits from the ZIP's own changes. The ZIP's exact source commit/archive hash is still needed.

## Repairs made

The root .gitignore retains its rules and now contains /dataset/ at line 229, .uv-cache/ at line 246, and .audit-*/ at line 247. /dataset/ replaces the ineffective-looking ./dataset entry; AGENTS.md documents a root local dataset directory. Git check-ignore verified hypothetical paths against the active working tree using the genuine temporary Git reference and --no-index. The .gitignore remains 5,405 bytes.

Ruff formatting and safe lint fixes were applied to these 23 Python files; this included the reported unused imports and two unused local assignments:
- benchmarks/terminus2-phase8/adapters/adaptive_adapter.py
- benchmarks/terminus2-phase8/adapters/baseline_adapter.py
- benchmarks/terminus2-phase8/adapters/harbor_trial_supervisor.py
- benchmarks/terminus2-phase8/adapters/supervised_process_adapter.py
- scripts/run_terminus2_benchmark_campaign.py
- scripts/terminus2_phase8_eval.py
- scripts/validate_terminus2_archive.py
- src/harbor/agents/terminus_2/adaptive_recovery.py
- src/harbor/agents/terminus_2/autonomous.py
- src/harbor/agents/terminus_2/benchmark_suite.py
- src/harbor/agents/terminus_2/failure_classifier.py
- src/harbor/agents/terminus_2/orchestration.py
- src/harbor/agents/terminus_2/task_planner.py
- src/harbor/agents/terminus_2/terminus_2.py
- src/harbor/agents/terminus_2/trajectory_evaluation.py
- tests/unit/agents/terminus_2/test_adaptive_recovery.py
- tests/unit/agents/terminus_2/test_autonomous.py
- tests/unit/agents/terminus_2/test_benchmark_suite.py
- tests/unit/agents/terminus_2/test_failure_classifier.py
- tests/unit/agents/terminus_2/test_orchestration.py
- tests/unit/agents/terminus_2/test_phase8_eval.py
- tests/unit/agents/terminus_2/test_task_planner.py
- tests/unit/agents/terminus_2/test_trajectory_evaluation.py

Type repairs added explicit validated string lists/maps and checkpoint-event fields in autonomous.py and task_planner.py, changed trajectory_evaluation.py to iterate only after list validation, and added override/protocol annotations in benchmark_suite.py. These changes reduced ty diagnostics from 54 to 40. Three Python 3.13 invalid-escape warnings were also fixed without changing intended runtime backslashes:
- adapters/dacode/parity/da_harbor_agent/agent/agents.py
- adapters/spider2-dbt/src/spider2_dbt/run_spider_agent_dbt.py
- adapters/webgen_bench/src/webgen_bench/task-template/tests/webvoyager/utils.py

No dependency manifest or lockfile versions changed. No telemetry key or external configuration was changed.

## Dependency installation and package integrity

The project uses uv and supports Python 3.12+; this copy specifies Python 3.13 and CI uses 3.13. The locked litellm==1.93.0 sdist requires maturin==1.9.4 and a Rust/PyO3 build. uv.lock lists Linux manylinux wheels only for this release; the Python 3.13 Windows binary-only dry-run reported no usable wheel. The sdist build failed because rustup has no configured Cargo toolchain. Rust was not installed.

A locked full sync first timed out fetching asttokens, which resolved on retry; it then failed at the litellm source build. A partial locked environment contains 329/330 packages, with litellm absent. A locked torch wheel installed successfully. No dependency constraints or lock versions changed.

Commands/results: uv lock --check --offline --no-cache PASS (330 packages resolved); uv pip install --dry-run --no-deps --only-binary :all: --python .venv/Scripts/python.exe litellm==1.93.0 FAIL (no usable Windows wheel); uv build --all-packages --out-dir .uv-cache/build-artifacts PASS for Harbor, harbor-atif2otel, harbor-langsmith, and harbor-rewardkit. The build warned that .uv-cache is inside the source tree and that the current uv version is outside a uv-build requirement; builds succeeded.

All 8 wheel/source distributions were inspected: zero .uv-cache, .venv, .audit-*, or __pycache__ paths were included. Importing harbor in the partial venv passed. uv.lock SHA-256: f3f4359458691a0a279aa489fbfb3a09dca3ebb8d34e587d7b4feff96479d51a.

## Security and privacy

The OSV audit covered 324 unique PyPI package pins in the main scan plus two tinker-cookbook versions separately. It returned 229 advisory records across 35 package versions; alias canonicalization yielded 148 identifiers. Aliases may duplicate advisory records, and matches do not establish exploitability. The set includes optional and development dependencies, not only the default runtime. The 35 matched package/version counts are:

| Package | Locked version | OSV records | Canonical IDs |
|---|---:|---:|---:|
| aiohttp | 3.14.3 | 8 | 8 |
| anyio | 4.12.1 | 4 | 2 |
| certifi | 2026.1.4 | 2 | 1 |
| claude-agent-sdk | 0.1.20 | 1 | 1 |
| cryptography | 46.0.3 | 13 | 7 |
| datasets | 4.5.0 | 2 | 1 |
| diskcache | 5.6.3 | 2 | 1 |
| filelock | 3.29.4 | 3 | 3 |
| fsspec | 2025.10.0 | 2 | 1 |
| h2 | 4.3.0 | 2 | 1 |
| hpack | 4.1.0 | 2 | 1 |
| langsmith | 0.8.8 | 1 | 1 |
| litellm | 1.93.0 | 2 | 1 |
| lxml | 6.0.2 | 2 | 1 |
| mcp | 1.25.0 | 7 | 4 |
| multidict | 6.7.0 | 2 | 1 |
| oauthlib | 3.3.1 | 4 | 2 |
| opentelemetry-api | 1.43.0 | 1 | 1 |
| paramiko | 3.5.1 | 2 | 1 |
| pillow | 12.2.0 | 67 | 54 |
| pyarrow | 22.0.0 | 2 | 1 |
| pyasn1 | 0.6.3 | 6 | 3 |
| pydantic-settings | 2.12.0 | 1 | 1 |
| pygments | 2.19.2 | 2 | 1 |
| pyjwt | 2.10.1 | 32 | 17 |
| pytest | 9.0.2 | 2 | 1 |
| requests | 2.32.5 | 2 | 1 |
| setuptools | 82.0.1 | 3 | 2 |
| soupsieve | 2.8.3 | 8 | 4 |
| starlette | 0.50.0 | 10 | 5 |
| torch | 2.10.0 | 2 | 2 |
| tornado | 6.5.4 | 18 | 11 |
| transformers | 5.5.4 | 4 | 2 |
| urllib3 | 2.7.0 | 6 | 3 |
| wheel | 0.45.1 | 2 | 1 |

The OSV scan used exact versions from uv.lock with pip-audit --disable-pip --no-deps --vulnerability-service osv. It sent package names/versions only, not source or secrets. The two tinker-cookbook versions had no matches. The lock remains unchanged by instruction; a reviewed security lock refresh is required before publication.

OSV matches litellm 1.93.0. GitHub advisory GHSA-3cv6-jpf6-8222 lists 1.93.0 as affected until 1.93.2 for authenticated LiteLLM Proxy request routing/credential exposure. GHSA-7hp6-4w63-5g45 also lists versions beginning at 1.91.0 in an affected proxy authentication range. Harbor source uses LiteLLM as a client library and has no litellm.proxy imports in the scanned source; applicability is conditional on operating that proxy feature, not established for Harbor's normal client flow. See https://github.com/advisories/GHSA-3cv6-jpf6-8222 and https://github.com/BerriAI/litellm/security/advisories/GHSA-7hp6-4w63-5g45.

Telemetry review: src/harbor/telemetry.py defines a PostHog project token at line 42 and sends it in a detached POST JSON body to the PostHog capture endpoint (lines 422-432). It is used as a public client-side event-capture token, not a secret API credential. At the time of this audit, ownership and intended public use were unverified. Subsequent maintainer confirmation records that the project belongs to Harbor and is intended to remain in this release; this is not independent technical verification against PostHog project settings. Telemetry is enabled by default; HARBOR_TELEMETRY values 0/false/no/off/disabled opt out (lines 45, 479-480). A random persistent installation ID is stored under the user config directory. Event properties are allowlisted; person profiles and GeoIP are disabled. Events can include job IDs, command path and flag names, platform/runtime, agent/model/provider names, dataset/public-repo refs, resources, counts, status, costs, tokens, durations, and reward. Raw prompts and exception text are not in the telemetry schema. docs-mintlify/telemetry/telemetry.mdx documents defaults, fields, identity, and opt-out and is broadly consistent with code. tests/conftest.py sets HARBOR_TELEMETRY=off; no PostHog event was sent by this audit.

Security handling incident: a diagnostic command accidentally emitted the literal PostHog value in tool output. It is intentionally omitted from this report and has not been repeated here. It was not sent to PostHog or the dependency scanner. At that time the owner needed to decide whether the client-side project token was intended for public use or should be rotated. The maintainer has since confirmed the project belongs to Harbor and the token is intended to remain in this release. No external credential was changed.

Pattern scan covered 3,310 text files in source, tests, packages, scripts, examples, adapters, and workflows. It found one PostHog-key-like literal in telemetry.py, one AWS access-key-shaped test sentinel, two private-key marker fixtures, and generic credential assignments consistent with examples, placeholders, and tests. No GitHub-token-shaped strings or credential-like filenames were found; no .env/private-key files were found by filename scan. Values are not included here.

## Static validation, docs, and CI

Python AST: 1,608 files, zero syntax errors. Python 3.13 SyntaxWarning-as-error parsing passed for the three repaired files. JSON: 262 files parsed, zero errors. TOML: 231 files; 195 genuine TOML parsed, 36 Harbor/Jinja templates deferred, zero other parse errors. YAML: 215/217 parsed; the two failures are raw Compose templates with unresolved placeholders at adapters/frontier-cs-algorithm/src/frontier_cs_algorithm/task-template/environment/docker-compose.yaml and adapters/swelancer/src/swelancer/task-template/environment/docker-compose.yaml. All GitHub Actions workflow YAML parsed.

Registry validation passed earlier: 80 datasets, 51,625 task entries, required formatting/metadata checks. Earlier Markdown audit checked 64 links across 341 Markdown files: zero genuine broken repository links; two generation-relative template links are unresolved outside their output context. Pixiu README registry path resolves to ../../registry.json. Dockerfiles/Compose templates were structurally inspected; 23 actual Compose files were valid and the two placeholder templates were deferred.

Ruff check passed across src, tests, packages, adapters, scripts, examples, benchmarks, apps, docs, docs-mintlify, and rfcs. Ruff format --check passed; 1,607 files already formatted. The three warning fixes passed targeted Ruff and SyntaxWarning-as-error parsing.

ty check was run with Python 3.13/Linux to match CI and reported 40 diagnostics: unresolved litellm imports, four optional smol module imports, and two litellm-dependent typing diagnostics in src/harbor/llms/utils.py. No Terminus-2 diagnostics remained after targeted repairs. A clean type-check result is BLOCKED until compatible dependencies are installed.

## Test results and environment blockers

| Category | Status | Evidence |
|---|---|---|
| Full unit execution | FAIL / INCOMPLETE | 11,917 items collected; 60 collection errors; 3 skips. Execution displayed extensive failures/errors and stalled at 99%; interrupted after no progress. No final execution summary was produced. |
| Unit collect-only | FAIL | pytest tests/unit/ --collect-only --continue-on-collection-errors -q --tb=no; exit 1; 11,917 collected, 60 errors, 3 skipped, 89.91 s. |
| Terminus-2 unit directory | BLOCKED | 9 collection errors caused by missing litellm imports; no complete execution. |
| Focused Antigravity | FAIL | 26 passed, 1 failed; first failure is ModuleNotFoundError: litellm; 1.99 s. |
| Telemetry tests | FAIL / BLOCKED | 23 passed, 7 failed; failures require missing litellm; 3.28 s. No live tracking request. |
| Integration/runtime | NOT RUN | Locked environment incomplete and Docker API unavailable; no integration-specific repair required. |
| Type check | FAIL / BLOCKED | 40 diagnostics as categorized above. |
| Shell syntax | BLOCKED | bash -n could not start WSL: Bash/Service/CreateInstance/E_ACCESSDENIED. |
| Docker-dependent tests | BLOCKED | docker version client started, but API returned permission denied at npipe:////./pipe/docker_engine; Docker config read also returned Access Denied. |
| Package build | PASS | Four packages built into 8 distributions; hygiene scan passed. |
| Phase 8 empirical benchmarks | NOT RUN | No empirical campaign, performance trial, or benchmark dataset was run. |

Full execution command: pytest tests/unit/ --continue-on-collection-errors -q -n 4 --dist worksteal --durations=20, with TEMP/TMP under a local Windows drive for the run. It did not complete and must not be treated as a pass. Individual execution totals are unavailable because no final summary was emitted.

## Ignore rules and workspace hygiene

Git check-ignore --no-index --verbose against the active working tree verified hypothetical dataset/, .venv, .uv-cache/, .audit-*/, __pycache__, build/, and .env.local paths. This verifies pattern behavior, not active tracked status; root Git metadata is absent. Existing exclusions cover bytecode, environments, build/distribution output, test/coverage caches, logs/databases, credentials/certificates, jobs/trials/tasks/datasets, local tools/configuration, and generated viewer files. Negations preserve examples/tasks, src/harbor/tasks, and apps/viewer.

The root dataset directory is absent. Existing .venv, .audit-pytest-temp, and .audit-unit-temp remain; the two audit temp dirs were pre-existing and empty. .pytest_cache, .ruff_cache, and .hypothesis were pre-existing and left intact. The audit-created .uv-cache still contains the temporary upstream clone, build products, OSV input/output, and pytest temp artifacts: recursive removal was rejected by the managed filesystem policy. The report-generation helper was removed. The pre-existing .venv and audit temp dirs were preserved. No user source, test, documentation, workflow, or project data was deleted.

Shell inventory previously found 371/377 shell files with CRLF; .gitattributes specifies LF for two scripts. No mass conversion was performed. No files larger than 100 MiB or accidental archives were found in the prior hygiene scan.

## Changed project files

Explicit source/configuration changes made by this audit (this report is new):
- .gitignore
- adapters/dacode/parity/da_harbor_agent/agent/agents.py
- adapters/spider2-dbt/src/spider2_dbt/run_spider_agent_dbt.py
- adapters/webgen_bench/src/webgen_bench/task-template/tests/webvoyager/utils.py
- benchmarks/terminus2-phase8/adapters/adaptive_adapter.py
- benchmarks/terminus2-phase8/adapters/baseline_adapter.py
- benchmarks/terminus2-phase8/adapters/harbor_trial_supervisor.py
- benchmarks/terminus2-phase8/adapters/supervised_process_adapter.py
- scripts/run_terminus2_benchmark_campaign.py
- scripts/terminus2_phase8_eval.py
- scripts/validate_terminus2_archive.py
- src/harbor/agents/terminus_2/adaptive_recovery.py
- src/harbor/agents/terminus_2/autonomous.py
- src/harbor/agents/terminus_2/benchmark_suite.py
- src/harbor/agents/terminus_2/failure_classifier.py
- src/harbor/agents/terminus_2/orchestration.py
- src/harbor/agents/terminus_2/task_planner.py
- src/harbor/agents/terminus_2/terminus_2.py
- src/harbor/agents/terminus_2/trajectory_evaluation.py
- tests/unit/agents/terminus_2/test_adaptive_recovery.py
- tests/unit/agents/terminus_2/test_autonomous.py
- tests/unit/agents/terminus_2/test_benchmark_suite.py
- tests/unit/agents/terminus_2/test_failure_classifier.py
- tests/unit/agents/terminus_2/test_orchestration.py
- tests/unit/agents/terminus_2/test_phase8_eval.py
- tests/unit/agents/terminus_2/test_task_planner.py
- tests/unit/agents/terminus_2/test_trajectory_evaluation.py
- AUDIT_REPORT.md (this report)

The venv and ignored caches were populated for checks. uv.lock and pyproject.toml were not changed.

## Required human decisions and remaining actions

1. [Resolved by subsequent maintainer confirmation] Confirm the PostHog project ownership and intended public-client use. That confirmation is not independent technical verification; no token change was made.
2. Review/authorize a security-focused lock refresh. The preserved lock has OSV matches in 35 pinned package versions; decide applicability and approve version changes separately.
3. Supply the ZIP's exact source commit or archive hash. Upstream v0.24.0 is only a candidate reference; active root has no Git tracking metadata.
4. Run locked dependency, unit, and type checks on Linux CI or another permitted environment with compatible wheels. Windows needs Rust to build litellm 1.93.0; Rust was not installed.
5. Restore least-privilege WSL/Bash and Docker named-pipe access if those checks are required; do not disable protections or elevate.
6. Human-review the 26 Python repairs, .gitignore, 238 current-only paths, 314 content differences, and 4 baseline-only paths before upload. Actual tracked/untracked status is unknown.
7. Remove the audit-generated .uv-cache after granting an allowed cleanup path or removing it manually; it is fully ignored but remains on disk because managed policy denied recursive deletion.

No Phase 8 campaign, staging, commit, push, release, or publication occurred. This repository is NOT READY for public upload; it is ready for human review of these findings and decisions.

## Baseline comparison appendix

Path categories are relative to upstream tag v0.24.0 only; they are not claims of Git status.

### Current-only paths (238)

<details><summary>Show paths</summary>

- .gitattributes
- benchmarks/terminus2-phase6/README.md
- benchmarks/terminus2-phase6/results.json
- benchmarks/terminus2-phase7/README.md
- benchmarks/terminus2-phase7/results.json
- benchmarks/terminus2-phase8/README.md
- benchmarks/terminus2-phase8/adapter-contract.md
- benchmarks/terminus2-phase8/adapters/adaptive_adapter.py
- benchmarks/terminus2-phase8/adapters/baseline_adapter.py
- benchmarks/terminus2-phase8/adapters/harbor_trial_supervisor.py
- benchmarks/terminus2-phase8/adapters/safety-attestation.example.json
- benchmarks/terminus2-phase8/adapters/supervised_process_adapter.py
- benchmarks/terminus2-phase8/manifest.json
- benchmarks/terminus2-phase8/preregistration.md
- docs-mintlify/agents/agent-auth-resolution.mdx
- docs-mintlify/agents/base-url-management.mdx
- docs-mintlify/images/agent-auth-resolution/parsing-and-routing-dark.svg
- docs-mintlify/images/agent-auth-resolution/parsing-and-routing-light.svg
- docs-mintlify/images/agent-auth-resolution/skip-parsing-dark.svg
- docs-mintlify/images/agent-auth-resolution/skip-parsing-light.svg
- docs-mintlify/images/error-classification-dark.png
- docs-mintlify/images/error-classification.png
- docs-mintlify/jobs/error-classification.mdx
- docs-mintlify/snippets/model-lookup.jsx
- docs-mintlify/tasks/lint.mdx
- docs/terminus2-adaptive-intelligence.md
- examples/agents/fabric/Dockerfile.codex
- examples/tasks/hello-harborignore/README.md
- examples/tasks/hello-harborignore/environment/Dockerfile
- examples/tasks/hello-harborignore/instruction.md
- examples/tasks/hello-harborignore/solution/.harborignore
- examples/tasks/hello-harborignore/solution/notes.md
- examples/tasks/hello-harborignore/solution/solve.sh
- examples/tasks/hello-harborignore/task.toml
- examples/tasks/hello-harborignore/tests/.harborignore
- examples/tasks/hello-harborignore/tests/fixtures/.harborignore
- examples/tasks/hello-harborignore/tests/fixtures/draft.txt
- examples/tasks/hello-harborignore/tests/fixtures/expected.txt
- examples/tasks/hello-harborignore/tests/local/check.sh
- examples/tasks/hello-harborignore/tests/test.sh
- examples/tasks/hello-world-multiple-solutions/environment/Dockerfile
- examples/tasks/hello-world-multiple-solutions/instruction.md
- examples/tasks/hello-world-multiple-solutions/solution/solution2/hello.txt
- examples/tasks/hello-world-multiple-solutions/solution/solution2/solve.sh
- examples/tasks/hello-world-multiple-solutions/solution/solve.sh
- examples/tasks/hello-world-multiple-solutions/task.toml
- examples/tasks/hello-world-multiple-solutions/tests/test.sh
- examples/tasks/reward-hacking/hello-world-non-root-user/README.md
- examples/tasks/reward-hacking/hello-world-non-root-user/environment/Dockerfile
- examples/tasks/reward-hacking/hello-world-non-root-user/instruction.md
- examples/tasks/reward-hacking/hello-world-non-root-user/solution/solve.sh
- examples/tasks/reward-hacking/hello-world-non-root-user/task.toml
- examples/tasks/reward-hacking/hello-world-non-root-user/tests/test.sh
- examples/tasks/secure-python-worker/README.md
- examples/tasks/secure-python-worker/environment/Dockerfile
- examples/tasks/secure-python-worker/environment/solution.py
- examples/tasks/secure-python-worker/instruction.md
- examples/tasks/secure-python-worker/solution/solve.sh
- examples/tasks/secure-python-worker/task.toml
- examples/tasks/secure-python-worker/tests/Dockerfile
- examples/tasks/secure-python-worker/tests/check.py
- examples/tasks/secure-python-worker/tests/test.sh
- packages/rewardkit/src/rewardkit/_worker_bootstrap.py
- packages/rewardkit/src/rewardkit/_worker_cleanup.py
- packages/rewardkit/src/rewardkit/sandbox.py
- packages/rewardkit/tests/sandbox/Dockerfile
- packages/rewardkit/tests/sandbox/conftest.py
- packages/rewardkit/tests/sandbox/test_cheats.py
- packages/rewardkit/tests/sandbox/test_setup.py
- packages/rewardkit/tests/sandbox/test_worker.py
- packages/rewardkit/tests/unit/test_sandbox.py
- packages/rewardkit/tests/unit/test_secure_python_worker_example.py
- rfcs/0003-secure-rewardkit-workers.md
- scripts/run_terminus2_benchmark_campaign.py
- scripts/terminus2_phase8_eval.py
- scripts/validate_terminus2_archive.py
- src/harbor/agents/agent_auth_resolution.py
- src/harbor/agents/computer_1/providers/tinker.py
- src/harbor/agents/installed/fabric.py
- src/harbor/agents/installed/kimi_code_trajectory.py
- src/harbor/agents/mcp_headers.py
- src/harbor/agents/terminus_2/adaptive_recovery.py
- src/harbor/agents/terminus_2/autonomous.py
- src/harbor/agents/terminus_2/benchmark_suite.py
- src/harbor/agents/terminus_2/failure_classifier.py
- src/harbor/agents/terminus_2/orchestration.py
- src/harbor/agents/terminus_2/recovery_knowledge.py
- src/harbor/agents/terminus_2/task_planner.py
- src/harbor/agents/terminus_2/trajectory_evaluation.py
- src/harbor/cli/agent_auth_resolution.py
- src/harbor/cli/lint.py
- src/harbor/cli/template-task/pytest-tests/Dockerfile
- src/harbor/cli/template-task/shared-pytest-tests/test.sh
- src/harbor/cli/template-task/tests/Dockerfile
- src/harbor/environments/kernel.py
- src/harbor/environments/kernel_docker.py
- src/harbor/environments/runta/__init__.py
- src/harbor/environments/runta/client.py
- src/harbor/environments/runta/environment.py
- src/harbor/environments/sail.py
- src/harbor/environments/sbx/__init__.py
- src/harbor/environments/sbx/cloud/__init__.py
- src/harbor/environments/sbx/cloud/client.py
- src/harbor/environments/sbx/cloud/files.py
- src/harbor/environments/sbx/cloud/http.py
- src/harbor/environments/sbx/cloud/process.py
- src/harbor/environments/sbx/cloud/sandboxes.py
- src/harbor/environments/sbx/compose.py
- src/harbor/environments/sbx/environment.py
- src/harbor/environments/sbx/errors.py
- src/harbor/environments/sbx/local.py
- src/harbor/environments/sbx/options.py
- src/harbor/environments/sbx/remote.py
- src/harbor/lint/__init__.py
- src/harbor/lint/compose.py
- src/harbor/lint/models.py
- src/harbor/lint/task.py
- src/harbor/models/model_api_format.py
- src/harbor/models/task/file_filter.py
- src/harbor/models/trial/error_policy.py
- src/harbor/utils/file_selection.py
- src/harbor/utils/file_staging.py
- src/harbor/utils/redaction.py
- tests/integration/test_lint_compose.py
- tests/integration/windows/test_windows_hello_world.py
- tests/integration/windows/test_windows_start_env.py
- tests/runtime/test_rewardkit_sandbox.py
- tests/runtime/test_sbx_nested.py
- tests/runtime/test_sbx_network_setup.py
- tests/unit/agents/computer_1/test_tinker.py
- tests/unit/agents/computer_1/test_tinker_routing.py
- tests/unit/agents/installed/test_aider.py
- tests/unit/agents/installed/test_aider_base_url.py
- tests/unit/agents/installed/test_catalog_connection_launch.py
- tests/unit/agents/installed/test_catalog_model_routing.py
- tests/unit/agents/installed/test_claude_code_model_aliases.py
- tests/unit/agents/installed/test_connection_credential_destinations.py
- tests/unit/agents/installed/test_credential_env.py
- tests/unit/agents/installed/test_fabric.py
- tests/unit/agents/installed/test_gemini_web_policy_restore.py
- tests/unit/agents/installed/test_kimi_code_native_configuration.py
- tests/unit/agents/installed/test_kimi_code_trajectory.py
- tests/unit/agents/installed/test_langgraph_gateway_connection.py
- tests/unit/agents/installed/test_litellm_format_override.py
- tests/unit/agents/installed/test_mcp_http_headers.py
- tests/unit/agents/installed/test_messages_endpoint_delivery.py
- tests/unit/agents/installed/test_mini_swe_native_model_names.py
- tests/unit/agents/installed/test_model_routing_matrix.py
- tests/unit/agents/installed/test_multi_provider_model_routes.py
- tests/unit/agents/installed/test_native_catalog_connections.py
- tests/unit/agents/installed/test_native_configuration_overrides.py
- tests/unit/agents/installed/test_native_connection_reporting.py
- tests/unit/agents/installed/test_native_connection_resolution.py
- tests/unit/agents/installed/test_native_model_connection.py
- tests/unit/agents/installed/test_native_model_routing.py
- tests/unit/agents/installed/test_opaque_litellm_credentials.py
- tests/unit/agents/installed/test_opencode_model_connection.py
- tests/unit/agents/installed/test_opencode_model_rendering.py
- tests/unit/agents/installed/test_openhands_nemo_protocol_override.py
- tests/unit/agents/installed/test_qwen_code_config.py
- tests/unit/agents/installed/test_runtime_backend_compatibility.py
- tests/unit/agents/installed/test_runtime_connection_resolution.py
- tests/unit/agents/installed/test_runtime_model_connections.py
- tests/unit/agents/installed/test_scoped_connection_env.py
- tests/unit/agents/installed/test_standardized_byok_connections.py
- tests/unit/agents/installed/test_web_tool_config_restore.py
- tests/unit/agents/terminus_2/test_adaptive_recovery.py
- tests/unit/agents/terminus_2/test_autonomous.py
- tests/unit/agents/terminus_2/test_benchmark_suite.py
- tests/unit/agents/terminus_2/test_failure_classifier.py
- tests/unit/agents/terminus_2/test_orchestration.py
- tests/unit/agents/terminus_2/test_phase8_eval.py
- tests/unit/agents/terminus_2/test_recovery_knowledge.py
- tests/unit/agents/terminus_2/test_task_planner.py
- tests/unit/agents/terminus_2/test_trajectory_evaluation.py
- tests/unit/agents/test_agent_credential_requirements.py
- tests/unit/agents/test_aws_model_credentials.py
- tests/unit/agents/test_aws_provider_access.py
- tests/unit/agents/test_model_credential_preflight.py
- tests/unit/agents/test_model_name.py
- tests/unit/agents/test_model_schema.py
- tests/unit/agents/test_native_connection_reporting.py
- tests/unit/agents/test_skip_model_parsing.py
- tests/unit/artifact_uploads.py
- tests/unit/cli/test_job_bridge_preflight.py
- tests/unit/cli/test_model_connection_diagnostics.py
- tests/unit/cli/test_native_connection_parsing.py
- tests/unit/cli/test_skip_model_parsing.py
- tests/unit/cli/test_trial_model_preflight.py
- tests/unit/cli/test_trials_start_connection_options.py
- tests/unit/environments/cwsandbox/test_cwsandbox_compose.py
- tests/unit/environments/sbx/__init__.py
- tests/unit/environments/sbx/conftest.py
- tests/unit/environments/sbx/local_support.py
- tests/unit/environments/sbx/remote_support.py
- tests/unit/environments/sbx/support.py
- tests/unit/environments/sbx/test_auth.py
- tests/unit/environments/sbx/test_cleanup.py
- tests/unit/environments/sbx/test_client.py
- tests/unit/environments/sbx/test_compose.py
- tests/unit/environments/sbx/test_config.py
- tests/unit/environments/sbx/test_environment.py
- tests/unit/environments/sbx/test_errors.py
- tests/unit/environments/sbx/test_files.py
- tests/unit/environments/sbx/test_lifecycle.py
- tests/unit/environments/sbx/test_lifetime.py
- tests/unit/environments/sbx/test_local.py
- tests/unit/environments/sbx/test_local_compose.py
- tests/unit/environments/sbx/test_network.py
- tests/unit/environments/sbx/test_process.py
- tests/unit/environments/sbx/test_rate.py
- tests/unit/environments/sbx/test_remote.py
- tests/unit/environments/sbx/test_remote_compose.py
- tests/unit/environments/test_auto_mounting.py
- tests/unit/environments/test_file_selection_transfer.py
- tests/unit/environments/test_kernel.py
- tests/unit/environments/test_runta_client.py
- tests/unit/environments/test_sail.py
- tests/unit/environments/test_staged_upload_parity.py
- tests/unit/llms/test_tinker.py
- tests/unit/llms/test_tinker_renderer_compat.py
- tests/unit/models/test_cpus_normalization.py
- tests/unit/models/test_model_api_format.py
- tests/unit/models/test_task_file_filter.py
- tests/unit/models/test_task_harborignore.py
- tests/unit/models/test_trial_result_policy.py
- tests/unit/publisher/test_packager_harborignore.py
- tests/unit/test_job_model_connections.py
- tests/unit/test_lint.py
- tests/unit/test_lint_compose.py
- tests/unit/test_verifier_build_inputs.py
- tests/unit/trial/test_web_tool_policy.py
- tests/unit/utils/test_file_selection.py
- tests/unit/utils/test_file_staging.py
- trials/test-task__2ibNsyd/lock.json
- trials/test-task__2ibNsyd/trial.log
- trials/test-task__rN7PBNG/lock.json
- trials/test-task__rN7PBNG/trial.log

</details>

## Follow-up: LiteLLM Windows installation blocker (2026-10-24)

**Result: BLOCKED; litellm was not installed.** The active environment is CPython 3.13.17, 64-bit AMD64 Windows (`win32`); project metadata supports Python >=3.12. The locked package is `litellm==1.93.0`, from PyPI. PyPI declares Python >=3.10,<3.15 and publishes this version's wheels only for CPython 3.10–3.14 on manylinux 2.28 x86-64 and aarch64; there is no compatible Windows wheel. The release also has an sdist. See [PyPI release metadata](https://pypi.org/project/litellm/1.93.0/).

Commands and results:
- `uv --cache-dir .uv-cache pip install --dry-run --no-deps --only-binary :all: --python .venv\\Scripts\\python.exe litellm==1.93.0` — exit 1; uv reports there are no usable wheels and the constraints are unsatisfiable when source builds are disabled. This was a dry run; it installed nothing.
- The same dry run using the default uv cache first failed before resolution with `Could not acquire lock` / Access Denied under `%LOCALAPPDATA%\\uv\\cache`; retrying with the already-existing project-local cache reached the expected no-wheel result.
- Environment inspection found no `UV_*` environment variables, no project/root `uv.toml`, and no `tool.uv` package index or binary/source override; only `sources` and `workspace` settings are present in `pyproject.toml`. Thus no observed package-manager setting caused the wheel mismatch.

The sdist build requirement previously inspected from the cached source metadata is `maturin==1.9.4`, configured for the LiteLLM Rust/PyO3 bridge. The host has no configured Cargo toolchain; a Windows source build also requires compatible native build tooling. No Rust/Cargo or system-wide tools were installed. An alternate Linux-wheel installation is not available through the current checks: WSL previously failed with `Bash/Service/CreateInstance/E_ACCESSDENIED`, and Docker API access remains denied.

Because the dependency remains absent, the focused Antigravity, telemetry, Terminus-2, full unit, and `ty check` commands were **not rerun** in this step; running them in the same incomplete environment would repeat known missing-import collection/failure results rather than validate the requested post-install state. Their prior outcomes remain recorded above. No product files, dependencies, or `uv.lock` were changed by this follow-up. No telemetry was transmitted and no secret values were printed.

**Minimum next action:** run the locked environment and checks on a permitted Linux CPython 3.13 environment with glibc >=2.28 and compatible architecture, or explicitly approve installing the Windows Rust/Cargo and native MSVC build prerequisites before retrying `uv sync --locked`. Do not substitute another dependency version. The repository is not ready for public upload based on this result.

### Baseline-only paths (4)

<details><summary>Show paths</summary>

- src/harbor/agents/model_connection.py
- src/harbor/environments/runta.py
- tests/integration/test_windows_hello_world.py
- tests/integration/test_windows_start_env.py

</details>

### Byte-different common paths (314)

<details><summary>Show paths</summary>

- .github/workflows/pytest.yml
- .github/workflows/ruff-format.yml
- .github/workflows/ty.yml
- .gitignore
- AGENTS.md
- CHANGELOG.md
- CITATION.cff
- CLAUDE.md
- README.md
- adapters/dacode/parity/da_harbor_agent/agent/agents.py
- adapters/pixiu/README.md
- adapters/spider2-dbt/src/spider2_dbt/run_spider_agent_dbt.py
- adapters/webgen_bench/src/webgen_bench/task-template/tests/webvoyager/utils.py
- apps/viewer/app/app.css
- apps/viewer/app/components/file-system-viewer.tsx
- apps/viewer/app/components/job-evals-waffle.tsx
- apps/viewer/app/components/navbar.tsx
- apps/viewer/app/root.tsx
- apps/viewer/app/routes/home.tsx
- apps/viewer/app/routes/job.tsx
- apps/viewer/app/routes/trial.tsx
- docs-mintlify/agents/custom-agents.mdx
- docs-mintlify/agents/pre-integrated-agents.mdx
- docs-mintlify/changelog.mdx
- docs-mintlify/docs.json
- docs-mintlify/jobs/configs.mdx
- docs-mintlify/jobs/environment-variables.mdx
- docs-mintlify/jobs/regrade.mdx
- docs-mintlify/jobs/run-a-job.mdx
- docs-mintlify/news.mdx
- docs-mintlify/rewardkit/judge-criteria.mdx
- docs-mintlify/rewardkit/motivation-and-design.mdx
- docs-mintlify/rewardkit/quick-start.mdx
- docs-mintlify/sandboxes/pre-integrated-sandboxes.mdx
- docs-mintlify/style.css
- docs-mintlify/tasks/artifacts.mdx
- docs-mintlify/tasks/configuration.mdx
- docs-mintlify/tasks/environment.mdx
- docs-mintlify/tasks/multi-container.mdx
- docs-mintlify/tasks/network-policies.mdx
- docs-mintlify/tasks/overview.mdx
- docs-mintlify/tasks/resources.mdx
- docs-mintlify/tasks/separate-verifier.mdx
- docs-mintlify/tasks/solution.mdx
- docs-mintlify/tasks/verifier.mdx
- docs-mintlify/tutorials/create-a-verifier-with-rewardkit.mdx
- docs/CLAUDE.md
- examples/configs/agents/fx-dev-job.yaml
- examples/configs/agents/fx-job.yaml
- examples/tasks/network-policy-matrix/static/compose-sidecar-controlled/environment/docker-compose.yaml
- examples/tasks/network-policy-matrix/static/compose-sidecar-uncontrolled-network/environment/docker-compose.yaml
- examples/tasks/reward-kit-example/tests/test.sh
- packages/rewardkit/CLAUDE.md
- packages/rewardkit/README.md
- packages/rewardkit/pyproject.toml
- packages/rewardkit/src/rewardkit/__init__.py
- packages/rewardkit/src/rewardkit/__main__.py
- packages/rewardkit/src/rewardkit/agents.py
- packages/rewardkit/src/rewardkit/models.py
- packages/rewardkit/src/rewardkit/reward.py
- packages/rewardkit/src/rewardkit/runner.py
- packages/rewardkit/tests/conftest.py
- packages/rewardkit/tests/unit/test_agents.py
- packages/rewardkit/tests/unit/test_cli.py
- packages/rewardkit/tests/unit/test_models.py
- packages/rewardkit/tests/unit/test_reward.py
- packages/rewardkit/tests/unit/test_runner.py
- pyproject.toml
- skills/create-task/SKILL.md
- skills/rewardkit/SKILL.md
- src/harbor/agents/base.py
- src/harbor/agents/capabilities.py
- src/harbor/agents/computer_1/computer_1.py
- src/harbor/agents/computer_1/providers/anthropic.py
- src/harbor/agents/computer_1/providers/base.py
- src/harbor/agents/computer_1/providers/gemini.py
- src/harbor/agents/computer_1/providers/openai.py
- src/harbor/agents/dspy_rlm.py
- src/harbor/agents/factory.py
- src/harbor/agents/installed/aider.py
- src/harbor/agents/installed/antigravity_cli.py
- src/harbor/agents/installed/antigravity_sdk.py
- src/harbor/agents/installed/antigravity_sdk_runner.py
- src/harbor/agents/installed/antigravity_sdk_runner.py.lock
- src/harbor/agents/installed/base.py
- src/harbor/agents/installed/claude_code.py
- src/harbor/agents/installed/cline/cline.py
- src/harbor/agents/installed/code_puppy.py
- src/harbor/agents/installed/codex.py
- src/harbor/agents/installed/copilot_cli.py
- src/harbor/agents/installed/cortex_code.py
- src/harbor/agents/installed/cursor_cli.py
- src/harbor/agents/installed/deerflow.py
- src/harbor/agents/installed/devin.py
- src/harbor/agents/installed/fx.py
- src/harbor/agents/installed/gemini_cli.py
- src/harbor/agents/installed/goose.py
- src/harbor/agents/installed/grok_build.py
- src/harbor/agents/installed/hermes.py
- src/harbor/agents/installed/junie.py
- src/harbor/agents/installed/kimi_cli.py
- src/harbor/agents/installed/kimi_code.py
- src/harbor/agents/installed/langgraph.py
- src/harbor/agents/installed/mcode.py
- src/harbor/agents/installed/mimo.py
- src/harbor/agents/installed/mini_swe_agent.py
- src/harbor/agents/installed/muse_code.py
- src/harbor/agents/installed/nemo_agent.py
- src/harbor/agents/installed/openclaw.py
- src/harbor/agents/installed/opencode.py
- src/harbor/agents/installed/openhands.py
- src/harbor/agents/installed/openhands_sdk.py
- src/harbor/agents/installed/openhands_sdk_runner.py
- src/harbor/agents/installed/pi.py
- src/harbor/agents/installed/qwen_code.py
- src/harbor/agents/installed/rovodev_cli.py
- src/harbor/agents/installed/strands.py
- src/harbor/agents/installed/strands_runner.py
- src/harbor/agents/installed/swe_agent.py
- src/harbor/agents/installed/trae_agent.py
- src/harbor/agents/installed/vibe.py
- src/harbor/agents/options.py
- src/harbor/agents/oracle.py
- src/harbor/agents/terminus_2/terminus_2.py
- src/harbor/agents/terminus_2/tmux_session.py
- src/harbor/bridges/acp.py
- src/harbor/cli/agents.py
- src/harbor/cli/init.py
- src/harbor/cli/jobs.py
- src/harbor/cli/main.py
- src/harbor/cli/tasks.py
- src/harbor/cli/template-task/pytest-tests/test.sh
- src/harbor/cli/template-task/tests/test.sh
- src/harbor/cli/trials.py
- src/harbor/cli/utils.py
- src/harbor/environments/apple_container.py
- src/harbor/environments/base.py
- src/harbor/environments/beam.py
- src/harbor/environments/blaxel.py
- src/harbor/environments/capabilities.py
- src/harbor/environments/cwsandbox.py
- src/harbor/environments/daytona/environment.py
- src/harbor/environments/dind_compose.py
- src/harbor/environments/docker/__init__.py
- src/harbor/environments/docker/compose_env.py
- src/harbor/environments/docker/docker.py
- src/harbor/environments/docker/docker_unix.py
- src/harbor/environments/docker/harbor-docker-egress-control-sidecar/bin/network-policy
- src/harbor/environments/docker/harbor-docker-egress-control-sidecar/entrypoint.sh
- src/harbor/environments/docker/runtime.py
- src/harbor/environments/e2b.py
- src/harbor/environments/factory.py
- src/harbor/environments/gke.py
- src/harbor/environments/modal.py
- src/harbor/environments/opensandbox.py
- src/harbor/environments/openshift.py
- src/harbor/environments/podman.py
- src/harbor/environments/resource_policies.py
- src/harbor/environments/runloop.py
- src/harbor/environments/singularity/singularity.py
- src/harbor/environments/smol.py
- src/harbor/environments/tar_transfer.py
- src/harbor/environments/vercel/environment.py
- src/harbor/job.py
- src/harbor/llms/lite_llm.py
- src/harbor/llms/litellm_config.py
- src/harbor/llms/tinker.py
- src/harbor/models/agent/name.py
- src/harbor/models/dataset/manifest.py
- src/harbor/models/environment_type.py
- src/harbor/models/job/config.py
- src/harbor/models/task/artifacts.py
- src/harbor/models/task/config.py
- src/harbor/models/task/paths.py
- src/harbor/models/task/task.py
- src/harbor/models/task/verifier_mode.py
- src/harbor/models/trial/config.py
- src/harbor/models/trial/result.py
- src/harbor/publisher/packager.py
- src/harbor/publisher/publisher.py
- src/harbor/telemetry.py
- src/harbor/trial/artifact_handler.py
- src/harbor/trial/multi_step.py
- src/harbor/trial/network_policy.py
- src/harbor/trial/regrade.py
- src/harbor/trial/trial.py
- src/harbor/upload/uploader.py
- src/harbor/utils/env.py
- src/harbor/utils/path_safety.py
- src/harbor/verifier/verifier.py
- src/harbor/viewer/models.py
- src/harbor/viewer/server.py
- tests/conftest.py
- tests/integration/test_multi_step_trial.py
- tests/runtime/test_multi_step_regrade.py
- tests/unit/agents/computer_1/test_providers.py
- tests/unit/agents/installed/test_antigravity_cli.py
- tests/unit/agents/installed/test_claude_code_auth.py
- tests/unit/agents/installed/test_claude_code_bedrock.py
- tests/unit/agents/installed/test_claude_code_mcp.py
- tests/unit/agents/installed/test_cline_cli.py
- tests/unit/agents/installed/test_code_puppy.py
- tests/unit/agents/installed/test_codex_acp.py
- tests/unit/agents/installed/test_codex_auth.py
- tests/unit/agents/installed/test_codex_config.py
- tests/unit/agents/installed/test_codex_load_trajectory.py
- tests/unit/agents/installed/test_codex_mcp.py
- tests/unit/agents/installed/test_cortex_code_run.py
- tests/unit/agents/installed/test_deerflow.py
- tests/unit/agents/installed/test_devin.py
- tests/unit/agents/installed/test_disable_web_search.py
- tests/unit/agents/installed/test_error_patterns.py
- tests/unit/agents/installed/test_fx.py
- tests/unit/agents/installed/test_gemini_cli.py
- tests/unit/agents/installed/test_gemini_cli_mcp.py
- tests/unit/agents/installed/test_grok_build.py
- tests/unit/agents/installed/test_hermes_cli.py
- tests/unit/agents/installed/test_junie_auth.py
- tests/unit/agents/installed/test_kimi_cli.py
- tests/unit/agents/installed/test_kimi_code.py
- tests/unit/agents/installed/test_langgraph_agent.py
- tests/unit/agents/installed/test_mcode.py
- tests/unit/agents/installed/test_mimo.py
- tests/unit/agents/installed/test_mini_swe_agent.py
- tests/unit/agents/installed/test_muse_code.py
- tests/unit/agents/installed/test_openclaw.py
- tests/unit/agents/installed/test_opencode.py
- tests/unit/agents/installed/test_opencode_acp.py
- tests/unit/agents/installed/test_opencode_mcp.py
- tests/unit/agents/installed/test_pi.py
- tests/unit/agents/installed/test_qwen_code_mcp.py
- tests/unit/agents/installed/test_rovodev_cli.py
- tests/unit/agents/installed/test_strands.py
- tests/unit/agents/installed/test_strands_runner.py
- tests/unit/agents/installed/test_swe_agent.py
- tests/unit/agents/installed/test_system_dependencies.py
- tests/unit/agents/installed/test_vibe.py
- tests/unit/agents/terminus_2/test_terminus_2_session_id.py
- tests/unit/agents/terminus_2/test_terminus_2_temperature.py
- tests/unit/agents/terminus_2/test_tmux_session.py
- tests/unit/agents/test_base_agent_model_info.py
- tests/unit/agents/test_dspy_rlm.py
- tests/unit/agents/test_env_propagation.py
- tests/unit/agents/test_factory.py
- tests/unit/agents/test_factory_computer_1.py
- tests/unit/agents/test_model_connection.py
- tests/unit/agents/test_nemo_agent.py
- tests/unit/agents/test_options.py
- tests/unit/agents/test_oracle.py
- tests/unit/cli/test_agent_override.py
- tests/unit/cli/test_agent_schema.py
- tests/unit/cli/test_config_composition.py
- tests/unit/cli/test_config_validation.py
- tests/unit/cli/test_init.py
- tests/unit/cli/test_jobs_override.py
- tests/unit/cli/test_jobs_start_retry.py
- tests/unit/cli/test_tasks_init_template.py
- tests/unit/cli/test_tasks_start_env.py
- tests/unit/cli/test_trials_config_composition.py
- tests/unit/cli/test_trials_start_log_filters.py
- tests/unit/cli/test_utils.py
- tests/unit/environments/cwsandbox/conftest.py
- tests/unit/environments/cwsandbox/test_cwsandbox.py
- tests/unit/environments/test_base_download_dir_filtered.py
- tests/unit/environments/test_base_env_mounts_passthrough.py
- tests/unit/environments/test_base_validation.py
- tests/unit/environments/test_beam.py
- tests/unit/environments/test_blaxel.py
- tests/unit/environments/test_container_runtime.py
- tests/unit/environments/test_daytona.py
- tests/unit/environments/test_docker.py
- tests/unit/environments/test_docker_mounts.py
- tests/unit/environments/test_docker_service_ops.py
- tests/unit/environments/test_modal.py
- tests/unit/environments/test_opensandbox.py
- tests/unit/environments/test_podman.py
- tests/unit/environments/test_runta.py
- tests/unit/environments/test_tar_transfer.py
- tests/unit/environments/test_vercel.py
- tests/unit/llms/test_lite_llm.py
- tests/unit/llms/test_litellm_config.py
- tests/unit/models/test_agent_config_env.py
- tests/unit/models/test_artifact_validation.py
- tests/unit/models/test_dataset_manifest.py
- tests/unit/models/test_task_config_mcp.py
- tests/unit/models/test_task_config_network.py
- tests/unit/models/test_validation.py
- tests/unit/test_agent_os_compat.py
- tests/unit/test_antigravity_sdk_agent.py
- tests/unit/test_cli_resume_upload.py
- tests/unit/test_env_resolver.py
- tests/unit/test_hosted_submit_status.py
- tests/unit/test_job_confirm_env_access.py
- tests/unit/test_job_diff.py
- tests/unit/test_multi_step_run_step.py
- tests/unit/test_openhands_sdk_agent.py
- tests/unit/test_package_registry_client.py
- tests/unit/test_publisher.py
- tests/unit/test_regrade.py
- tests/unit/test_regrade_config_fallback.py
- tests/unit/test_simulated_user.py
- tests/unit/test_single_step_trial.py
- tests/unit/test_trial_artifacts.py
- tests/unit/test_trial_cleanup.py
- tests/unit/test_trial_verifier_artifact_transfer.py
- tests/unit/test_trial_verifier_separate.py
- tests/unit/test_trial_windows_multistep.py
- tests/unit/test_uploader.py
- tests/unit/test_verifier.py
- tests/unit/test_verifier_env_override.py
- tests/unit/trial/test_network_policy.py
- tests/unit/viewer/test_run_launcher.py
- tests/unit/viewer/test_task_avg_reward.py
- uv.lock

</details>
