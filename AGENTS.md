# AGENTS.md

## Why This Repo Exists

This repository is building a vendor-agnostic `Harness Kernel` for coding-agent
workflows. The goal is to define kernel-owned sources of truth for instructions,
policy, verification, and projection rules before growing vendor-specific
adapters.

## What Is Authoritative

This `AGENTS.md` is a leaf adapter for OpenAI-style repo instructions. It is not
the primary source of truth.

Start with these files:

- `README.md` for repository scope and current status
- `DESIGN.md` for rationale, rollout order, and boundaries
- `harness/context-index.yaml` for the full durable context lookup order

If a workflow rule changes, update the kernel-owned artifact first and then keep
this file aligned with it.

## How To Work In This Repo

- Keep repo instructions pointer-first; do not turn this file into a long handbook.
- Treat vendor-facing files as projections, not primary authorities.
- Treat missing compatibility entries as unreviewed, not automatically unsupported.
- Do not claim runtime enforcement or adapter support that is not documented in the kernel.
- Add runtime helpers only after a concrete gap is documented.

## Current State

- The repository is still in a draft foundation phase.
- Kernel artifacts exist under `harness/`.
- `AGENTS.md` is currently the first documented leaf adapter.
- No build, test, or runtime wrapper commands are defined yet; verification intent lives in `harness/oracles.yaml`.
