#!/usr/bin/env python3
"""Draft term files from accepted candidates. Create-only: an existing
term is never overwritten (use bg_update.py for that). Status is always
the profile's agent_status (Draft). Every term gets the candidate's
confidentiality and all of its sources in `source_refs`.

  bg_draft.py --repo G --top 20            # skips accept: false
  bg_draft.py --repo G --ids candidate,job-offer
  bg_draft.py --repo G --accepted          # candidates with accept: true
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bg_core import (SLUG_RE, as_list, common_args, default_author,
                     dump_yaml, highest_classification, load_config,
                     load_profile, load_terms, load_yaml, need_repo,
                     split_sentences, today, write_text)

WIKI = re.compile(r'\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]*))?\]\]')


def unwiki(text):
  return WIKI.sub(lambda m: m.group(2) or m.group(1), text or '')


def render(prof, cfg, cand, author):
  sources = [str(x) for x in as_list(cand.get('sources'))]
  conf = highest_classification([cand.get('confidentiality')])
  opts = {'id': cand['id'], 'name': cand['name'],
          'type': cand.get('type_hint') or cfg.get('default_type', 'Concept'),
          'source_origin': ', '.join(sources) or 'n/a',
          'confidentiality': conf,
          'author': author, 'today': today()}
  if opts['type'] not in prof.get('types', [opts['type']]):
    opts['type'] = cfg.get('default_type', 'Concept')
  fm = {}
  for k, v in (prof.get('template') or {}).items():
    fm[k] = v.format(**opts) if isinstance(v, str) else v
  fm['confidentiality'] = conf
  fm['source_refs'] = sources
  if cand.get('aliases'):
    fm['alternative_names'] = cand['aliases']
  if 'pl' in cfg.get('languages', []):
    fm['name_pl'] = cand.get('name_pl') or ''
    fm['description_pl'] = cand.get('definition_pl') or ''
  related = [x for x in as_list(cand.get('links')) if x != cand['id']][:3]
  fm['related_terms'] = related
  sents = split_sentences(unwiki(cand.get('definition', '')))
  defn = ' '.join(sents[:2]) or 'TODO: write a one or two sentence definition.'
  rest = ' '.join(sents[2:])
  parts = ['---', dump_yaml(fm).rstrip('\n'), '---', '',
           '# ' + cand['name'], '', defn, '']
  for title in prof.get('sections') or ['Description Details', 'What it is']:
    parts += ['## ' + title, '']
    if title == 'Description Details':
      parts.append(rest or 'TODO: add rationale, usage or scope.')
    elif title == 'What it is':
      b = [unwiki(x) for x in as_list(cand.get('bullets'))[:4]]
      parts += ['- ' + x for x in b] if b else ['- TODO: essential trait']
    else:
      parts.append('- TODO: Not X; that is Y')
    parts.append('')
  return '\n'.join(parts)


def one_way(pick):
  """Drop mirrored links among the picked candidates (REL-08): the
  term with fewer links keeps the link; ties go to the lower id."""
  links = {c['id']: list(as_list(c.get('links'))) for c in pick}
  for i in sorted(links):
    for x in list(links[i]):
      if x in links and i in links[x]:
        loser = i if (len(links[i]), i) > (len(links[x]), x) else x
        links[loser].remove(i if loser == x else x)
  for c in pick:
    c['links'] = links[c['id']]


def main():
  ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
  common_args(ap)
  g = ap.add_mutually_exclusive_group(required=True)
  g.add_argument('--top', type=int,
                 help='draft the top N new candidates; a candidate the '
                      'user vetoed with accept: false is skipped')
  g.add_argument('--ids', help='comma list of candidate ids')
  g.add_argument('--accepted', action='store_true',
                 help="candidates marked accept: true in candidates.yaml")
  ap.add_argument('--author', default=None)
  a = ap.parse_args()
  repo = need_repo(a)
  cfg, prof = load_config(repo), None
  prof = load_profile(repo, cfg)
  cpath = os.path.join(repo, '.glossary', 'candidates.yaml')
  if not os.path.isfile(cpath):
    sys.exit('run bg_discover.py first')
  cands = load_yaml(cpath).get('candidates') or []
  if a.top:
    for c in cands:
      if c.get('accept') is False:
        print('skip (accept: false): %s' % c['id'])
    pick = [c for c in cands
            if not c.get('exists') and c.get('accept') is not False][:a.top]
  elif a.ids:
    want = set(a.ids.split(','))
    pick = [c for c in cands if c['id'] in want]
  else:
    pick = [c for c in cands if c.get('accept') is True]
  existing = {t['fm'].get('id') for t in load_terms(repo, cfg)}
  author = a.author or default_author(cfg)
  made = 0
  one_way(pick)
  for c in pick:
    if not SLUG_RE.match(c['id']):
      print('skip bad id %r' % c['id'])
      continue
    path = os.path.join(repo, cfg['terms_dir'], c['id'] + '.md')
    if c['id'] in existing or os.path.exists(path):
      print('skip (exists, use bg_update): %s' % c['id'])
      continue
    write_text(path, render(prof, cfg, c, author) + '\n', a.dry_run)
    print('%s %s' % ('would draft' if a.dry_run else 'drafted', c['id']))
    made += 1
  if not a.dry_run and made:
    lock = os.path.join(repo, '.glossary', 'ids.lock')
    ids = set(open(lock).read().split()) if os.path.isfile(lock) else set()
    ids |= {c['id'] for c in pick if os.path.exists(os.path.join(
      repo, cfg['terms_dir'], c['id'] + '.md'))}
    write_text(lock, '\n'.join(sorted(ids)) + '\n')
  print('%d term(s)' % made)


if __name__ == '__main__':
  main()
