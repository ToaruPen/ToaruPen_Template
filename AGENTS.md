# AGENTS.md

## Why This Repo Exists

This repository is a reusable development template.

It includes a vendor-agnostic `Harness Kernel` for coding-agent workflows, but
the template is meant to be applied after understanding the target project,
researching its constraints, and selecting an appropriate stack.

## What Is Authoritative

This file is a shared leaf adapter for repo-level instructions. Kernel-owned
workflow artifacts remain the primary source of truth.

Start with these files:

- `README.md` for repository scope and current status
- `harness/manifest.yaml` for the committed project intake record and stack-selection decision
- `harness/examples/manifest-specialization.example.yaml` for a filled-in reference example
- `docs/adr/` for decision records and templates
- `DESIGN.md` for rationale, rollout order, and boundaries
- `harness/context-index.yaml` for the full durable context lookup order

If a workflow rule changes, update the kernel-owned artifact first and then keep
this file aligned with it.

## How To Work In This Repo

- Treat this repository as a template to be specialized for a future project, not as a finished product by itself.
- Record the target project's intake and stack selection in `harness/manifest.yaml` before overcommitting to generated adapters or runtime helpers.
- When specializing against an existing project, inspect the existing codebase before adding runtime helpers, hooks, traces, or CI wiring.
- Keep repo instructions pointer-first; do not turn this file into a long handbook.
- Treat vendor-facing files as projections, not primary authorities.
- Treat missing compatibility entries as unreviewed, not automatically unsupported.
- Do not claim runtime enforcement or adapter support that is not documented in the kernel.
- Add runtime helpers only after a concrete gap is documented.

## Current State

- The repository is still in a draft foundation phase.
- Kernel artifacts exist under `harness/` as template-owned workflow sources.
- `harness/manifest.yaml` is the committed home for project intake and stack-selection records.
- `docs/adr/` holds the current ADR template and committed decision records.
- `AGENTS.md` is currently the first documented leaf adapter.
- Verification wrappers are defined in `Makefile` (`make check` runs the
  full lint/format/typecheck/test/dead/docs sweep). The canonical oracle
  intent lives in `harness/oracles.yaml`.
- Python toolchain is managed via `pyproject.toml` and `uv`. Validators
  under `scripts/` are invoked as `uv run python scripts/check_*.py`.
