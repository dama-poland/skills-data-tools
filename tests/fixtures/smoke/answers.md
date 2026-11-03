# Smoke answers (fixture)

Synthetic fixture of a good agent answer, used by `python3 tests/check_smoke.py --self-check`.

## Q1

### Answer

In CTMS, `device` is a free-text note for the delivery aid used in the study. In EDC, `device` is a yes or no flag showing whether an injection aid was used. The two systems use one label for different things.

### Sources

- `sources/ctms.md`, `CTMS-ARCH-v1`, retrieved 2026-10-24.
- `sources/edc.md`, `EDC-ARCH-v1`, retrieved 2026-10-24.

### Confidence

High, because both source notes define the field directly.

### Open doubts

The glossary term `device` is Under Review, so the intended single meaning is not settled.

### Classification

Public.

## Q2

### Answer

`randomisation-number` is Approved in the glossary, and no current system note links to it (gap list, section "Approved term used by no system").

### Sources

- `examples/data/glossary/terms/randomisation-number.md`, source_origin `SUPPLY-ARCH-v2`, retrieved 2026-10-31.
- `generated/architecture/gaps.md`, generated 2026-10-31 from the approved concept links.

### Confidence

High, because the gap list is built by script from the approved links.

### Open doubts

Proposed links are not counted. A proposed link from Supply v2 could change this result once a human approves it.

### Classification

Public.

## Q3

### Answer

Supply v1 had no device field. Supply v2 adds the field `device_model`, described as the model code of the device packed in the kit, and supersedes v1. It adds an approved link to the term `device-model`.

### Sources

- `sources/supply-v1.md`, `SUPPLY-ARCH-v1`, retrieved 2026-09-01.
- `sources/supply-v2.md`, `SUPPLY-ARCH-v2`, retrieved 2026-10-24.

### Confidence

High, because the model diff lists the added field and the added link.

### Open doubts

The sources do not say whether Supply stores only the model code or also a unit serial number.

### Classification

Public.
