#!/usr/bin/env python3
"""Extract candidate terms from knowledge-base sources.

Sources come from --source kind:path (repeatable), from `sources:` in
glossary.yaml, or interactively with --ask. Output is a ranked candidate
list in .glossary/candidates.yaml; nothing in terms/ is touched.
Each candidate carries the highest confidentiality of all its sources
(a source without one counts as internal).

  bg_discover.py --repo G --source obsidian:~/vault --source csv:t.csv
  bg_discover.py --repo G --ask
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bg_adapters import ADAPTERS, KIND_HELP, detect_kind, run_adapter
from bg_core import (dump_yaml, load_config, load_terms, need_repo, slugify,
                     common_args, write_text, as_list, name_hash, name_key,
                     highest_classification, source_ref_of, term_name_keys)

JUNK = re.compile(r'(?i)^(index|home|readme|todo|untitled|inbox|template|'
                  r'daily|\d{4}-\d{2}-\d{2}|new note)\b')


def ask_sources():
  if not sys.stdin.isatty():
    sys.exit('no sources given and stdin is not a terminal; pass --source '
             'kind:path (kinds: %s)' % ', '.join(sorted(ADAPTERS)))
  print('Which sources should I read? One per line as kind:path, or just a '
        'path to auto-detect.\nKinds:')
  for k, v in KIND_HELP.items():
    print('  %-11s %s' % (k, v))
  print('Empty line to finish.')
  out = []
  while True:
    ln = input('source> ').strip()
    if not ln:
      return out
    out.append(ln)


def parse_source(s):
  head, _, rest = s.partition(':')
  if rest and head in ADAPTERS:
    return head, rest
  return detect_kind(s), s


def assign_ids(merged, known_names):
  """Give every name a unique id. A name keeps the plain slug unless
  another name already owns it; then it gets `<slug>-<name hash>`. A name
  that an existing term carries keeps that term's id first (plain or
  suffixed)."""
  taken = {}
  for key, m in merged.items():
    base = slugify(m['name'])
    for sid in (base, '%s-%s' % (base, name_hash(m['name']))):
      if key in known_names.get(sid, ()):
        m['id'] = taken[sid] = sid
        break
  for key in sorted(merged):
    m = merged[key]
    if m['id']:
      continue
    sid = base = slugify(m['name'])
    if sid in taken or sid in known_names:
      sid = '%s-%s' % (base, name_hash(m['name']))
    while sid in taken or sid in known_names:
      sid += '-x'
    m['id'] = taken[sid] = sid


def mentions(name, corpus_lower):
  pat = re.compile(r'\b' + re.escape(name.lower()) + r'\b')
  return sum(len(pat.findall(t)) for t in corpus_lower)


def main():
  ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
  common_args(ap)
  ap.add_argument('--source', action='append', default=[],
                  help='kind:path (repeatable)')
  ap.add_argument('--ask', action='store_true',
                  help='prompt for the list of sources')
  ap.add_argument('--keep-empty', action='store_true',
                  help='keep candidates that have no definition')
  ap.add_argument('--limit', type=int, default=0, help='keep top N')
  a = ap.parse_args()
  repo = need_repo(a)
  cfg = load_config(repo)

  specs = list(a.source)
  if a.ask:
    specs += ask_sources()
  if not specs:
    specs = ['%s:%s' % (s['kind'], s['path'])
             for s in (cfg.get('sources') or [])]
  if not specs:
    specs = ask_sources()
  parsed = [parse_source(s) for s in specs]

  raw = []
  for kind, path in parsed:
    if not os.path.exists(os.path.expanduser(path)):
      print('skip (not found): %s' % path, file=sys.stderr)
      continue
    got = run_adapter(kind, path)
    print('%-10s %-40s %d raw candidates' % (kind, path[-40:], len(got)))
    raw += got

  terms = load_terms(repo, cfg)
  existing = {t['fm'].get('id') for t in terms}
  known_names = {t['fm'].get('id'): term_name_keys(t['fm']) for t in terms}
  # One entry per name; ids are assigned afterwards so that they do not
  # depend on the order of the sources.
  merged = {}
  for c in raw:
    name = c['name'].strip()
    if (len(name) < 3 or len(name.split()) > 6 or JUNK.match(name)):
      continue
    key = name_key(name)
    m = merged.setdefault(key, {
      'id': None, 'name': name, 'definition': '', 'aliases': [],
      'type_hint': c['type_hint'], 'links': [], 'tags': [],
      'bullets': [], 'sources': [], 'name_pl': '', 'definition_pl': '',
      'confidentiality': None})
    if len(c['definition']) > len(m['definition']) and len(
        c['definition']) < 600:
      m['definition'] = c['definition']
      m['type_hint'] = c['type_hint']
    for k in ('aliases', 'links', 'tags', 'bullets'):
      m[k] = sorted(set(m[k]) | set(as_list(c.get(k)))) if k != 'bullets' \
        else (m[k] or as_list(c.get(k)))
    for k in ('name_pl', 'definition_pl'):
      m[k] = m[k] or c.get(k, '')
    seen = [m['confidentiality']] if m['confidentiality'] else []
    m['confidentiality'] = highest_classification(
      seen + [c.get('confidentiality')])
    ref = source_ref_of(c)
    if ref not in m['sources']:
      m['sources'].append(ref)
  assign_ids(merged, known_names)
  cands = [m for m in merged.values()
           if a.keep_empty or m['definition']]

  corpus = [c.get('text', '').lower() for c in raw]
  corpus += [(c.get('definition') or '').lower() for c in raw]
  for m in cands:
    n = mentions(m['name'], corpus)
    m['score'] = n + 2 * len(m['sources']) + (3 if m['definition'] else 0)
    m['exists'] = m['id'] in existing
    m['accept'] = None
  cands.sort(key=lambda m: (-m['score'], m['id']))
  if a.limit:
    cands = cands[:a.limit]
  known = {m['id'] for m in cands}
  by_name = {name_key(m['name']): m['id'] for m in cands}
  for m in cands:
    ids = (by_name.get(name_key(x)) or (
      slugify(x) if slugify(x) in known else None) for x in m['links'])
    m['links'] = sorted({i for i in ids if i})

  out = os.path.join(repo, '.glossary', 'candidates.yaml')
  print('%d candidates (%d already terms) -> %s%s' % (
    len(cands), sum(m['exists'] for m in cands), out,
    ' [dry-run]' if a.dry_run else ''))
  for m in cands[:10]:
    print('  %4d  %-28s %s' % (m['score'], m['id'], m['definition'][:50]))
  write_text(out, dump_yaml({'candidates': cands}), a.dry_run)
  if not a.dry_run and parsed:
    cfg_path = os.path.join(repo, 'glossary.yaml')
    import yaml
    c2 = yaml.safe_load(open(cfg_path, encoding='utf-8')) or {}
    if not c2.get('sources'):
      c2['sources'] = [{'kind': k, 'path': p} for k, p in parsed]
      write_text(cfg_path, dump_yaml(c2))


if __name__ == '__main__':
  main()
