# Final Harbor Terminus Release Review

> **Historical review with current validation addendum.** The release and full-suite findings below preserve evidence collected on 2026-10-24 and 2026-10-25. They are historical unless explicitly identified as current. The current focused validation snapshot is dated 2026-10-26 and appears below.

Original review date: 2026-10-25
Scope: this repository and retained audit evidence. A separate protected reference workspace was not accessed or modified.

## FINAL RELEASE STATUS

**Historical decision on 2026-10-25: NOT READY**

### Current validation snapshot — 2026-10-26

- Focused regression suite: the run before adding the Bedrock regression reported **632 passed, 5 skipped**; the current rerun with that regression reports **633 passed, 5 skipped**. This is a selected regression suite, not the full `tests/unit` suite.
- `uv lock --check --offline`: **passed**.
- Ruff lint and format checks on the 11 changed Python files: **passed**.
- Current Git status at this snapshot: **3,657 staged files, 14 modified working-tree paths, 0 untracked files**. The staged snapshot remains intact; the modified paths include pre-existing unstaged work and the review fixes.
- The full unit suite was not run for this validation. The retained larger Windows run below is diagnostic historical evidence and is not a green full-suite result or supported-CI run.

These checks do not resolve the broader release limitations recorded below, including missing supported CI evidence, unresolved full type-check evidence, and source provenance that cannot be established from Git ancestry.

The supported public security profile is the default/core install only. Known findings remain in explicitly unsupported optional and development profiles, but they are not claims of supported security coverage or remediation. The two LiteLLM findings affect Proxy functionality; Harbor's supported deployment does not operate LiteLLM Proxy, although repository inspection cannot establish what external operators deploy. The maintainer has confirmed that the embedded PostHog project belongs to Harbor and is intended to remain in this release; this has not been independently verified against PostHog project settings. `SECURITY.md` now documents the private vulnerability-reporting contact for this release. Public release remains blocked by incomplete supported CI/type/test evidence and missing Git provenance.

## EXECUTIVE SUMMARY

The previous reports described different moments in the work. The October 24 audit records the initial dependency inventory and incomplete Windows environment checks. The later advisory follow-up clarified affected ranges. The candidate refresh recorded by the October 25 review updated the default security set and retained the vulnerable optional/dev package versions. `DEPENDENCY_DECISION_MEMO.md` is a historical proposal, not the final decision record. Its claim that no dependency changes were made is superseded by the subsequent recorded refresh.

`pyproject.toml` and `uv.lock` currently agree. The lock check passed. The approved core package refresh and focused dependency regressions passed as documented in the earlier review; this turn did not repeat those checks. The Windows full unit report is not a supported-CI result and its failures are predominantly platform/optional-profile/environment limitations. It cannot establish a clean release test run.

In the 2026-10-25 review, no dependency versions were changed. The lock consistency check, 580 targeted regressions, separate 12-test telemetry selection, and targeted type check passed as recorded then. No telemetry was transmitted. The current 2026-10-26 focused validation is recorded above. No commit, push, release, or publication is recorded in this report.

## SUPPORTED PROFILE

- Python: `pyproject.toml` declares `requires-python = ">=3.12"`; `.python-version` selects 3.13. Current CI uses Python 3.13. Support beyond Python 3.13 is declared but not demonstrated by this workspace's execution evidence.
- Operating systems: CI defines Linux and Windows jobs. The README now describes those CI-tested operating systems without promising that every optional integration works on both. macOS is not represented in the inspected CI workflow, so no macOS support claim is made here.
- **Supported public release profile:** the default/core install using `[project].dependencies` in `pyproject.toml`, including LiteLLM as a model client.
- **Unsupported optional profiles for this release:** `huggingface`, `tinker`, `dspy`, `adapter`, `blaxel`, `langsmith`, `gke`, `beam`, `computer-1`, `cloud`, and `all`. Their features remain in the tree and may be installable, but Harbor makes no security-support or remediation promise for them in this release. The `dev` dependency group is development-only and is not a supported public runtime profile.
- **Skypilot:** explicitly private early access in `pyproject.toml`; unsupported for this public release and excluded from `cloud` and `all`.
- CI installs `--all-extras`, which exercises unsupported extras. That CI configuration does not expand the supported public security profile; maintainers should distinguish CI coverage from product support.
- **LiteLLM Proxy:** the supported Harbor deployment does not operate Proxy. Source inspection found LiteLLM client imports/calls and no Proxy server startup. This repository cannot prove what an external operator deploys.

## DEPENDENCY STATUS

The current root constraints and lock were parsed again. The refreshed default pins are aiohttp 3.14.4, multidict 6.9.1, anyio 4.14.2, certifi 2026.10.19, cryptography 50.0.0, filelock 4.2.1, h2 4.4.1, hpack 4.2.0, PyJWT 2.15.0, requests 2.33.0, urllib3 2.8.0, FastAPI 0.133.0, Starlette 1.3.1, and yarl 1.25.1. LiteLLM remains 1.93.0.

The current `pyproject.toml` and `uv.lock` were unchanged in the 2026-10-25 review. `uv lock --check --offline --no-cache` passed there with 330 packages resolved. The current `uv lock --check --offline` result is recorded in the validation snapshot above. No dependency refresh was performed for that validation.

OpenTelemetry is selected through cloud/provider extras, `pydantic-settings` is in optional dependency paths (not a declared default direct dependency), and setuptools is reached through optional/build-related packages. They are not default/core direct dependencies. Findings in those packages apply only to the relevant optional or development paths and are outside the supported public profile for this release. Unsupported status is not a fix or a claim that the packages are safe.

## SECURITY / OSV STATUS

The earlier baseline reviewed 148 canonical IDs: 147 matched affected versions in the pre-refresh lock and one Torch record was outside its affected range. I re-evaluated retained PyPI OSV ranges against current `uv.lock` versions. The refreshed core versions no longer match the prior default-runtime findings. Findings listed below remain in unsupported optional/dev profiles; they remain package-level findings and are not remediated by the support boundary. The two LiteLLM advisories affect Proxy behavior, which the supported Harbor deployment does not operate; this does not establish what external operators deploy. Current OSV records also show the new aiohttp 3.14.4 advisories fixed at 3.14.4, and Starlette's request-form advisory fixed at 1.3.1. [aiohttp GHSA-494j-54xm-rwp3](https://osv.dev/vulnerability/GHSA-494j-54xm-rwp3), [Starlette CVE-2026-54283](https://osv.dev/vulnerability/CVE-2026-54283), [cryptography PYSEC-2026-3552](https://osv.dev/vulnerability/PYSEC-2026-3552).

| Package/profile | Classification | Status |
|---|---|---|
| LiteLLM 1.93.0 | LiteLLM Proxy-specific; outside the supported Harbor deployment profile | Two Proxy advisories remain applicable to the locked package version. The supported Harbor deployment does not operate Proxy; repository evidence cannot establish external operator deployments. Not package-fixed. |
| claude-agent-sdk | Unsupported optional profile: `adapter` | Affected version remains. |
| datasets, fsspec, PyArrow, Pillow, Transformers | Unsupported optional profiles: `huggingface`, `tinker` | Affected versions remain; some also appear in dev. Transformers' current cap prevents the reviewed fixed candidate. |
| diskcache | Unsupported optional profile: `dspy`; unresolved remediation | Advisory remains; reviewed records show no fixed release boundary. |
| LangSmith | Unsupported optional profile: `langsmith`/`cloud` | Affected version remains. |
| lxml | Unsupported optional profile: Tinker/blobfile path; exact extra path unresolved | Affected version remains. |
| MCP | Unsupported optional profiles: `adapter`, `blaxel`, `cloud` | Affected version remains. |
| oauthlib | Unsupported optional profiles: `gke`, `cloud` | Affected version remains. |
| OpenTelemetry API | Unsupported optional profile: `cloud`/provider extras | Affected version remains; the previous “Core” classification was incorrect. |
| Paramiko | Unsupported optional profiles: `beam`, `cloud`; unresolved remediation | Advisory remains; reviewed records show no fixed release boundary. |
| pyasn1 | Unsupported optional profile: `computer-1` | Affected version remains. |
| pydantic-settings | Unsupported optional profiles: MCP paths (`adapter`, `blaxel`, `cloud`) | Affected version remains; not a default direct dependency. |
| Pygments, pytest, SoupSieve, Tornado | Development-only | Affected locked versions remain in the development lock. |
| setuptools | Unsupported optional/build path: Tinker/Torch | Affected version remains; not a default direct dependency. |
| Torch | Unsupported optional profile: `tinker`; unresolved remediation | One advisory is not applicable (outside its affected range); another remains applicable and has no reviewed fixed boundary. |
| Wheel | Unsupported/early-access profile: `skypilot` | Advisory remains and its current Wheel constraint conflicts with the reviewed fix. Skypilot is explicitly early access and excluded from `cloud`/`all`. |

### Exact remaining advisory inventory and candidate impact

The following inventory was rebuilt against the current locked versions in `uv.lock` and the retained OSV affected-range records in `.uv-cache/osv-authoritative-records.json`, then checked against current OSV pages for the newly published aiohttp and LiteLLM records. “Affected” means the locked version falls in the advisory's published PyPI range; it does not assert that Harbor's code reaches the vulnerable feature. Aliases are grouped by advisory identity. The OSV appendix contains linked entries for each identifier.

| Locked package | Remaining advisory IDs (aliases are grouped in OSV index) | Profile classification | Is current locked version affected? Candidate/remediation and compatibility |
|---|---|---|---|
| `litellm 1.93.0` | GHSA-3cv6-jpf6-8222 / CVE-2026-84377 / PYSEC-2026-4066; GHSA-7hp6-4w63-5g45 / CVE-2026-114612 | LiteLLM Proxy-specific | **Yes** for both published package ranges. Both advisories describe Proxy server behavior; Harbor's supported profile uses LiteLLM as a client and repository search found no Proxy startup/import. Candidate `1.100.4` fixes both; `1.93.2` fixes only the first. `1.100.4` requires compatible `boto3`/`botocore==1.43.1`, `s3transfer>=0.17,<0.18`, `fastuuid>=0.14`, `pydantic-settings>=2.14.1`, and `aiohttp>=3.14.2`; the reviewed default+dev resolver succeeded for Python 3.12/3.13 but changes several packages. No upgrade is made for this release because Proxy is outside the supported Harbor deployment profile; external operator deployments cannot be established from this repository. [OSV GHSA-3cv6-jpf6-8222](https://osv.dev/vulnerability/GHSA-3cv6-jpf6-8222), [OSV CVE-2026-114612](https://osv.dev/vulnerability/CVE-2026-114612) |
| `claude-agent-sdk 0.1.20` | GHSA-h4mw-j7qp-8mwm / CVE-2026-96620 | Unsupported optional profile: `adapter` | **Yes.** Candidate `0.2.121`; SDK resume/API behavior needs adapter regression tests if this profile is later supported. |
| `datasets 4.5.0` | PYSEC-2026-3716 / CVE-2026-66007 / GHSA-379c-qx7v-6h59 | Unsupported optional profiles: `huggingface`, `tinker` | **Yes.** Candidate `5.0.1` is a major upgrade; validate dataset loading/serialization and Tinker compatibility if later supported. |
| `diskcache 5.6.3` | PYSEC-2026-2447 / CVE-2025-69872 / GHSA-w8v5-vhqr-4h9v | Unsupported optional profile: `dspy` | **Yes.** No fixed version was recorded; no safe version candidate established. |
| `fsspec 2025.10.0` | PYSEC-2026-4217 / CVE-2026-104851 / GHSA-27vj-qcqg-25rc | Unsupported optional profiles: `huggingface`, `tinker` | **Yes.** Candidate `2026.6.0`; validate data paths if either profile is later supported. |
| `langsmith 0.8.8` | GHSA-f4xh-w4cj-qxq8 / CVE-2026-59152 | Unsupported optional profiles: `langsmith`, `cloud`, `all` | **Yes.** Candidate `0.8.18`; validate tracing middleware if later supported. |
| `lxml 6.0.2` | PYSEC-2026-87 / CVE-2026-41066 / GHSA-vfmq-68hx-4jfw | Unsupported optional profile: Tinker/blobfile document path | **Yes.** Candidate `6.1.0`; native wheel/platform build validation remains if later supported. |
| `mcp 1.25.0` | GHSA-84m7-p3x7-pcfv / CVE-2026-59951; PYSEC-2026-3481 / CVE-2026-52870 / GHSA-hvrp-rf83-w775; PYSEC-2026-3482 / CVE-2026-52869 / GHSA-jpw9-pfvf-9f58; PYSEC-2026-3483 / CVE-2026-59950 / GHSA-vj7q-gjh5-988w | Unsupported optional profiles: `adapter`, `blaxel`, `cloud`, `all` | **Yes** for all four records. Candidate `1.30.0`; validate streamable HTTP, task handlers, session checks, and WebSocket host/origin handling if later supported. |
| `oauthlib 3.3.1` | PYSEC-2026-4113 / CVE-2026-49264 / GHSA-hj66-6f7g-4r5v; PYSEC-2026-4114 / CVE-2026-49265 / GHSA-xpv3-w29h-x7cv | Unsupported optional profiles: `gke`, `cloud`, `all` | **Yes** for both. Candidate `4.0.0` is a major release; validate requests-oauthlib and Kubernetes auth compatibility if later supported. |
| `opentelemetry-api 1.43.0` | GHSA-xcq7-p3pf-p88h / CVE-2026-114603 | Unsupported optional profiles: `cloud`, `all` | **Yes.** Candidate API/SDK/exporter/proto/common family `1.45.1` with related instrumentation family `0.66b1`; must update coherently and validate tracing if later supported. |
| `paramiko 3.5.1` | PYSEC-2026-2858 / CVE-2026-44405 / GHSA-r374-rxx8-8654 | Unsupported optional profiles: `beam`, `cloud`, `all` | **Yes.** No fixed version was recorded; no safe version candidate established. |
| `Pillow 12.2.0` | 54 advisory identities: GHSA-22hg-r758-rrw9, GHSA-24rc-8hj2-v98c, GHSA-254f-3936-288h, GHSA-27h8-gf7j-v5hc, GHSA-332p-7hrc-92wf, GHSA-3j72-p6qg-6xp7, GHSA-4558-3h8r-v8xp, GHSA-462x-pgg6-55fp, GHSA-4rm8-3hmm-39fg, GHSA-4rr5-89j8-mwwm, GHSA-58r4-6rv3-gfh8, GHSA-5x8w-8jj5-q52h, GHSA-5xm2-6676-qcp9, GHSA-654x-cwwv-5j9c, GHSA-65qm-jvmh-6pqg, GHSA-74r2-7ff9-mjj2, GHSA-78g4-xqwv-q3g8, GHSA-7mwm-ghpf-9vrm, GHSA-8g5g-8vmr-9782, GHSA-9v9v-9qvf-h2hj, GHSA-c6hw-5grf-ff96, GHSA-cp9v-662q-vvx9, GHSA-f2g6-542v-9j58, GHSA-fc9g-5qg7-mf45, GHSA-g4qv-2jxx-769h, GHSA-g7cr-3p24-7wf7, GHSA-g842-9rc4-69pw, GHSA-gg2r-wvfm-q9rx, GHSA-j4m9-6w36-pw47, GHSA-jg86-v3jv-hrpm, GHSA-mrfp-p49p-3hf2, GHSA-p4wg-p73j-c528, GHSA-p8hx-v2p6-rp84, GHSA-pchr-8j38-3x4p, GHSA-q45j-58j2-45rg, GHSA-rfgq-q3w2-pmv2, GHSA-v9pv-5gc8-w2m6, GHSA-vx6w-vv9f-6gvg, GHSA-w889-685w-c8fh, GHSA-xgh8-jp6q-p5x8, GHSA-xvh5-g6gv-559v, PYSEC-2026-2253, PYSEC-2026-2254, PYSEC-2026-2255, PYSEC-2026-2256, PYSEC-2026-2257, PYSEC-2026-3451, PYSEC-2026-3452, PYSEC-2026-3453, PYSEC-2026-3454, PYSEC-2026-3493, PYSEC-2026-3494, PYSEC-2026-3495, PYSEC-2026-3496 | Unsupported optional profile: Tinker/rewardkit image paths | **Yes** for all 54 records. Candidate `13.0.0`; validate native wheel coverage and image/font behavior if this profile is later supported. |
| `pyarrow 22.0.0` | PYSEC-2026-113 / CVE-2026-25087 / GHSA-rgxp-2hwp-jwgg | Unsupported optional profiles: `huggingface`, `tinker` | **Yes.** Candidate `23.0.1`; validate native wheels, especially Windows ARM64, if later supported. |
| `pyasn1 0.6.3` | PYSEC-2026-3455 / CVE-2026-59884 / GHSA-m4p7-r5rc-7g4j; PYSEC-2026-3456 / CVE-2026-59885 / GHSA-8ppf-4f7h-5ppj; PYSEC-2026-3457 / CVE-2026-59886 / GHSA-hm4w-wwcw-mr6r | Unsupported optional profiles: `computer-1`, `all` | **Yes** for all three. Candidate `0.6.4`; validate Google auth/ASN.1 parsing if later supported. |
| `pydantic-settings 2.12.0` | GHSA-4xgf-cpjx-pc3j / CVE-2026-58203 | Unsupported optional profiles: MCP paths (`adapter`, `blaxel`, `cloud`, `all`) | **Yes.** Candidate `2.14.2`; resolver coupling exists with the proposed LiteLLM upgrade. |
| `setuptools 82.0.1` | GHSA-xmj3-9gf7-h52w; PYSEC-2026-3447 / CVE-2026-59890 / GHSA-h35f-9h28-mq5c | Unsupported optional/build profiles: Tinker/Torch; development tooling path | **Yes** for both records. Candidate `84.1.0`; validate build/install paths if later supported. |
| `torch 2.10.0` | PYSEC-2026-139 / CVE-2026-4538; PYSEC-2025-194 / CVE-2025-3000 / GHSA-rrmf-rvhw-rf47 | Unsupported optional profiles: `tinker`, `all` | `PYSEC-2026-139`: **Yes**, no fixed version recorded. `PYSEC-2025-194`: **No**, current version is outside its affected range. No safe candidate established for the applicable advisory. |
| `transformers 5.5.4` | PYSEC-2026-3929 / CVE-2026-9856 / GHSA-xrqw-3rrv-vx5w; PYSEC-2026-4174 / CVE-2026-80047 / GHSA-x9r9-c232-4q39 | Unsupported optional profiles: `tinker`, `all` | **Yes** for both. Candidate `5.10.0` conflicts with Harbor's explicit `transformers<=5.5.4` cap; do not change the cap without Tinker compatibility evidence. |
| `wheel 0.45.1` | PYSEC-2026-2047 / CVE-2026-24049 / GHSA-8rrh-rw8j-w5fx | Unsupported/early-access profile: `skypilot` | **Yes.** Candidate `0.46.2` conflicts with locked Skypilot's `wheel<0.46`; a reviewed newer Skypilot conflicts with Hugging Face Hub's Click constraint. Declare Skypilot unsupported or resolve that profile before shipping it. |
| `Pygments 2.19.2` | PYSEC-2026-2987 / CVE-2026-4539 / GHSA-5239-wwwm-4pmq | Development-only | **Yes.** Candidate `2.20.0`; refresh and validate pytest console output. |
| `pytest 9.0.2` | PYSEC-2026-1845 / CVE-2025-71176 / GHSA-6w46-j5rx-g56g | Development-only | **Yes.** Candidate `9.0.3`; validate test runner/plugin behavior. |
| `soupsieve 2.8.3` | PYSEC-2026-3071 / CVE-2026-49476 / GHSA-2wc2-fm75-p42x; PYSEC-2026-3072 / CVE-2026-49477 / GHSA-836r-79rf-4m37; PYSEC-2026-4170 / CVE-2026-86000 / GHSA-gjv8-xp57-g29c; PYSEC-2026-4171 / CVE-2026-85999 / GHSA-j934-xhv5-fg8f | Development-only: rewardkit test dependency | **Yes** for all four. Candidate `2.9.0`; validate rewardkit HTML parsing. |
| `tornado 6.5.4` | GHSA-3hv7-mjh2-fv65 / CVE-2026-103261; GHSA-8423-8fgw-73vq / CVE-2026-91990; GHSA-c2m8-h5v5-343r / CVE-2026-103263; GHSA-chx6-46f5-w4vp / CVE-2026-103262; GHSA-pw6j-qg29-8w7f / CVE-2026-91992; PYSEC-2026-140 / CVE-2026-31958 / GHSA-qjxf-f2mg-c6mc; PYSEC-2026-2287 / CVE-2026-35536; PYSEC-2026-3387 / CVE-2026-49853; PYSEC-2026-3388 / CVE-2026-49854; PYSEC-2026-3389 / CVE-2026-49855; PYSEC-2026-3928 / CVE-2026-82397 / GHSA-mpf4-983q-p7j4 | Development-only: ipykernel/notebook tooling | **Yes** for all 11. Candidate `6.5.9`; validate notebook/kernel startup and request parsing. |

The default/core dependency set has no remaining confirmed, applicable advisory for Harbor's supported code path in this reviewed inventory. LiteLLM remains an affected package version, but its two findings are Proxy-specific and outside the maintainer-declared supported Harbor deployment. Repository inspection cannot establish what an external operator deploys. A package inventory scan is point-in-time; this conclusion is limited to current OSV data available for review on 2026-10-25 and the retained OSV record set.

For detailed advisory IDs, aliases, candidate versions, and resolver constraints, see `OSV_ADVISORY_REVIEW.md`. No speculative dependency upgrades were made in this policy pass. Findings remain relevant if users install unsupported extras, but they are outside this release's security-support promise. Revisit the profile policy before a later release claims security support for any extra. The LiteLLM Proxy findings do not establish an exploitable Harbor endpoint; external operator deployments remain outside repository evidence.

## TEST STATUS

The retained completed Windows run reported 13,743 collected, 13,049 passed, 351 failed, 342 skipped, and 1 error. This 2026-10-25 run is diagnostic historical evidence only, not a supported CI run and not a green full-suite result. The current focused regression suite is a separate selection and reported **633 passed, 5 skipped** as recorded above. Targeted verification in the earlier review ran with `PYTHON_DOTENV_DISABLED=1` to avoid loading dotenv values from above the repository; dotenv-autoload tests were not selected. The earlier 580-test command was:

```text
.audit-test-venv\Scripts\python.exe -m pytest tests/unit/agents/terminus_2 tests/unit/llms/test_lite_llm.py tests/unit/llms/test_litellm_config.py tests/unit/cli/test_config_composition.py tests/unit/cli/test_config_validation.py tests/unit/cli/test_trials_config_composition.py tests/unit/cli/test_jobs_start_retry.py tests/unit/cli/test_mcp_config.py tests/unit/models/test_task_config_network.py tests/unit/models/test_task_config_env.py tests/unit/models/test_task_config_mcp.py tests/unit/trial/test_network_policy.py -q -vv --tb=no
```

Result: **580 passed, 27 warnings in 170.99s**. No full suite was invoked. A separate `.audit-test-venv\\Scripts\\python.exe -m pytest tests/unit/test_telemetry.py tests/unit/cli/test_main_telemetry.py -q -k "opt_out or posthog_by_default or stable_allowlisted_projection or command_telemetry" --tb=short` run reported **12 passed, 24 deselected**. These tests use mocked capture and did not send events. The broader telemetry selection attempted in the previous turn was interrupted during the telemetry module and has no summary; the narrower telemetry run passed. The October 24 initial audit's full run stalled with 60 collection errors and no final execution summary; it is not a pass and is superseded as the current test count by the later completed report.

The earlier clean-dotenv full run did not finish and has no JUnit summary. The full `tests/unit` suite was not run for the current validation. The supported CI workflow uses Ubuntu and Windows runners, Python 3.13, 15-minute non-runtime job limits and separate Linux runtime tests; those jobs have not been executed as part of this validation. The failed Windows-only clusters should not be represented as project regressions, but the unavailable supported CI result remains a release confidence gap.

## FAILURE CLASSIFICATION

The completed Windows run's 351 failures and one error are classified from the retained sanitized JUnit evidence and prior investigation:

- 283 symlink tests fail before application behavior with Windows `WinError 1314`.
- 27 LangGraphJS tests fail during Node inspection of a user-profile path (`EPERM`).
- 9 tests require POSIX `sh`; 6 trajectory-sync cases time out in those shell-dependent paths.
- 8 Mosaic and 6 Fabric failures plus one Fabric import error require absent optional runtimes.
- 2 Vercel VCR tests encounter Windows cache `WinError 5`.
- 10 agent/model/auth tests are affected by dotenv values inherited from above the workspace. Those values are not included here and the external file was not inspected. Isolated targeted evidence in the prior report showed the affected checks pass with dotenv isolated.
- 0 failures were attributed to the approved dependency refresh in the earlier focused regression review. This classification is based on test evidence and is not a proof that no unrelated defect exists.

The categories sum to the reported totals. No failing cluster was rerun in this pass because the retained report already identifies the mechanism and a supported Linux/Windows CI execution would distinguish project behavior more usefully.

## TYPE-CHECK STATUS

The prior full `ty` output was not retained; the audit recorded approximately 40 diagnostics, summarized as unresolved LiteLLM imports in its incomplete environment, four optional Smol imports, and two LiteLLM-dependent typing diagnostics in `src/harbor/llms/utils.py`. The exact individual 40 diagnostics cannot be reconstructed from the summary, so the earlier count cannot be item-classified more precisely. The four Smol imports are optional/platform dependency diagnostics, not issues in the changed Terminus-2 modules. The LiteLLM unresolved imports and two derived typing diagnostics were dependency/stub artifacts. This narrow command passed with **All checks passed!**:

```text
.venv\Scripts\ty.exe check --python .audit-test-venv src/harbor/agents/terminus_2/adaptive_recovery.py src/harbor/agents/terminus_2/autonomous.py src/harbor/agents/terminus_2/benchmark_suite.py src/harbor/agents/terminus_2/failure_classifier.py src/harbor/agents/terminus_2/orchestration.py src/harbor/agents/terminus_2/task_planner.py src/harbor/agents/terminus_2/terminus_2.py src/harbor/agents/terminus_2/trajectory_evaluation.py src/harbor/llms/utils.py --output-format concise --no-progress
```

The same paths checked against incomplete `.venv` produced unresolved imports and downstream type noise, confirming the environment cause. No code issue was identified; ty config was not changed.

## TELEMETRY STATUS

Telemetry is enabled by default; `HARBOR_TELEMETRY=0`, `false`, `no`, `off`, or `disabled` opts out. The code sends allowlisted command/job metadata to PostHog's public event-capture endpoint from a detached process. Fields include runtime/platform, command/subcommand and recognized option names, Harbor dataset/package-task references, public Git references, agent/provider/model labels, outcome, durations, usage/cost aggregates, and exception type names. The schema excludes raw commands/configuration, prompts, environment values, exception messages, and tracebacks. The embedded value starts with `phc_` and is sent as the project token to the public capture endpoint. PostHog documents `phc_` project tokens as public, write-only/client-side tokens that cannot access private data; no personal or project-secret API credential is embedded. [PostHog API overview](https://posthog.com/docs/api), [PostHog project-token guidance](https://posthog.com/docs/privacy). No telemetry was sent in this review. README disclosure and the telemetry page describe default-on collection and opt-out. **The maintainer confirms the project belongs to Harbor and is intended to remain in this release; this confirmation is not independent technical verification against PostHog project settings.**

## PUBLIC REPOSITORY SECURITY SWEEP

Prior recorded scans found no `.env` or private-key files in project source and no GitHub-token-shaped values. They found the PostHog client project token and credential-shaped test/example sentinels; no values are reproduced here. The test run emitted credential-shaped values from an ancestor dotenv source; that external file was not inspected, raw outputs were sanitized, and no value is included here. This environment should be isolated from inherited dotenv values for future test runs. No confirmed genuine secret was identified in the project files by the recorded scan. The earlier review found no root `.env`; ignored audit environments/caches and local trials were present. Git metadata now exists in the repository. A full credential-pattern rescan was not repeated in that review.

`SECURITY.md` documents `tejasash2001@gmail.com` as the private vulnerability-reporting contact for this release and instructs reporters not to disclose vulnerability details publicly before the maintainer has had an opportunity to investigate. This documentation does not claim that GitHub Security Advisories or another dedicated security service is enabled.

## DOCUMENTATION STATUS

README telemetry disclosure links to the telemetry docs, which list event fields and opt-out. README now states the declared Python lower bound, the Python version/OSes exercised by CI, and limits claims for optional extras. The docs do not establish macOS support. Existing report evidence found no genuine broken repository Markdown links; generation-relative template links remain context-specific. This review did not run a new link crawler or inspect every example/template. `CONTRIBUTING.md` exists and is unchanged. `SECURITY.md` documents the private reporting contact for this release; GitHub Security Advisories are not claimed to be enabled.

## GIT / PROVENANCE STATUS

The intended comparison baseline is upstream Harbor v0.24.0 tag, commit `b53b8134e1241686dca7759af188f987ecc48e8b`, as documented in `AUDIT_REPORT.md`. This snapshot cannot be proven to derive from that commit: the current Git repository has no established ancestry to that reference, and no verified source archive hash is recorded. Git status at this review shows 3,657 staged additions and 13 modified working-tree paths, with no untracked files. This does not establish authorship or provenance. The source tree should be compared with a verified source archive before public release. Keep intended source/config/docs/tests and benchmark materials; exclude ignored audit caches, virtual environments, local results/data, secrets, and build outputs. Keep `uv.lock` because it supports reproducible workspace installs.

Git is initialized in the current workspace. The original staged snapshot remains staged; this review does not alter the index. Before publication, record the verified baseline/archive hash if available, inspect the complete staged diff, confirm ignored artifacts are not staged, and preserve the provenance mapping. No publication occurred here.

## COMPLETE AUDIT-WIDE FILE INVENTORY

Git history does not establish source ancestry; the inventory is a reconciliation of the October 24 audit's upstream comparison, recorded edits, present files, and timestamps. The audit comparison found 3,655 active project files, 238 paths present only in this tree, 314 common paths with byte differences (two line-ending-only), and four baseline-only paths. The exact path-level current-only, baseline-only, and common-difference lists are retained in the `Baseline comparison appendix` of `AUDIT_REPORT.md`; these indicate differences from the candidate upstream tag, not authorship.

### A. Project changes intentionally made during project work

The audit evidence records the following non-audit source/config/test changes as intentional project work; historical authorship cannot be proven without Git:

- `.gitignore` (dataset/cache/audit exclusions; subsequently strengthened for credential file extensions)
- `adapters/dacode/parity/da_harbor_agent/agent/agents.py`
- `adapters/spider2-dbt/src/spider2_dbt/run_spider_agent_dbt.py`
- `adapters/webgen_bench/src/webgen_bench/task-template/tests/webvoyager/utils.py`
- `benchmarks/terminus2-phase8/adapters/adaptive_adapter.py`
- `benchmarks/terminus2-phase8/adapters/baseline_adapter.py`
- `benchmarks/terminus2-phase8/adapters/harbor_trial_supervisor.py`
- `benchmarks/terminus2-phase8/adapters/supervised_process_adapter.py`
- `scripts/run_terminus2_benchmark_campaign.py`
- `scripts/terminus2_phase8_eval.py`
- `scripts/validate_terminus2_archive.py`
- `src/harbor/agents/terminus_2/adaptive_recovery.py`
- `src/harbor/agents/terminus_2/autonomous.py`
- `src/harbor/agents/terminus_2/benchmark_suite.py`
- `src/harbor/agents/terminus_2/failure_classifier.py`
- `src/harbor/agents/terminus_2/orchestration.py`
- `src/harbor/agents/terminus_2/task_planner.py`
- `src/harbor/agents/terminus_2/terminus_2.py`
- `src/harbor/agents/terminus_2/trajectory_evaluation.py`
- `tests/unit/agents/terminus_2/test_adaptive_recovery.py`
- `tests/unit/agents/terminus_2/test_autonomous.py`
- `tests/unit/agents/terminus_2/test_benchmark_suite.py`
- `tests/unit/agents/terminus_2/test_failure_classifier.py`
- `tests/unit/agents/terminus_2/test_orchestration.py`
- `tests/unit/agents/terminus_2/test_phase8_eval.py`
- `tests/unit/agents/terminus_2/test_task_planner.py`
- `tests/unit/agents/terminus_2/test_trajectory_evaluation.py`

The audit report attributes Ruff formatting, unused-import/local cleanup, Python 3.13 invalid-escape warning repairs, and Terminus-2 typing repairs to these files. Earlier review records two narrowly changed tests: `tests/unit/cli/test_jobs_start_retry.py` and `tests/unit/cli/test_trials_config_composition.py` (Rich path-wrap assertion normalization).

### B. Audit/release-process changes

- `.gitignore` (audit additions and current credential-pattern additions)
- `README.md` (telemetry disclosure predates this pass; supported-profile wording and maintainer-confirmed PostHog ownership recorded this pass)
- `docs-mintlify/telemetry/telemetry.mdx` (maintainer-confirmed ownership and lack of independent technical verification recorded this pass)
- `SECURITY.md` (private reporting contact and supported-profile scope recorded)
- `AUDIT_REPORT.md` (audit report and evidence appendix)
- `OSV_ADVISORY_REVIEW.md` (advisory investigation; current release-policy scope clarified this pass, with historical candidate/count evidence retained)
- `DEPENDENCY_DECISION_MEMO.md` (historical proposal; current policy decision and supported scope clarified this pass)
- `FINAL_RELEASE_REVIEW.md` (this authoritative report)
- `tests/unit/cli/test_jobs_start_retry.py`
- `tests/unit/cli/test_trials_config_composition.py`

The approved dependency refresh changed `pyproject.toml` and `uv.lock` relative to the original audit baseline according to the October 25 report, although the earlier AUDIT_REPORT described the pre-refresh state. The previous final report says both files were unchanged from its immediate pre-refresh baseline. Git history does not establish exact historical authorship or byte deltas against the original source archive; no dependency file was edited in the current validation pass.

### C. Temporary audit artifacts and retained evidence

Root-level retained sanitized evidence: `.audit-clean-pytest.sanitized.log`, `.audit-final-pytest.sanitized.log`, `.audit-final-results.sanitized.xml`, `.audit-full-pytest.sanitized.log`, `.audit-full-results.sanitized.xml`, `.audit-hermetic-pytest.sanitized.log`, `.audit-hermetic-results.sanitized.xml`, `.audit-final-baseline.json`.

Audit directories: `.audit-cargo/`, `.audit-pytest-temp/`, `.audit-rustup/`, `.audit-test-venv/`, `.audit-unit-temp/`, and `.uv-cache/` (temporary upstream clone, build products, OSV input/output and temporary test material as described by `AUDIT_REPORT.md`). These directories are ignored and must not enter a release tree. They were preserved; no evidence was deleted in this pass.

### D. Generated/cache files and local data

Present generated/local state includes `.venv/`, `.hypothesis/`, `.pytest_cache/`, `.ruff_cache/`, `.uv-cache/`, `trials/`, Python `__pycache__`/`.pyc` files, and likely tool-local artifacts under audit directories. Root `dataset/` was absent in the recorded check. These are excluded by `.gitignore` rules; individual nested files were not enumerated. This inventory does not assert that every ignored path is harmless or empty.

### E. Uncertain historical changes

All 238 current-only paths, 314 byte-different common paths, and four baseline-only paths are uncertain historical changes relative to the upstream candidate tag. The audit's complete lists remain in `AUDIT_REPORT.md`. None can be reliably classified as project-authored versus pre-existing ZIP content or audit modification without Git provenance and a verified source archive. File timestamps support sequence only, not authorship.

## REMAINING BLOCKERS

1. The two LiteLLM Proxy advisories remain applicable to locked LiteLLM 1.93.0, but are outside Harbor's supported/default deployment profile. This does not establish what an external operator deploys; operators of Proxy remain outside this repository's supported profile.
2. Affected dependencies remain in unsupported optional profiles and the development dependency profile. Some have no reviewed fixed version or conflict with project constraints (`diskcache`, `paramiko`, Torch, Transformers/Tinker, Wheel/Skypilot). The all-extras CI profile is therefore not shown safe, and no security support is claimed for these profiles.
3. No clean supported CI run from this release candidate is available; full type checking is unresolved in the incomplete environment.
4. Exact source provenance remains unverified: Git history does not establish ancestry to the comparison baseline, and a verified source archive hash is not recorded. The provenance document records the maintainer's stated acceptance of this limitation; it is not independent verification.

## NON-BLOCKING LIMITATIONS

- The retained 351 Windows failures plus one error are explained by platform permissions, shell availability, absent optional runtimes, cache access and inherited dotenv values; they do not establish 352 product defects.
- macOS support and Python versions newer than 3.13 are not established by this workspace's CI evidence.
- Audit caches and virtual environments remain on disk but are ignored; this pass preserved evidence rather than deleting it.
- Independent technical verification of PostHog project ownership against project settings is unavailable; maintainer confirmation for this release is recorded above.

## EXACT MAINTAINER ACTIONS REQUIRED

1. Run the repository's supported Python 3.13 CI jobs on Linux and Windows with clean environment variables; resolve remaining failures and obtain a complete `ty check` result from a fully installed profile.
2. Preserve the provenance caveat, inspect the staged tree against this inventory, and exclude `.audit-*`, `.uv-cache`, virtual environments, local data, secrets and build outputs.

## FINAL RECOMMENDATION

Do not publish this tree yet. Before public publication, obtain supported CI/type-check evidence. The private reporting contact is documented in `SECURITY.md`; the report does not claim GitHub Security Advisories are enabled. The maintainer has accepted the documented source-provenance limitation and confirmed PostHog project ownership and intended use; the latter is not independently verified against PostHog project settings. The supported public security profile is default/core only; optional profiles and development dependencies remain unsupported for this release and retain the package-level findings documented above. LiteLLM Proxy advisories are outside the supported Harbor deployment profile, while external operator deployments cannot be determined from repository inspection. No external publication has occurred.
