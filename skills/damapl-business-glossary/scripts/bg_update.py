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

  bg_update.py --repo G --patch p.yaml --dry-run
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bg_adapters import run_adapter
from bg_core import (as_list, bump_text, common_args, default_author,
                     dump_yaml, load_config, load_profile, load_terms,
                     load_yaml, need_repo, read_term, set_definition,
                     set_fm_field, set_section, slugify, unified,
                     write_text)

IMMUTABLE = ('id', 'created_by', 'created')
BUMP_FIELDS = ('version', 'version_date', 'changed_by')


def apply_op(t, op, prof, author, allow_status):
  text = t['text']
  for k in (op.get('set') or {}):
    if k in IMMUTABLE:
      raise ValueError('`%s` is immutable (ids never change)' % k)
    if k in BUMP_FIELDS:
      raise ValueError('`%s` is managed by the bump' % k)
    if k == 'status' and not allow_status and \
        op['set'][k] != prof.get('agent_status', 'Draft'):
      raise ValueError('agents only write status %s (use --allow-status)'
                       % prof.get('agent_status', 'Draft'))
  fm = t['fm']
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
  ops, seen = [], {t['fm'].get('id'): t for t in terms}
  for s in cfg.get('sources') or []:
    for c in run_adapter(s['kind'], s['path']):
      t = seen.get(slugify(c['name']))
      if not t or not c['definition'] or len(c['definition']) > 600:
        continue
      if c['definition'].strip() != t['definition'].strip():
        ops.append({'id': t['fm']['id'], 'definition': c['definition'],
                    'reason': 'source %s:%s differs' % (
                      c['source'], c['source_ref'])})
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
  ap.add_argument('--allow-status', action='store_true')
  a = ap.parse_args()
  repo = need_repo(a)
  cfg = load_config(repo)
  prof = load_profile(repo, cfg)
  terms = load_terms(repo, cfg)
  by_id = {t['fm'].get('id'): t for t in terms}
  author = a.author or default_author(cfg)

  if a.from_sources:
    ops = propose(repo, cfg, terms)
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
