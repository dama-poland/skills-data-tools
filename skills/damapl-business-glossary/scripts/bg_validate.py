#!/usr/bin/env python3
"""Validate terms against the repo's rule profile and compute tiers.

  bg_validate.py --repo G                 # text report
  bg_validate.py --repo G --strict        # exit 1 on any finding shown
  bg_validate.py --repo G --strict --level MUST   # exit 1 on MUST only
  bg_validate.py --repo G --format json --profile minimal
  bg_validate.py --repo G --lock          # record ids in .glossary/ids.lock
"""

import argparse
import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bg_core import (PROFILES_DIR, common_args, dump_yaml, load_config,
                     load_profile, load_terms, load_yaml, need_repo,
                     split_term, write_text)
from bg_rules import evaluate, tiers


TODO_RE = re.compile(r'\bTODO\b')


def run(repo, profile_override=None):
  cfg = load_config(repo)
  if profile_override:
    cfg['profile'] = profile_override
  prof = load_profile(repo, cfg)
  terms = load_terms(repo, cfg)
  parse_findings = []
  for t in terms:
    err = t['fm'].get('_parse_error') or (
      None if split_term(t['text'])[0].strip() else 'no frontmatter block')
    if err:
      tid = os.path.basename(t['path'])[:-3]
      t['fm'] = {'id': tid}
      parse_findings.append({
        'term': tid, 'rule': 'YAML-01', 'level': 'MUST',
        'message': 'frontmatter cannot be read: %s' % ' '.join(
          str(err).split())})
  lock_path = os.path.join(repo, '.glossary', 'ids.lock')
  lock = []
  if os.path.isfile(lock_path):
    lock = open(lock_path, encoding='utf-8').read().split()
  viol = evaluate(terms, prof, cfg, {'ids_lock': lock})
  viol += parse_findings
  for t in terms:
    if TODO_RE.search(t['text']):
      viol.append({'term': t['fm'].get('id'), 'rule': 'DRAFT-TODO',
                   'level': 'SHOULD',
                   'message': 'placeholder TODO still in the term; the '
                   'term stays below Silver'})
  return cfg, prof, terms, viol, tiers(terms, viol, prof)


def main():
  ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
  common_args(ap)
  ap.add_argument('--profile', help='override profile (name or path)')
  ap.add_argument('--strict', action='store_true',
                  help='exit 1 on any finding shown (MUST or SHOULD); '
                  'combine with --level MUST to fail on MUST only')
  ap.add_argument('--format', choices=('text', 'json'), default='text')
  ap.add_argument('--lock', action='store_true')
  ap.add_argument('--level', choices=('MUST', 'SHOULD'), default='SHOULD',
                  help='lowest level to show (default SHOULD = all)')
  a = ap.parse_args()
  repo = need_repo(a)
  override = None
  if a.profile:
    override = a.profile if os.path.isfile(a.profile) else os.path.join(
      PROFILES_DIR, a.profile.replace('.yaml', '') + '.yaml')
  cfg, prof, terms, viol, tr = run(repo, override)
  if a.level == 'MUST':
    viol = [v for v in viol if v['level'] == 'MUST']
  must = [v for v in viol if v['level'] == 'MUST']
  dist = collections.Counter(tr.values())
  if a.format == 'json':
    print(json.dumps({'terms': len(terms), 'violations': viol,
                      'tiers': tr, 'tier_counts': dist}, indent=1))
  else:
    for v in sorted(viol, key=lambda v: (v['term'] or '', v['rule'])):
      print('%-6s %-9s %-26s %s' % (
        v['level'], v['rule'], v['term'], v['message']))
    print('\n%d terms, %d MUST, %d SHOULD; profile %s' % (
      len(terms), len(must), len(viol) - len(must), prof.get('name')))
    print('tiers: ' + ', '.join('%s=%d' % kv for kv in sorted(dist.items())))
  if a.lock and not a.dry_run:
    lp = os.path.join(repo, '.glossary', 'ids.lock')
    have = set(open(lp).read().split()) if os.path.isfile(lp) else set()
    ids = have | {t['fm'].get('id') for t in terms if t['fm'].get('id')}
    write_text(lp, '\n'.join(sorted(ids)) + '\n')
    print('ids.lock: %d ids' % len(ids))
  if a.strict and viol:
    sys.exit(1)


if __name__ == '__main__':
  main()
