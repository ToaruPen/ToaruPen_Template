# Harness Kernel Template

This repository is building a vendor-agnostic `Harness Kernel` for coding-agent
workflows.

The current goal is not to ship a finished framework. It is to establish a
careful source of truth for instructions, policy, verification, and projection
rules before generating vendor-specific files.

## Current Contents

- `DESIGN.md`: design rationale, scope boundaries, and rollout order
- `harness/capabilities.schema.json`: canonical capability vocabulary schema
- `harness/capability-profile.yaml`: this repository's initial capability profile
- `harness/manifest.yaml`: repository scope and rollout manifest
- `harness/compatibility-matrix.yaml`: partial vendor compatibility matrix
- `harness/policy.yaml`: policy intent and approval boundaries
- `harness/rules.yaml`: proposed structural rules
- `harness/oracles.yaml`: planned verification packs
- `harness/projections/`: projection contracts for vendor-specific outputs

## Working Principles

- Kernel artifacts are the workflow source of truth
- Vendor files are projections, not primary authorities
- Static context should stay short and pointer-first
- Verification should be defined explicitly, not implied by prompts
- Missing compatibility entries are unreviewed, not automatically unsupported

## Current Status

- Foundation artifact drafts are in place
- Git history is initialized and pushed
- The first documented projection target is `AGENTS.md`
- No generated vendor adapters exist yet

## Next Steps

1. Expand compatibility coverage carefully
2. Decide how projection specs become generated files
3. Add runtime helpers only after concrete gaps are proven
