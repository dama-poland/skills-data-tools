---
title: "Supply (synthetic) index"
summary: "Compatibility index for the Supply system, split into supply-v1.md and supply-v2.md to exercise the freshness scenario."
type: "source"
source_id: "SUPPLY-INDEX"
version: "n/a"
retrieved: "2026-10-24"
updated: "2026-10-24"
review_by: "2027-01-24"
owner: "Synthetic demo maintainers"
status: "approved"
confidentiality: "public"
hosted_model_allowed: true
---

# Supply (synthetic)

The Supply system is split into two versioned sources for the freshness demo:

- `supply-v1.md`: `SUPPLY-ARCH-v1`, no device field.
- `supply-v2.md`: `SUPPLY-ARCH-v2`, adds `device_model`, supersedes `SUPPLY-ARCH-v1`.

Use `supply-v2.md` as the current source. Load both versions only for the freshness
scenario described in `examples/README.md`.
