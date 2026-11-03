#!/usr/bin/env python3
"""Minimise related_terms (tree-not-mesh ontology method).

R1 drop a plain link when the pair already has a typed relation.
R2 keep a mutual plain pair on one side only (fewer links keeps it;
   ties go to the lower id).
R3 cap related_terms at --max entries (default 2), keeping the first.
Edits only the related_terms block (plus the version bump).

  bg_relations.py --repo G --dry-run
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bg_core import (REL_KEYS, as_list, bump_text, common_args,
                     default_author, load_config, load_profile,
                     load_terms, need_repo, rel_targets, set_fm_field,
                     unified, write_text)


def main():
  ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
  common_args(ap)
  ap.add_argument('--max', type=int, default=2)
  ap.add_argument('--no-bump', action='store_true',
                  help='skip the version bump (default: bump b)')
  a = ap.parse_args()
  repo = need_repo(a)
  cfg = load_config(repo)
  prof = load_profile(repo, cfg)
  terms = {t['fm']['id']: t for t in load_terms(repo, cfg)
           if t['fm'].get('id')}
  rel = {i: list(as_list(t['fm'].get('related_terms')))
         for i, t in terms.items()}
  typed = set()
  for i, t in terms.items():
    r = rel_targets(t['fm'])
    for k in REL_KEYS:
      for x in r[k]:
        typed.add(frozenset((i, x)))
  new = {i: list(v) for i, v in rel.items()}
  for i in new:
    new[i] = [x for x in new[i] if frozenset((i, x)) not in typed]
  for i in sorted(new):
    for x in list(new[i]):
      if i in new.get(x, []):
        loser = i if (len(new[i]), i) > (len(new.get(x, [])), x) else x
        other = x if loser == i else i
        if other in new[loser]:
          new[loser].remove(other)
  for i in new:
    new[i] = new[i][:a.max]
  changed = 0
  for i, t in terms.items():
    if new[i] == rel[i]:
      continue
    changed += 1
    text = set_fm_field(t['text'], 'related_terms', new[i])
    if not a.no_bump:
      text = bump_text(text, 'b', default_author(cfg), prof)
    print('%s: %s -> %s' % (i, rel[i], new[i]))
    if a.dry_run:
      print(unified(t['text'], text, os.path.basename(t['path'])))
    write_text(t['path'], text, a.dry_run)
  print('%d term(s) %s' % (changed, 'would change' if a.dry_run
                            else 'changed'))


if __name__ == '__main__':
  main()
