---
title: Source adapters
summary: The source adapters of the business-glossary skill, what each reads, the candidate format they return, and how to add a new adapter.
---

# Source adapters

`bg_discover.py` runs one adapter per source. Sources are given as
`kind:path`, listed in `glossary.yaml` under `sources:`, or entered with
`--ask`. The skill must ask the user for this list; never guess a vault path.

| Kind | Reads | Extra behavior |
|---|---|---|
| `obsidian` | vault folder, `.md` notes | frontmatter `aliases`, `type`, `tags`; `[[wikilinks]]` become candidate links; `.obsidian` and `.trash` skipped |
| `folder` | any folder of `.md`, `.txt`, `.rst` | fallback adapter; also reads `Term: definition` lines and glossary tables |
| `csv`, `tsv` | columns `term` or `name`, `definition`; optional `synonyms`, `type`, `name_pl`, `definition_pl` | delimiter detected |
| `xlsx` | first sheet, same columns as CSV | stdlib only, no formulas |
| `confluence` | HTML export folder | page title is the term, first paragraph the definition |
| `docx` | Word documents | `Term: definition` lines plus the first heading as one candidate |

`obsidian` and `folder` treat a note whose path or title matches
`glossary|terms|definitions` as a term list, not as one term.

## Encoding

Text sources (notes, CSV, HTML) must be UTF-8, with or without a byte order
mark; UTF-16 with a byte order mark is also read. Any other file (Latin-1,
UTF-16 without a mark, binary) and any damaged `.docx` or `.xlsx` stops
`bg_discover` and `bg_update --from-sources` with an `ERROR` that names the
file. Nothing is decoded with replacement characters and no file is skipped
silently: convert the file to UTF-8 or remove it from the source, then rerun.

## Candidate ids

The id is the ASCII slug of the name. Polish and other Latin diacritics are
transliterated (`Żółć` -> `zolc`, `Łódź` -> `lodz`). A name with no Latin
letter or digit gets `term-<hash>`. Two different names never share an id:
the later one gets `<slug>-<hash of the name>`, in a fixed order, so ids do
not depend on the order of the sources.

## Candidate format

```yaml
id: customer-journey          # ASCII slug of the name (ł -> l, ż -> z); the future term id
name: Customer Journey
definition: first paragraph or the longest definition found
aliases: [Buyer Journey]
type_hint: Process            # keyword guess, a starting point only
links: [persona]              # wikilinks to other candidates
sources: ['obsidian:projects/Customer Journey.md', 'csv:terms.csv:3']
score: 12                     # mentions across all notes + sources + definition
exists: false                 # already a term in the repo
accept: null                  # set true to select with bg_draft --accepted
```

## Discovery rules

- Duplicates merge by id; the longest definition under 600 characters wins.
- Names under 3 characters, over 6 words, or matching junk (`index`, `todo`,
  dates, `inbox`) are dropped. Candidates without a definition are dropped
  unless `--keep-empty`.
- Ranking is a heuristic. Show the top of the list to the user and let them
  veto.

## Adding an adapter

1. Write `a_<kind>(path, opts)` in `bg_adapters.py` that yields candidate dicts
   with at least `name`, `definition`, `source`, `source_ref`, `aliases`,
   `type_hint`, `links`, `tags`, `bullets`, `text`.
2. Register it in `ADAPTERS`, add a line to `KIND_HELP`, and extend
   `detect_kind` if the source can be recognized from its shape.
3. Add a fixture and a test in `tests/test_glossary_e2e.py` of the source repository.

Sources needing credentials (live Confluence, Jira, Google Drive) are not
adapters: export or download first, then point `confluence` or `folder` at the
copy. Use your own download tool for that step.
