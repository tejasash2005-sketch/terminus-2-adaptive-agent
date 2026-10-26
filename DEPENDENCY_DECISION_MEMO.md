# Dependency decision memo

> **Maintainer decision applied (2026-10-25).** For this public release, the supported security profile is the default/core profile only. The optional extras `huggingface`, `tinker`, `dspy`, `adapter`, `blaxel`, `langsmith`, `gke`, `beam`, `computer-1`, `cloud`, and `all` are unsupported; the development dependency group is not a supported public runtime profile. `skypilot` remains explicitly early-access/unsupported. Findings and candidate data below are preserved for the affected package paths; unsupported status is not remediation, and no functionality or dependency versions were removed or changed. Harbor's supported deployment does not operate LiteLLM Proxy; its two Proxy advisories are outside that deployment profile, but repository inspection cannot establish what an external operator deploys. See `FINAL_RELEASE_REVIEW.md` for current release status.

> **Historical proposal, superseded in part (2026-10-25).** This memo records a pre-refresh proposal and says no dependency files had then been changed. The later review records an approved default dependency refresh reflected in the current `pyproject.toml` and `uv.lock`; see `FINAL_RELEASE_REVIEW.md` for reconciled status. Optional-profile recommendations and unresolved compatibility decisions remain relevant. Labels of OpenTelemetry, `pydantic-settings`, and setuptools as potentially Core should not be read as proof they are default dependencies.

**Date:** 2026-10-24
**Evidence:** `AUDIT_REPORT.md`, `OSV_ADVISORY_REVIEW.md`, `pyproject.toml`, `uv.lock`, and repository searches.
**Status:** Decision proposal only. No source, dependency declaration, or lockfile was changed.

## 1. LiteLLM Proxy usage (historical evidence, current decision above)

Harbor's supported deployment does **not** operate LiteLLM Proxy. Harbor declares LiteLLM as a direct dependency and uses it as a model client. The reviewed source contains no `litellm.proxy` import or proxy-server startup/configuration. Proxy mentions found are external model endpoints, comments, tests, or unrelated proxies. Repository inspection cannot establish what an external operator deploys; such deployments are outside this supported profile.

If Proxy is operated, `litellm==1.100.4` is the lowest stable candidate in the review that covers both LiteLLM findings. `1.93.2` covers only one and leaves the critical Proxy advisory applicable. If Proxy is not operated, the two findings remain present in the locked library version, but the reviewed vulnerable Proxy surface is not evidenced in Harbor's default use.

## 2. Confirmed findings by install profile

The OSV follow-up resolved **147 of 148** canonical scanned advisory IDs as applicable to locked versions; one Torch record is outside its affected range. This means affected version ranges, not 147 independent vulnerabilities or proof of exploitability. The lock contains optional and development packages because the dev group selects many extras. `pyproject.toml` defines the following direct/default-runtime findings in the review's candidate table:

| Scope | Locked package(s) with applicable findings | Proposed reviewed candidate(s) |
|---|---|---|
| Default/core runtime | `aiohttp`, `anyio`, `certifi`, `cryptography`, `filelock`, `h2`, `hpack`, `pyjwt`, `requests`, `starlette`, `urllib3` | `3.14.4`, `4.14.2`, `2026.10.19`, `50.0.0`, `4.2.1`, `4.4.1`, `4.2.0`, `2.15.0`, `2.33.0`, `1.3.1` with FastAPI `0.133.0`, `2.8.0` respectively |
| LiteLLM library; Proxy advisories outside supported deployment profile | `litellm==1.93.0` | `1.100.4` candidate remains technical evidence if Proxy support is later added; no upgrade is made for this release boundary |
| Unsupported optional extras/workspace packages | `claude-agent-sdk`, `datasets`, `fsspec`, `lxml`, `mcp`, `oauthlib`, `pillow`, `pyarrow`, `pyasn1`, `langsmith` | Reviewed candidates are recorded in `OSV_ADVISORY_REVIEW.md`; findings are not remediated and no security-support claim is made for these profiles |
| Optional, no fixed version found | `diskcache`, `paramiko`, `torch` | No fixed candidate in reviewed advisory metadata; track/assess vendor mitigation. Torch's separate `PYSEC-2025-194` does not apply |
| Development / dev-selected extras | `pytest`, `pygments`, `soupsieve`, `tornado` | `9.0.3`, `2.20.0`, `2.9.0`, `6.5.9` |

Nuance: the prior review labels `opentelemetry-api`, `pydantic-settings`, and `setuptools` as Core in its table, but their documented dependency paths are selected optional cloud, LiteLLM-candidate, or tinker/dev paths, not all necessarily in a minimal base install. They are needed in the broader default + dev candidate resolution described by that review. OTel family candidates: API/SDK/exporter/proto/common `1.45.1`, related instrumentation/semantic-convention packages `0.66b1`. `pydantic-settings` candidate `2.14.2`; `setuptools` candidate `84.1.0`. Confirm the intended install profile before treating those as mandatory base-runtime updates.

## 3. Smallest coherent proposal and companions

The historical smallest security-focused *profile* proposal was to update default runtime findings together and refresh dev-only findings separately. The current release decision supersedes its assumed scope: default/core only is supported; optional extras and the development group are outside the public security-support promise. This is not a claim that their findings are fixed or packages safe.

For LiteLLM `1.100.4`, required companion resolution includes `boto3==1.43.1`, aligned `botocore==1.43.1`, `s3transfer>=0.17,<0.18` (review candidate `0.17.0`), `fastuuid>=0.14`, `pydantic-settings>=2.14.1`, and `aiohttp>=3.14.2`; the proposed aiohttp `3.14.4` satisfies that minimum. Boto3/s3transfer are also required by the `ec2` extra and must stay aligned. `multidict==6.9.1` accompanies the aiohttp fix.

Keep coupled packages coherent: FastAPI/Starlette (`0.133.0`/fixed Starlette candidate), HTTP/2 (`h2`/`hpack`), Requests/urllib3, and the OpenTelemetry family if that profile is included. The resolver found a default + dev candidate solution for Python 3.12 and 3.13. Review its full lock diff before adoption.

## 4. Constraint changes and unresolved conflicts

- **Transformers:** candidate `5.10.0` cannot resolve under `pyproject.toml`'s `tinker` extra cap `transformers>=5.3.0,<=5.5.4`. Supporting the proposed fix requires a maintainer decision and changing that declared upper bound, then validating tinker-cookbook compatibility.
- **Skypilot/Wheel:** current optional Skypilot nightly requires `wheel<0.46`, conflicting with Wheel's reviewed fix `>=0.46.2`. A reviewed newer Skypilot nightly accepts `wheel>=0.46.3` but requires `click<8.2`, conflicting with Hugging Face Hub's `click>=8.4.2`. Fixing this optional profile requires deciding whether Skypilot remains supported and resolving both constraints; do not force it into the base profile.
- **FastAPI/Starlette:** current FastAPI `0.128.0` caps Starlette below `0.51`; moving Starlette to the reviewed fixed range requires a FastAPI update to at least the reviewed `0.133.0` candidate. This changes the framework version but remains within the existing declared `fastapi>=0.128.0` constraint; no root constraint edit is indicated by the reviewed metadata.
- **LiteLLM:** current root constraint is `litellm>=1.92.0`; candidate `1.100.4` fits without a declared constraint change. Companion packages arise from metadata/resolution; the documented boto3 requirement is at least `1.43.1`, which conflicts with currently locked boto3/botocore `1.41.5` and s3transfer `0.15.x`.
- Other reviewed candidates fit existing broad root constraints according to the prior resolution, but major API changes (e.g. `filelock 4`, `oauthlib 4`, `datasets 5`) and native-wheel gaps need platform validation. Cryptography `50.0.0` lacked reviewed wheels for Windows arm64 and macOS Intel.

## 5. Python evidence

PyPI metadata for proposed candidates was reviewed as supporting Python 3.12, 3.13, and 3.14; Windows x64/CPython 3.13 binary-only candidate dry-run succeeded. `uv pip compile` candidate default + dev resolution succeeded for Python 3.12 and 3.13. The Python 3.14 universal resolution timed out fetching `psutil` metadata and is **unverified**; there is no native Python 3.14 execution evidence. The project declares `requires-python = ">=3.12"`, so broader future compatibility is also unverified.

## 6. Verification after an authorized refresh

Run `uv lock --check`, install/sync the intended profiles on Python 3.12 and 3.13, review the lock diff and rerun OSV against the resulting lock. Then run `uv run pytest tests/unit/` as the repository's default verification scope, plus the focused checks from the review: LiteLLM model/provider and (if applicable) Proxy auth/role tests; HTTP/HTTP2 and FastAPI/ASGI regression tests; JWT/auth and crypto tests; file-lock/cache concurrency tests; and profile-specific adapter/cloud tests. For dev changes include pytest plugin collection, rewardkit HTML parsing, and notebook/Tornado startup. Run integration/runtime tests only for affected code and in a usable external-service/Docker environment. The earlier full suite was incomplete (60 collection errors); do not report it as passing. Type checking also remains blocked by missing dependencies/diagnostics.

## 7. Historical questions and remaining maintainer actions

1. The Proxy/profile questions above were answered for this release as recorded in the maintainer decision at the top. Revisit only if the supported deployment or security-support scope changes.
2. Should the tinker Transformers upper bound be raised, and which versions does tinker-cookbook support, if that optional profile is later approved for support?
3. How should consumers handle the applicable `diskcache`, `paramiko`, and `torch` findings that have no reviewed fixed release, if those profiles are later approved for support?
4. Is native-build validation available for platforms without candidate wheels, if those profiles are later approved for support?

No lock refresh or version change is authorized by this memo. The previous audit's restrictions remain in force.
