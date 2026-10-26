# Terminus-2 Phase 6 offline regression benchmark

Run from a fully provisioned Harbor checkout:

```python
import asyncio
from harbor.agents.terminus_2.benchmark_suite import (
    run_default_regression_suite,
    write_benchmark_report,
)

report = asyncio.run(run_default_regression_suite())
write_benchmark_report(report, "benchmarks/terminus2-phase6/results.json")
print(report["summary"])
```

The bundled suite exercises the actual autonomous control loop with deterministic
fake model responses and an in-memory executor. It checks behavior, not model
quality, tool reliability, or real-world task completion. `results.json` is a
machine-generated example run, not a performance claim. Rerun in your own
provisioned environment to regenerate local timing data. For publishable empirical
comparisons, add a fixed real-task corpus, independent verifiers, matched baseline
runs, repeated trials, environment/model/budget metadata, and raw results.
