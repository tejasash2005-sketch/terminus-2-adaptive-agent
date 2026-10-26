"""Run the offline Terminus-2 Phase 7 repeatability campaign."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from harbor.agents.terminus_2.benchmark_suite import (
    run_repeated_default_campaign,
    write_benchmark_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repetitions",
        type=int,
        default=10,
        help="number of full offline suite repetitions (1-100)",
    )
    parser.add_argument(
        "--output", type=Path, default=Path("artifacts/terminus2-phase7-campaign.json")
    )
    args = parser.parse_args()
    report = asyncio.run(run_repeated_default_campaign(args.repetitions))
    write_benchmark_report(report, args.output)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "repetitions": report["repetitions"],
                "total_case_runs": report["total_case_runs"],
                "all_trials_passed": report["summary"]["all_trials_passed"],
                "mean_trial_pass_rate": report["summary"]["mean_trial_pass_rate"],
            },
            indent=2,
        )
    )
    return 0 if report["summary"]["all_trials_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
