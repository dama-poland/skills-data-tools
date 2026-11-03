#!/usr/bin/env python3
"""Build the derived views: one offline HTML site (search, A-Z, graph,
type/category views, per-term pages), terms.json, glossary.csv, a-z.md.

D3 is inlined from assets/vendor, so index.html opens with no server and
no network. Output goes to <repo>/generated/ (gitignored by default).
Only terms with `confidentiality: public` reach the site, terms.json,
glossary.csv, a-z.md and validation.json; a missing value counts as not
public. Excluded
terms are listed on stdout, and links to them are dropped from the views.

  bg_site.py --repo G [--out DIR] [--dry-run]
"""

import argparse
import csv
import html
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bg_core import (SKILL_DIR, as_list, common_args, need_repo,
                     normalize_classification, rel_targets, write_text)
from bg_validate import run

OWNER_KEYS = ('created_by', 'business_owner', 'technical_owner',
              'data_steward')


HTTP_URL_RE = re.compile(r'^https?://\S+$', re.IGNORECASE)
CSV_FORMULA_START = ('=', '+', '-', '@', '\t', '\r')


def web_concordance(entries):
  """Keep the label of each concordance entry; keep its url only if it is
  an http(s) link. Other schemes (javascript:, data:, file:) are dropped."""
  out = []
  for c in entries:
    if not isinstance(c, dict):
      continue
    url = str(c.get('url') or '').strip()
    out.append({'url': url if HTTP_URL_RE.match(url) else '',
                'label': c.get('label') or ''})
  return out


def csv_safe(value):
  """Neutralise a CSV cell that a spreadsheet would read as a formula."""
  text = str(value)
  return "'" + text if text.startswith(CSV_FORMULA_START) else text


def is_public(t):
  return normalize_classification(t['fm'].get('confidentiality')) == 'public'


def drop_hidden(x, hidden):
  """Remove links to excluded terms from one exported term."""
  for k in ('related_terms', 'homonym_of'):
    x[k] = [v for v in x[k] if v not in hidden]
  x['relations'] = {k: [v for v in vs if v not in hidden]
                    for k, vs in x['relations'].items()}
  x['relations'] = {k: vs for k, vs in x['relations'].items() if vs}
  for k in ('boundary_term_ref', 'successor_term'):
    if x[k] in hidden:
      x[k] = None
  return x


def term_json(t, tr, issues):
  fm = t['fm']
  rels = rel_targets(fm)
  return {
    'id': fm.get('id'), 'name': fm.get('name') or t['title'],
    'name_pl': fm.get('name_pl') or '', 'type': fm.get('type') or 'Concept',
    'category': fm.get('category') or '',
    'status': fm.get('status') or 'Draft', 'tier': tr,
    'acronyms': [str(x) for x in as_list(fm.get('acronyms'))],
    'alternative_names': [str(x) for x in as_list(
      fm.get('alternative_names'))],
    'definition': t['definition'],
    'description_pl': fm.get('description_pl') or '',
    'sections': t['sections'], 'titles': t['titles'],
    'related_terms': as_list(fm.get('related_terms')),
    'relations': {k: v for k, v in rels.items() if v},
    'homonym_of': as_list(fm.get('homonym_of')),
    'boundary_term_ref': fm.get('boundary_term_ref'),
    'successor_term': fm.get('successor_term'),
    'concordance': web_concordance(as_list(fm.get('concordance'))),
    'owners': {k: str(fm[k]) for k in OWNER_KEYS if fm.get(k)},
    'version': str(fm.get('version') or ''),
    'last_reviewed': str(fm.get('last_reviewed') or ''),
    'source_origin': str(fm.get('source_origin') or ''),
    'issues': issues,
  }


def main():
  ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
  common_args(ap)
  ap.add_argument('--out', default=None, help='default <repo>/generated')
  a = ap.parse_args()
  repo = need_repo(a)
  cfg, prof, terms, viol, tiers = run(repo)
  out = os.path.abspath(a.out or os.path.join(repo, 'generated'))
  public_ids = {t['fm'].get('id') for t in terms if is_public(t)}
  viol = [v for v in viol if v['term'] in public_ids]
  tiers = {i: tr for i, tr in tiers.items() if i in public_ids}
  issues = {}
  for v in viol:
    if v['level'] == 'MUST':
      issues.setdefault(v['term'], []).append(
        '%s: %s' % (v['rule'], v['message']))
  items, excluded = [], []
  for t in terms:
    i = t['fm'].get('id')
    if not i or t['fm'].get('status') == 'Archived':
      continue
    if not is_public(t):
      excluded.append((i, t['fm'].get('confidentiality') or
                       'no confidentiality'))
      continue
    items.append(term_json(t, tiers.get(i, 'Below'), issues.get(i, [])))
  hidden = {i for i, _ in excluded}
  items = [drop_hidden(x, hidden) for x in items]
  items.sort(key=lambda x: x['name'].lower())
  data = {
    'title': cfg.get('name', 'Business Glossary'),
    'languages': cfg.get('languages', ['en']),
    'primary_language': cfg.get('primary_language', 'en'),
    'profile': prof.get('name'), 'terms': items,
  }
  blob = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
  tpl = open(os.path.join(SKILL_DIR, 'assets', 'site_template.html'),
             encoding='utf-8').read()
  d3 = open(os.path.join(SKILL_DIR, 'assets', 'vendor', 'd3.min.js'),
            encoding='utf-8').read().replace('</script', '<\\/script')
  parts = {'__TITLE__': html.escape(str(data['title'])), '__D3__': d3,
           '__DATA__': blob}
  page = re.sub('__TITLE__|__D3__|__DATA__', lambda m: parts[m.group(0)], tpl)
  buf = io.StringIO()
  w = csv.writer(buf)
  w.writerow(['id', 'name', 'name_pl', 'type', 'category', 'status',
              'tier', 'definition', 'version'])
  for x in items:
    w.writerow([csv_safe(v) for v in (
      x['id'], x['name'], x['name_pl'], x['type'], x['category'],
      x['status'], x['tier'], x['definition'], x['version'])])
  az = ['---', 'title: %s A-Z index' % data['title'],
        'summary: Generated alphabetical index of every glossary term; '
        'do not edit by hand.', '---', '']
  cur = ''
  for x in items:
    L = x['name'][:1].upper()
    if L != cur:
      cur = L
      az += ['', '## ' + L, '']
    az.append('- [%s](../terms/%s.md) (%s): %s' % (
      x['name'], x['id'], x['type'], x['definition'][:100]))
  files = {
    'site/index.html': page,
    'terms.json': json.dumps(data, ensure_ascii=False, indent=1),
    'glossary.csv': buf.getvalue(),
    'a-z.md': '\n'.join(az) + '\n',
    'validation.json': json.dumps(
      {'violations': viol, 'tiers': tiers}, indent=1),
  }
  for rel, text in files.items():
    print('%s %s (%d KB)' % ('would write' if a.dry_run else 'wrote',
                             os.path.join(out, rel), len(text) // 1024))
    write_text(os.path.join(out, rel), text, a.dry_run)
  print('%d terms' % len(items))
  if excluded:
    print('excluded %d term(s) that are not public:' % len(excluded))
    for i, conf in excluded:
      print('  %s (%s)' % (i, conf))


if __name__ == '__main__':
  main()
