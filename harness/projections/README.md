# Projection Conventions

Status: draft

Projection specs describe how kernel-owned artifacts map into a vendor-specific
surface. They are design contracts, not generated outputs.

## Rules

- Each projection file targets exactly one vendor surface.
- Projection specs must name the intended output path, but do not create that file by themselves.
- Projection specs may only map behavior that is supported by the current compatibility matrix.
- Unmapped kernel capabilities must be called out explicitly as omitted, deferred, or externalized.
- Vendor files remain leaf adapters and must never become the source of truth.

## File Naming

- Store projection specs in `harness/projections/`.
- Use `<vendor>-<surface>.yaml` naming.
- Prefer one file per emitted artifact, even if multiple files belong to the same vendor.

## Required Sections

- `target`: vendor and output path
- `status`: draft or active
- `inputs`: kernel artifacts that feed the projection
- `realization`: how the target file is materialized and checked
- `mappings`: how kernel concepts map into the target surface
- `omissions`: what stays outside the target surface and why
