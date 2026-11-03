#!/usr/bin/env python3
"""Diff-based update of existing terms. Never rewrites a whole term:
only the named frontmatter fields or body sections change, ids never
change, and the version is bumped (b for a value change, c for editorial).

Modes
  --patch FILE        apply a patch (YAML list of ops, see below)
  --from-sources      compare sources with terms; write proposals only
  --bump-only IDS     bump version of the listed terms (--level a|b|c)

Patch op:
  - id: candidate            # required, must exist
    set: {type: Role}        # replace frontmatter fields
    add: {alternative_names: [Job Seeker]}
    remove: {related_terms: [recruiter]}
    definition: "One or two sentences."
    sections: {What it is: "- bullet"}
    level: b                 # optional; default b, use c for typo fixes

Guards (set, add and remove alike): `id`, `created`, `created_by` are
immutable; `version`, `version_date`, `changed_by` belong to the bump;
`approved_by`, `approved_on`, `approved_version` are written by a human
only and always refused. `status` changes only through `set`, and only to
Draft unless --allow-status is given together with the human-only signal
DAMAPL_HUMAN_APPROVAL=1. An agent never sets it. A profile whose
`agent_status` is not Draft is refused before any change.
`confidentiality` changes only through `set` and never goes down
(public < internal < restricted); `source_refs` entries are never removed.
--from-sources proposals raise confidentiality and add the source ref when
a differing source is classified higher than the term.

  bg_update.py --repo G --patch p.yaml --dry-run
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bg_adapters import SourceError, run_adapter
from bg_core import (AGENT_STATUS, APPROVAL_FIELDS, CLASSIFICATIONS,
                     as_list, bump_text, common_args,
                     default_author, dump_yaml, highest_classification,
                     load_config, load_profile, load_terms, load_yaml,
                     name_key, need_repo, normalize_classification,
                     read_term, set_definition, set_fm_field, set_section,
                     source_ref_of, unified, write_text)

IMMUTABLE = ('id', 'created_by', 'created')
BUMP_FIELDS = ('version', 'version_date', 'changed_by')
HUMAN_APPROVAL_ENV = 'DAMAPL_HUMAN_APPROVAL'


def check_classification(kind, k, v, fm):
  """confidentiality never goes down; source_refs entries never go away."""
  if k == 'confidentiality':
    if kind != 'set':
      raise ValueError('confidentiality is a single value; `%s` on it is '
                       'refused (use set)' % kind)
    if str(v).strip().lower() not in CLASSIFICATIONS:
      raise ValueError('confidentiality must be one of %s'
                       % ', '.join(CLASSIFICATIONS))
    cur = normalize_classification(fm.get('confidentiality'))
    if CLASSIFICATIONS.index(normalize_classification(v)) < \
        CLASSIFICATIONS.index(cur):
      raise ValueError('confidentiality %s -> %s is a downgrade; only a '
                       'dated human decision can declassify' % (cur, v))
  if k == 'source_refs':
    if kind == 'remove':
      raise ValueError('source_refs entries are never removed')
    if kind == 'set' and set(map(str, as_list(fm.get('source_refs')))) - \
        set(map(str, as_list(v))):
      raise ValueError('source_refs entries are never removed (use add)')


def check_guards(op, fm, allow_status):
  """Refuse protected fields in every field op (set, add, remove)."""
  for kind in ('set', 'add', 'remove'):
    for k, v in (op.get(kind) or {}).items():
      check_classification(kind, k, v, fm)
      if k in IMMUTABLE:
        raise ValueError('`%s` is immutable (ids never change)' % k)
      if k in BUMP_FIELDS:
        raise ValueError('`%s` is managed by the bump' % k)
      if k in APPROVAL_FIELDS:
        raise ValueError('`%s` records a human approval; agents never '
                         'write it' % k)
      if k == 'status' and kind != 'set':
        raise ValueError('status is a single value; `%s` on status is '
                         'refused (use set)' % kind)
      if k == 'status' and not allow_status and v != AGENT_STATUS:
        raise ValueError('agents only write status %s' % AGENT_STATUS)


def apply_op(t, op, prof, author, allow_status):
  text = t['text']
  fm = t['fm']
  check_guards(op, fm, allow_status)
  for k, v in (op.get('set') or {}).items():
    if fm.get(k) != v:
      text = set_fm_field(text, k, v)
  for k, vals in (op.get('add') or {}).items():
    cur = as_list(fm.get(k))
    new = cur + [v for v in as_list(vals) if v not in cur]
    if new != cur:
      text = set_fm_field(text, k, new)
  for k, vals in (op.get('remove') or {}).items():
    cur = as_list(fm.get(k))
    new = [v for v in cur if v not in as_list(vals)]
    if new != cur:
      text = set_fm_field(text, k, new)
  if op.get('definition') and op['definition'].strip() != t['definition']:
    text = set_definition(text, op['definition'])
  for title, content in (op.get('sections') or {}).items():
    from bg_core import section_key
    if t['sections'].get(section_key(title)) != content.strip():
      text = set_section(text, title, content)
  if text == t['text']:
    return text
  return bump_text(text, op.get('level', 'b'), author, prof)


def propose(repo, cfg, terms):
  """Compare sources with existing terms; return patch ops, apply none."""
  ops, seen = [], {}
  for t in terms:
    seen.setdefault(name_key(t['fm'].get('name') or ''), t)
  for s in cfg.get('sources') or []:
    for c in run_adapter(s['kind'], s['path']):
      t = seen.get(name_key(c['name']))
      if not t or not c['definition'] or len(c['definition']) > 600:
        continue
      if c['definition'].strip() != t['definition'].strip():
        op = {'id': t['fm']['id'], 'definition': c['definition'],
              'reason': 'source %s:%s differs' % (
                c['source'], c['source_ref'])}
        cur = normalize_classification(t['fm'].get('confidentiality'))
        conf = highest_classification([cur, c.get('confidentiality')])
        if conf != cur:
          op['set'] = {'confidentiality': conf}
        ref = source_ref_of(c)
        if ref not in map(str, as_list(t['fm'].get('source_refs'))):
          op['add'] = {'source_refs': [ref]}
        ops.append(op)
  return ops


def main():
  ap = argparse.ArgumentParser(
    description=__doc__.split('\n')[0],
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog='\n'.join(__doc__.split('\n')[2:]))
  common_args(ap)
  g = ap.add_mutually_exclusive_group(required=True)
  g.add_argument('--patch')
  g.add_argument('--from-sources', action='store_true')
  g.add_argument('--bump-only', help='comma list of term ids')
  ap.add_argument('--level', choices=('a', 'b', 'c'), default='b')
  ap.add_argument('--author', default=None)
  ap.add_argument('--allow-status', action='store_true',
                  help='allow a status other than Draft; needs the '
                  'human-only signal %s=1' % HUMAN_APPROVAL_ENV)
  a = ap.parse_args()
  if a.allow_status and os.environ.get(HUMAN_APPROVAL_ENV) != '1':
    sys.exit('ERROR --allow-status needs %s=1, set by a human; agents '
             'never set it' % HUMAN_APPROVAL_ENV)
  repo = need_repo(a)
  cfg = load_config(repo)
  prof = load_profile(repo, cfg)
  if prof.get('agent_status', AGENT_STATUS) != AGENT_STATUS:
    sys.exit('ERROR profile agent_status is %r; agents only write status '
             '%s, so a profile cannot raise it' % (prof['agent_status'],
                                                   AGENT_STATUS))
  terms = load_terms(repo, cfg)
  by_id = {t['fm'].get('id'): t for t in terms}
  author = a.author or default_author(cfg)

  if a.from_sources:
    try:
      ops = propose(repo, cfg, terms)
    except SourceError as exc:
      sys.exit('ERROR %s' % exc)
    out = os.path.join(repo, '.glossary', 'proposals.yaml')
    write_text(out, dump_yaml(ops), a.dry_run)
    print('%d proposal(s) -> %s (review, then --patch it)' % (
      len(ops), out))
    return
  if a.bump_only:
    ops = [{'id': i, 'level': a.level} for i in a.bump_only.split(',')]
  else:
    ops = load_yaml(a.patch)
    if isinstance(ops, dict):
      ops = [ops] if ops else []
  errors = changed = 0
  for op in ops:
    t = by_id.get(op.get('id'))
    if not t:
      print('ERROR unknown id %r (ids are never created here)' % op.get('id'))
      errors += 1
      continue
    try:
      if a.bump_only:
        new = bump_text(t['text'], a.level, author, prof)
      else:
        new = apply_op(t, op, prof, author, a.allow_status)
    except ValueError as exc:
      print('ERROR %s: %s' % (op['id'], exc))
      errors += 1
      continue
    if new == t['text']:
      print('unchanged %s' % op['id'])
      continue
    changed += 1
    print(unified(t['text'], new, os.path.basename(t['path'])))
    write_text(t['path'], new, a.dry_run)
  print('%d term(s) %s, %d error(s)' % (
    changed, 'would change' if a.dry_run else 'changed', errors))
  if errors:
    sys.exit(1)


if __name__ == '__main__':
  main()
