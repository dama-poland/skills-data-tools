# Gap list

Generated from approved `concepts:` entries in system notes and the glossary. Each finding is a prompt for a human decision, not a verdict.

| check | findings |
|---|---|
| meaning conflict | 1 |
| homonym risk | 1 |
| link to a term that is not Approved | 2 |
| system with no approved links | 1 |
| approved term used by no system | 1 |
| link with no source | 0 |

## Meaning conflict (1)

One term id has different meaning text in different systems. Compare text only: a human decides whether the wording or the concept differs. An `Approved` glossary term suggests the wording differs; any other status suggests an open meaning.

| term | glossary status | system | meaning | source |
|---|---|---|---|---|
| device | Under Review | ctms | Free-text note for the delivery aid used in the study | CTMS-ARCH-v1 |
| device | Under Review | edc | Yes or no flag showing whether an injection aid was used | EDC-ARCH-v1 |

## Homonym risk (1)

Different term ids that share a name or a `homonym_of` link and are used in one system or in two systems linked by a shared term.

| terms | reason | same system | linked systems |
|---|---|---|---|
| device-model / device-unit | homonym_of link | device-registry | device-registry - supply-v2 |

## Link to a term that is not Approved (2)

An approved link points to a glossary term whose status is not `Approved`, or to no term.

| term | glossary status | systems |
|---|---|---|
| device | Under Review | ctms, edc |
| dose-event | Draft | edc |

## System with no approved links (1)

The system note has no approved `concepts:` entry, so the map cannot place it.

- supply

## Approved term used by no system (1)

The term is `Approved` in the glossary, but no current system note links to it.

- randomisation-number

## Link with no source (0)

A concept entry has no `source`, so its meaning cannot be traced.

None.
