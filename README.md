# Development Harness Template

This repository is a reusable template for starting new software projects.

It includes a vendor-agnostic `Harness Kernel` for coding-agent workflows, but
the repository itself is not only a kernel sandbox. The intent is to understand
the target project first, research the domain and constraints, choose an
appropriate stack, and then adapt the harness to that concrete project.

The current goal is not to ship a finished framework. It is to establish a
careful template-owned source of truth for workflow instructions, policy,
verification, projection rules, and project-intake guidance.

## Current Contents

- `DESIGN.md`: design rationale, scope boundaries, and rollout order
- `harness/capabilities.schema.json`: canonical capability vocabulary schema
- `harness/capability-profile.yaml`: this repository's initial capability profile
- `harness/manifest.yaml`: committed specialization record for project intake, stack selection, repository scope, and rollout
- `harness/context-index.yaml`: durable context lookup order
- `harness/compatibility-matrix.yaml`: partial vendor compatibility matrix
- `harness/policy.yaml`: policy intent and approval boundaries
- `harness/review.yaml`: review inputs and questions
- `harness/rules.yaml`: proposed structural rules
- `harness/oracles.yaml`: verification pack definitions and current check status
- `docs/adr/`: ADR templates and committed decision records
- `harness/projections/`: projection contracts for vendor-specific outputs
- `harness/examples/manifest-specialization.example.yaml`: filled-in reference example for `specialization_record`
- `AGENTS.md`: first emitted leaf adapter based on the OpenAI projection contract
- `CLAUDE.md`: symlinked Anthropic-facing adapter pointing to `AGENTS.md`
- `scripts/check_adr.py`: ADR structure and presence validation
- `scripts/check_rules.py`: rules metadata validation
- `scripts/check_oracles_ready.py`: project-specific quality command readiness validation
- `scripts/check_projection_sync.py`: realization checks for emitted and symlinked adapters
- `scripts/check_compatibility_matrix.py`: reviewed-cell coverage summary for the compatibility matrix
- `reports/adr-check.json`: latest runtime report for ADR structure validation
- `reports/rules-check.json`: latest runtime report for rules metadata validation
- `reports/oracles-readiness.json`: latest runtime report for core quality command readiness
- `reports/projection-sync.json`: latest runtime change report for projection inputs and realization checks
- `reports/compatibility-matrix.json`: latest runtime report for reviewed-cell coverage and unreviewed capability lists

## Working Principles

- Start with the target project's goals, domain, constraints, and expected workflows
- Let stack selection follow project understanding rather than precommitting too early
- Introduce project-specific runtime elements only after discussion and investigation of the target project or existing codebase
- Kernel artifacts are the source of truth for the template's workflow scaffolding
- Vendor files are projections, not primary authorities
- Static context should stay short and pointer-first
- Verification should be defined explicitly, not implied by prompts
- Missing compatibility entries are unreviewed, not automatically unsupported

## Template Workflow

Use `harness/manifest.yaml` as the committed record for project intake, research,
stack selection, and harness application. The template workflow order is defined
there and should be specialized before vendor-facing adapters are expanded.

See `harness/examples/manifest-specialization.example.yaml` for a filled-in
reference example, then record real project decisions in `harness/manifest.yaml`.

## Current Status

- Foundation artifact drafts are in place
- Git history is initialized and pushed
- The first documented leaf adapter is `AGENTS.md`
- `CLAUDE.md` is symlinked to `AGENTS.md` as a shared adapter surface
- Project intake and stack-selection decisions now live in `harness/manifest.yaml`
- ADR structure, rules metadata, and oracle-readiness checkers are now available
- Other vendor adapters are not emitted yet

## Next Steps

1. Use `harness/examples/manifest-specialization.example.yaml` as a reference, then fill in `harness/manifest.yaml`
2. Expand compatibility coverage carefully
3. Run the runtime report scripts when ADR, rules, or oracle-readiness state changes
