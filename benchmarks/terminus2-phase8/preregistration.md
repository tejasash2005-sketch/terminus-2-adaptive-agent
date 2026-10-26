# Phase 8 preregistration v2

This is a preregistered benchmark specification for manifest v2. Timestamp and archive the final signed copy before confirmatory runs. No empirical results are contained here.

## Research question and systems

- Primary question: does the Phase 7 adaptive Terminus-2 configuration improve independently verified task success over the frozen baseline?
- Baseline revision/config hash: record immediately before confirmatory execution.
- Adaptive revision/config hash: record immediately before confirmatory execution.
- Model/provider/version and parameters: record immediately before confirmatory execution.
- Executor/verifier revision: record immediately before confirmatory execution.
- Benchmark manifest content SHA-256: `cc444864ae2b59541d5757e8110dde8e0c736ca53cd9edb31622dc42db989d5d`
- Benchmark manifest schema: `harbor-terminus2-phase8-manifest-v2`

## Design

- Benchmark: 100 task cases, 20 in each of routine, recovery, dependencies, state-change, and safety categories.
- Runnable-category policy for the current Harbor supervisor: routine, dependencies, and state-change are structurally runnable; recovery and safety are explicitly blocked pending their required enforcement integrations. Blocked categories are not empirical failures and must not be counted as executed trials.
- Pilot: 3 paired seeds per case; pilot results are for harness validation and sample-size estimation only. If the pilot influences task selection/tuning, exclude affected cases from confirmatory analysis or issue a new frozen benchmark version.
- Confirmatory plan: 5 paired seeds per currently runnable case (600 assigned executions total: 60 runnable cases × 5 seeds × 2 systems) unless the pre-run power analysis requires more. The 40 blocked cases are not assigned executions.
- Seeds: 11, 29, 47 for pilot; 11, 29, 47, 71, 97 for proposed confirmatory plan.
- Pairing: each task-seed executes once per system from equivalent clean state. Randomize execution schedule using a published seed. Isolate checkpoints, caches, and persistent recovery knowledge between systems.
- Limits and fairness conditions: 60-second task timeout, 20 declared tool/model-call budgets (not independently enforced by the stock supervisor), $1 declared monetary budget (not independently enforced), 2 CPU, 4096 MiB memory, 4096 MiB storage, disposable Docker environment, and equivalent baseline/adaptive task inputs. Actual billed cost and provider-call counts must come from independent telemetry where available.

## Endpoints

- Primary: absolute difference in independently verified success rate, adaptive minus baseline, in percentage points.
- Secondary: category success rates, latency distributions, paired latency delta, measured cost per assigned run and per verified success, retries/replans/tool calls, recovery success, budget exhaustion, false completion, safety incidents.
- Success oracle: independent workspace checks plus task-specific relationships. Dependency cases require stage1 to preserve the declared source fields and stage2 to reference stage1 and the declared source derivation input. State-change cases require the current state to equal the preregistered transition `after` state and the result to report that current state. Routine cases require exact artifact JSON. Blocked categories have no confirmatory endpoint until their missing enforcement is integrated and separately preregistered.
- Timeout, agent crash, failed oracle, or exhausted agent budget: failure. Invalid-run exclusions only for predeclared infrastructure failures independent of agent behavior; disclose every exclusion and rerun.

## Statistical analysis

- Primary uncertainty: 95% percentile cluster bootstrap interval, resampling task IDs and retaining all seeds and both systems within each sampled task; 10,000 resamples; seed `20261023` unless changed before runs.
- Report baseline/adaptive rates, absolute difference, interval, paired discordance counts, and all category-level results.
- Secondary paired test: McNemar exact test on paired task-seed outcomes may be reported descriptively; repeated seeds remain clustered within task for the primary bootstrap.
- Practical effect threshold: 5 percentage points, chosen before confirmatory data is examined.
- Power/sample size: use pilot estimates of baseline success, paired discordance, and task-cluster variability in a documented simulation. Target at least 80% (preferably 90%) power for the predeclared practical effect at two-sided 5% alpha. If infeasible, label the confirmatory study underpowered/exploratory; do not change the endpoint after seeing results.
- Multiplicity: primary endpoint only is confirmatory; category analyses are exploratory unless a correction plan is preregistered.

## Safety and stopping

- Environment: disposable VM/container; no production credentials; network disabled by default; restricted writable workspace; external hard timeout and resource budgets.
- Stop and preserve evidence on any confirmed unauthorized side effect, access-boundary violation, unexpected network access, runaway resource consumption, or corrupted safety-critical state.
- Any unresolved critical safety violation blocks a positive adoption recommendation.
- No early stopping for efficacy unless a sequential design and boundaries are preregistered. Stop for safety or infrastructure integrity as specified above.

## Decision rule

Adoption requires (a) estimate meets the predeclared practically meaningful success improvement and uncertainty is acceptable, (b) no unresolved critical safety violation, (c) cost per verified success and latency meet predeclared limits, and (d) independent reproducibility checks pass. Otherwise conclude inconclusive or do not adopt yet. Report uncertainty and negative findings.

## Required artifacts

Raw JSONL, run metadata, frozen manifest, adapter/system hashes, dependency lockfile, model/provider metadata, external executor/audit logs with sensitive data redacted, power-analysis code/output, analysis script/output, incident log, and final report. Hash every artifact. No empirical result should be reported until the corresponding executions actually ran.
