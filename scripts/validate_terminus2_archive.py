"""Validate a Harbor portfolio ZIP before publishing it."""

from __future__ import annotations

import argparse
import json
import stat
import zipfile
from pathlib import PurePosixPath

REQUIRED = (
    "LICENSE",
    "pyproject.toml",
    "README.md",
    "docs/terminus2-adaptive-intelligence.md",
    "src/harbor/agents/terminus_2/task_planner.py",
    "src/harbor/agents/terminus_2/orchestration.py",
    "src/harbor/agents/terminus_2/autonomous.py",
    "src/harbor/agents/terminus_2/benchmark_suite.py",
    "tests/unit/agents/terminus_2/test_task_planner.py",
    "tests/unit/agents/terminus_2/test_orchestration.py",
    "tests/unit/agents/terminus_2/test_autonomous.py",
    "tests/unit/agents/terminus_2/test_benchmark_suite.py",
    "benchmarks/terminus2-phase7/README.md",
    "benchmarks/terminus2-phase7/results.json",
    "scripts/run_terminus2_benchmark_campaign.py",
    "scripts/validate_terminus2_archive.py",
    "scripts/terminus2_phase8_eval.py",
    "tests/unit/agents/terminus_2/test_phase8_eval.py",
    "benchmarks/terminus2-phase8/manifest.json",
    "benchmarks/terminus2-phase8/README.md",
    "benchmarks/terminus2-phase8/adapter-contract.md",
    "benchmarks/terminus2-phase8/preregistration.md",
    "benchmarks/terminus2-phase8/adapters/baseline_adapter.py",
    "benchmarks/terminus2-phase8/adapters/adaptive_adapter.py",
    "benchmarks/terminus2-phase8/adapters/supervised_process_adapter.py",
    "benchmarks/terminus2-phase8/adapters/harbor_trial_supervisor.py",
    "benchmarks/terminus2-phase8/adapters/safety-attestation.example.json",
)
FORBIDDEN_PARTS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".tox",
}


def validate(path: str) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            duplicates = sorted({name for name in names if names.count(name) > 1})
            if duplicates:
                errors.append(f"duplicate ZIP entries: {duplicates[:10]}")
            name_set = set(names)
            missing = [name for name in REQUIRED if name not in name_set]
            if missing:
                errors.append(f"missing required files: {missing}")
            unsafe = []
            forbidden = []
            symlinks = []
            for info in infos:
                name = info.filename
                path_obj = PurePosixPath(name)
                if "\\" in name or path_obj.is_absolute() or ".." in path_obj.parts:
                    unsafe.append(name)
                if any(
                    part in FORBIDDEN_PARTS for part in path_obj.parts
                ) or name.endswith(".pyc"):
                    forbidden.append(name)
                mode = info.external_attr >> 16
                if stat.S_ISLNK(mode):
                    symlinks.append(name)
            if unsafe:
                errors.append(f"unsafe archive paths: {unsafe[:10]}")
            if forbidden:
                errors.append(
                    f"development caches or VCS files included: {forbidden[:10]}"
                )
            if symlinks:
                warnings.append(
                    f"archive contains symlinks; verify targets manually: {symlinks[:10]}"
                )
            corrupt = archive.testzip()
            if corrupt:
                errors.append(f"CRC failure in archive member: {corrupt}")
            return {
                "archive": path,
                "valid": not errors,
                "entry_count": len(infos),
                "total_uncompressed_bytes": sum(info.file_size for info in infos),
                "required_file_count": len(REQUIRED) - len(missing),
                "required_file_total": len(REQUIRED),
                "errors": errors,
                "warnings": warnings,
            }
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        return {
            "archive": path,
            "valid": False,
            "entry_count": 0,
            "errors": [f"{type(exc).__name__}: {exc}"],
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", help="path to the ZIP archive to validate")
    args = parser.parse_args()
    result = validate(args.archive)
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
