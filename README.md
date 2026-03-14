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
- `harness/context-index.yaml`: durable context lookup order
- `harness/compatibility-matrix.yaml`: partial vendor compatibility matrix
- `harness/policy.yaml`: policy intent and approval boundaries
- `harness/review.yaml`: review inputs and questions
- `harness/rules.yaml`: proposed structural rules
- `harness/oracles.yaml`: verification pack definitions and current check status
- `harness/projections/`: projection contracts for vendor-specific outputs
- `AGENTS.md`: first emitted leaf adapter based on the OpenAI projection contract
- `CLAUDE.md`: symlinked Anthropic-facing adapter pointing to `AGENTS.md`
- `scripts/check_projection_sync.rb`: realization checks for emitted and symlinked adapters
- `scripts/check_compatibility_matrix.rb`: reviewed-cell coverage summary for the compatibility matrix
- `reports/projection-sync.json`: latest runtime change report for projection inputs and realization checks
- `reports/compatibility-matrix.json`: latest runtime coverage report for the compatibility matrix

## Working Principles

- Kernel artifacts are the workflow source of truth
- Vendor files are projections, not primary authorities
- Static context should stay short and pointer-first
- Verification should be defined explicitly, not implied by prompts
- Missing compatibility entries are unreviewed, not automatically unsupported

## Current Status

- Foundation artifact drafts are in place
- Git history is initialized and pushed
- The first documented leaf adapter is `AGENTS.md`
- `CLAUDE.md` is symlinked to `AGENTS.md` as a shared adapter surface
- Other vendor adapters are not emitted yet

## Next Steps

1. Expand compatibility coverage carefully
2. Run `scripts/check_projection_sync.rb` and inspect `reports/projection-sync.json` for realization results and input changes
3. Run `scripts/check_compatibility_matrix.rb` and inspect `reports/compatibility-matrix.json` for reviewed-cell coverage
