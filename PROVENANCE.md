# Project Provenance

This document records the available source-provenance evidence and its limits. The current workspace has Git metadata, but this document does not claim ancestry that the available Git history cannot establish.

## Project identity

- Project: **Harbor**
- Package/distribution: `harbor`
- Current project version: `0.24.0`

These values appear in the project metadata in `pyproject.toml`; the project name is also reflected in `README.md` and `CITATION.cff`.

## Verified upstream

The upstream repository URL documented in this workspace is:

`https://github.com/harbor-framework/harbor`

The URL appears explicitly in repository metadata and configuration, including `CITATION.cff`, `AGENTS.md`, package URL metadata, and Harbor documentation configuration. This establishes the documented upstream reference, not the exact source origin of this workspace.

## Baseline reference

The prior audit compared this workspace with Harbor `v0.24.0`, using comparison commit:

`b53b8134e1241686dca7759af188f987ecc48e8b`

Comparison against that tag and commit does **not** prove that this workspace originated from that exact revision.

The recorded tree comparison found:

- 238 current-only paths
- 314 common paths with byte differences
- 4 baseline-only paths

The workspace differs materially from the referenced Harbor baseline. It is described here as a **modified Harbor snapshot containing Terminus-2 work**. This description does not claim an exact Git fork, ancestry, or source-archive relationship.

## Git history

When this document was first prepared, the `.git` directory was absent. As of 2026-10-25, Git metadata has been initialized in the active workspace on an unborn `master` branch with 3,657 staged additions, but no commits or remotes. This still establishes no Git ancestry, source history, or authorship. No attempt has been made to reconstruct history.

## Authors and ownership

The available metadata explicitly identifies Alex Shaw as a package author in `pyproject.toml`, and “Harbor Framework Team” appears as the author in `CITATION.cff`. These entries do not establish current repository ownership or maintainer authorization for this particular workspace. That ownership and authorization are **not established by the available evidence**.

## Exact source origin

The exact archive or checkout used to create this workspace has not been identified, and its cryptographic hash is not available. Therefore, exact source provenance cannot currently be claimed. The baseline comparison above is a reference point only; it is not evidence that the workspace originated from commit `b53b8134e1241686dca7759af188f987ecc48e8b`.

## Maintainer acceptance for this release

The maintainer has explicitly accepted this provenance limitation for this release: the exact source archive or checkout cannot be independently identified, its cryptographic hash is unavailable, and Git ancestry is unavailable. This acceptance records a release decision; it does **not** verify provenance, establish a source history, or claim that this workspace originated from the Harbor `v0.24.0` comparison commit above.

## Before publication

- Identify and verify the source archive or checkout used for this workspace.
- Record its cryptographic hash.
- Verify the exact upstream commit or tag, if available.
- Document the origin of modifications made after that source was obtained.
- Git is already initialized; preserve the provenance caveat and do not present the staged snapshot as verified upstream history.
