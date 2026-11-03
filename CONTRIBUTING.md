---
title: "Contributing"
summary: "Contribution rules for changes to the DAMA Poland skills collection (DAMA Day 2026 trial) and synthetic examples."
updated: "2026-10-24"
review_by: "2027-01-24"
owner: "DAMA Poland maintainers"
status: "candidate"
confidentiality: "public"
---

# Contributing

1. Open an issue before a large change.
2. Keep one topic per pull request and use plain, specific prose.
3. Never add client data, confidential company names, personal data or credentials.
4. Mark every example as synthetic or public and give it canonical metadata.
5. Preserve source provenance, classification and dated human decisions.
6. Contributions are made under the Apache License 2.0 (section 5 of the licence). No separate contributor agreement is required.

## Review and merge

- One approval from either author and green CI are enough to merge.
- Follow the [Code of Conduct](CODE_OF_CONDUCT.md) in all project spaces.
- Edit shared files in `shared/` only, then run `python3 scripts/sync_shared.py`. CI fails if a copy in a skill differs.
- Run `scripts/lint.sh` and `python3 -m unittest discover -s tests -p 'test_*.py'` before you open a pull request.

## Support

Support is best effort. There is no guaranteed response time.
