# ADR 0001: Use manifest as the committed specialization record

Status: accepted

## Context

This repository is a reusable development template rather than a single finished
project. The template needs one committed place to capture project intake,
research, stack selection, and the downstream harness specialization choices
that follow from those decisions.

## Decision

`harness/manifest.yaml` is the committed home for template specialization.

The `specialization_record` section stores project intake, research, stack
selection, and harness-application status. Other documents should point to the
manifest instead of duplicating those decisions.

## Alternatives Considered

- Separate intake and stack-selection files
- Keeping specialization notes only in README or DESIGN prose

## Consequences

The manifest becomes the canonical place to read and update specialization
state. Other workflow artifacts stay lighter and more pointer-first, but the
template also needs example and checker support so the manifest does not become
ambiguous or overly manual.

## Related Artifacts

- `harness/manifest.yaml`
- `harness/context-index.yaml`
- `harness/policy.yaml`
- `harness/examples/manifest-specialization.example.yaml`

## Supersedes

None
