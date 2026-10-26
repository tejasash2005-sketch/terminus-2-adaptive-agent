# Harbor

 [![](https://dcbadge.limes.pink/api/server/https://discord.gg/QVvyhRw5UQ)](https://discord.gg/QVvyhRw5UQ)
[![Docs](https://img.shields.io/badge/Docs-000000?style=for-the-badge&logo=mdbook&color=105864)](https://harborframework.com/docs)
[![Cookbook](https://img.shields.io/badge/Cookbook-000000?style=for-the-badge&logo=mdbook&color=105864)](https://github.com/harbor-framework/harbor-cookbook)
[![DOI](https://zenodo.org/badge/1032170083.svg)](https://doi.org/10.5281/zenodo.20953922)



Harbor is a framework from the creators of [Terminal-Bench](https://www.tbench.ai) for evaluating and optimizing agents and language models. You can use Harbor to:

- Evaluate arbitrary agents like Claude Code, OpenHands, Codex CLI, and more.
- Build and share your own benchmarks and environments.
- Conduct experiments in thousands of environments in parallel through providers like Daytona, Modal, LangSmith, Blaxel, Novita Sandbox, Tensorlake, Runta, and Sail.
- Generate rollouts for RL optimization.

Check out the [Harbor Cookbook](https://github.com/harbor-framework/harbor-cookbook) for end-to-end examples and guides.

Harbor usage telemetry is enabled by default and can be disabled. See the
[usage stats documentation](https://harborframework.com/docs/usage-stats) for
what is collected and how to opt out. The embedded PostHog project's ownership
has been confirmed by the maintainer as belonging to Harbor and intended to
remain in this release. This records maintainer confirmation; repository evidence
does not independently verify ownership against PostHog project settings.

## Experimental: Terminus-2 Adaptive Terminal Intelligence

This repository snapshot also includes an experimental extension to Terminus-2:
conservative terminal-failure classification, recovery guidance, per-run recovery
telemetry, optional persistent recovery-outcome memory, and a JSON results evaluator.
The extension avoids automatic command retries because a timed-out command may
already have changed the environment. Its task-planning module validates structured
step proposals, dependencies, status transitions, remediation replans, and an opt-in
multi-component dispatcher with explicit routing and dependency-aware failure handling.
Handlers are injected; the opt-in `autonomous.py` extension now uses Harbor's existing
`BaseLLM` abstraction for structured planning and an injected, policy-enforcing executor
and verifier for guarded sequential execution. It does not execute model-generated shell
text or automatically replace Terminus-2’s interactive agent loop. The offline regression
suite in `benchmark_suite.py` checks core orchestration and safety behavior; it is not an
external-model performance study.

See [the adaptive-intelligence design and usage guide](docs/terminus2-adaptive-intelligence.md)
for configuration, telemetry semantics, evaluation instructions, and explicit phase
status. The benchmark evaluator is tooling only; measured baseline-versus-adaptive
results must be collected before making performance claims.

### Phase 7 release hardening

Phase 7 adds stricter autonomous-run configuration and checkpoint validation,
JSON-safe executor result contracts, cancellation checkpoints, unique atomic
checkpoint staging files, and a repeatability campaign for the offline regression
suite. From a fully installed development checkout, run the focused tests and
repeatability campaign and ZIP structural validation using the commands in
[`benchmarks/terminus2-phase7/README.md`](benchmarks/terminus2-phase7/README.md).
Synthetic timings are local regression measurements, not external-model or
real-world performance claims. See the guide for release status and remaining
validation requirements.

### Phase 8 empirical evaluation harness

Phase 8 adds a frozen 100-case benchmark manifest, a paired randomized runner for
user-supplied baseline/adaptive adapters, independent workspace oracles, controlled
fault-injection hooks, append-only JSONL run records, and task-cluster bootstrap
analysis. It does **not** ship empirical agent results: a real campaign requires
reviewed adapters, externally enforced isolation/resource limits, and independently
verified executions. See [`benchmarks/terminus2-phase8/README.md`](benchmarks/terminus2-phase8/README.md),
its adapter contract and preregistration template, and the harness tests.

## Installation

Harbor declares Python 3.12 or newer. The repository CI currently exercises
Python 3.13 on Linux and Windows. For this release, the supported public security
profile is the default/core install. Optional extras remain available in the
project but are unsupported profiles for this release: `huggingface`, `tinker`,
`dspy`, `adapter`, `blaxel`, `langsmith`, `gke`, `beam`, `computer-1`, `cloud`,
and `all`. Skypilot is early access and unsupported; development dependencies are
not a supported runtime profile. See [SECURITY.md](SECURITY.md) for the security
support boundary and publication prerequisite.

```bash tab="uv"
uv tool install harbor
```
or
```bash tab="pip"
pip install harbor
```


## Example: Running Terminal-Bench-2.0
Harbor is the official harness for [Terminal-Bench-2.0](https://github.com/laude-institute/terminal-bench-2):

```bash
export ANTHROPIC_API_KEY=<YOUR-KEY>
harbor run --dataset terminal-bench@2.0 \
   --agent claude-code \
   --model anthropic/claude-opus-5-5 \
   --n-concurrent 4
```

This will launch the benchmark locally using Docker. To run it on a cloud provider (like Daytona) pass the `--env` flag as below:

```bash
export ANTHROPIC_API_KEY=<YOUR-KEY>
export DAYTONA_API_KEY=<YOUR-KEY>
harbor run --dataset terminal-bench@2.0 \
   --agent claude-code \
   --model anthropic/claude-opus-5-5 \
   --n-concurrent 100 \
   --env daytona
```

To see all supported agents, and other options run:

```bash
harbor run --help
```

To explore all supported third party benchmarks (like SWE-Bench and Aider Polyglot) run:

```bash
harbor datasets list
```

To evaluate an agent and model one of these datasets, you can use the following command:

```bash
harbor run -d "<dataset@version>" -m "<model>" -a "<agent>"
```

## Citation

If you use **Harbor** in academic work, please cite it using the “Cite this repository” button on GitHub or the following BibTeX entry:

```bibtex
@software{Harbor_Framework,
author = {{Harbor Framework Team}},
title = {{Harbor: A framework for evaluating and optimizing agents and models in container environments}},
year = {2026},
doi = {10.5281/zenodo.20953922},
url = {https://doi.org/10.5281/zenodo.20953922}
}
```

The DOI above is the **concept DOI**, which always resolves to the latest release and aggregates citations across all versions. To cite a specific version instead, use that version's DOI from the [Zenodo record](https://doi.org/10.5281/zenodo.20953922).
