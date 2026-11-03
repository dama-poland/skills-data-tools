"""Classification in the business glossary: bg_discover carries the highest
confidentiality seen, bg_draft writes `confidentiality` and every source in
`source_refs`, bg_site leaves terms that are not public out of every export,
and bg_update never lowers confidentiality or drops a source ref.

All notes are synthetic.
Run: python3 -m unittest tests.test_glossary_classification
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), 'skills',
                       'damapl-business-glossary', 'scripts')
sys.path.insert(0, SCRIPTS)
from bg_core import load_yaml, read_term  # noqa: E402

NOTES = {
  'alpha.md': ('Alpha Widget', 'public',
               'A synthetic widget that every public test note describes.'),
  'beta.md': ('Beta Ledger', 'restricted',
              'A synthetic ledger that only restricted notes describe.'),
  'gamma.md': ('Gamma Queue', None,
               'A synthetic queue from a note with no classification.'),
  'delta-1.md': ('Delta Record', 'public',
                 'A synthetic record described in a public note first.'),
  'delta-2.md': ('Delta Record', 'internal',
                 'A synthetic record that an internal note also describes.'),
  'odd.md': ('Odd Token', 'secret-ish',
             'A synthetic token from a note with an unknown classification.'),
}
for _n in range(1, 5):
  NOTES['eps-%d.md' % _n] = ('Epsilon Signal', 'public',
                             'A synthetic signal noted in public note %d.' % _n)


def note(name, conf, definition):
  fm = ['---', 'title: %s' % name]
  if conf:
    fm.append('confidentiality: %s' % conf)
  body = ['---', '', '# ' + name, '', definition, '']
  if name == 'Alpha Widget':   # a public term that links a restricted one
    body += ['See also [[Beta Ledger|the ledger]].', '']
  return '\n'.join(fm + body)


def run(script, *args, ok=True):
  p = subprocess.run([sys.executable, os.path.join(SCRIPTS, script)] +
                     list(args), capture_output=True, text=True)
  if ok and p.returncode != 0:
    raise AssertionError('%s failed:\n%s%s' % (script, p.stdout, p.stderr))
  return p


class Classification(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.tmp = tempfile.mkdtemp()
    cls.vault = os.path.join(cls.tmp, 'vault')
    os.makedirs(cls.vault)
    for fn, (name, conf, definition) in NOTES.items():
      with open(os.path.join(cls.vault, fn), 'w', encoding='utf-8') as fh:
        fh.write(note(name, conf, definition))
    cls.repo = os.path.join(cls.tmp, 'g')
    run('bg_init.py', cls.repo, '--name', 'Classified')
    run('bg_discover.py', '--repo', cls.repo, '--source',
        'obsidian:' + cls.vault)
    run('bg_draft.py', '--repo', cls.repo, '--top', '20')
    cls.site = run('bg_site.py', '--repo', cls.repo)

  @classmethod
  def tearDownClass(cls):
    shutil.rmtree(cls.tmp)

  def term(self, tid):
    return read_term(os.path.join(self.repo, 'terms', tid + '.md'))

  def test_discover_carries_highest_classification(self):
    cands = {c['id']: c for c in load_yaml(os.path.join(
      self.repo, '.glossary', 'candidates.yaml'))['candidates']}
    self.assertEqual(cands['alpha-widget']['confidentiality'], 'public')
    self.assertEqual(cands['beta-ledger']['confidentiality'], 'restricted')
    self.assertEqual(cands['gamma-queue']['confidentiality'], 'internal')
    self.assertEqual(cands['delta-record']['confidentiality'], 'internal')
    self.assertEqual(cands['odd-token']['confidentiality'], 'restricted')

  def test_draft_writes_confidentiality_and_all_source_refs(self):
    self.assertEqual(self.term('beta-ledger')['fm']['confidentiality'],
                     'restricted')
    self.assertEqual(self.term('delta-record')['fm']['confidentiality'],
                     'internal')
    eps = self.term('epsilon-signal')['fm']
    self.assertEqual(eps['confidentiality'], 'public')
    self.assertEqual(len(eps['source_refs']), 4)
    self.assertEqual(len(eps['source_origin'].split(',')), 4)

  def test_public_term_links_restricted_term_in_repo(self):
    self.assertIn('beta-ledger',
                  self.term('alpha-widget')['fm']['related_terms'])

  def test_site_exports_only_public_terms(self):
    out = os.path.join(self.repo, 'generated')
    data = json.load(open(os.path.join(out, 'terms.json'), encoding='utf-8'))
    ids = sorted(t['id'] for t in data['terms'])
    self.assertEqual(ids, ['alpha-widget', 'epsilon-signal'])
    for rel in ('terms.json', 'glossary.csv', 'site/index.html', 'a-z.md',
                'validation.json'):
      with open(os.path.join(out, rel), encoding='utf-8') as fh:
        text = fh.read()
      for word in ('Beta Ledger', 'beta-ledger', 'Gamma Queue',
                   'Delta Record', 'Odd Token', 'restricted notes'):
        self.assertNotIn(word, text, '%s leaks into %s' % (word, rel))

  def test_validation_json_lists_only_public_terms(self):
    out = os.path.join(self.repo, 'generated', 'validation.json')
    data = json.load(open(out, encoding='utf-8'))
    self.assertEqual(sorted(data['tiers']), ['alpha-widget', 'epsilon-signal'])
    for v in data['violations']:
      self.assertIn(v['term'], ('alpha-widget', 'epsilon-signal'))

  def edit_term(self, tid, old, new):
    path = os.path.join(self.repo, 'terms', tid + '.md')
    with open(path, encoding='utf-8') as fh:
      text = fh.read()
    self.assertIn(old, text)
    with open(path, 'w', encoding='utf-8') as fh:
      fh.write(text.replace(old, new, 1))
    return path, text

  def test_site_issues_do_not_name_hidden_terms(self):
    # aaa-hidden (restricted) duplicates the public name Alpha Widget, and
    # an is_a cycle runs through restricted beta-ledger and closes on the
    # public epsilon-signal: both MUST messages name a hidden id.
    hidden = os.path.join(self.repo, 'terms', 'aaa-hidden.md')
    beta = self.term('beta-ledger')['text']
    with open(hidden, 'w', encoding='utf-8') as fh:
      fh.write(beta.replace('id: beta-ledger', 'id: aaa-hidden')
               .replace('name: Beta Ledger', 'name: Alpha Widget'))
    saved = [self.edit_term(tid, 'relations: {}\n',
                            'relations:\n  is_a: [%s]\n' % parent)
             for tid, parent in (('alpha-widget', 'beta-ledger'),
                                 ('beta-ledger', 'epsilon-signal'),
                                 ('epsilon-signal', 'alpha-widget'))]
    try:
      out = os.path.join(self.tmp, 'out-issues')
      run('bg_site.py', '--repo', self.repo, '--out', out)
      data = json.load(open(os.path.join(out, 'terms.json'),
                            encoding='utf-8'))
      issues = {t['id']: t['issues'] for t in data['terms']}
      self.assertTrue(any('NAME-04' in x and 'withheld' in x
                          for x in issues['alpha-widget']), issues)
      self.assertTrue(any('REL-07' in x and 'withheld' in x
                          for x in issues['epsilon-signal']), issues)
      for rel in ('terms.json', 'site/index.html', 'validation.json'):
        with open(os.path.join(out, rel), encoding='utf-8') as fh:
          text = fh.read()
        for word in ('aaa-hidden', 'beta-ledger', 'Beta Ledger'):
          self.assertNotIn(word, text, '%s leaks into %s' % (word, rel))
    finally:
      os.remove(hidden)
      for path, text in saved:
        with open(path, 'w', encoding='utf-8') as fh:
          fh.write(text)

  def test_public_findings_withholds_hidden_names_and_ids(self):
    from bg_site import public_findings
    terms = [
      {'fm': {'id': 'alpha-widget', 'name': 'Alpha Widget',
              'confidentiality': 'public'}, 'title': 'Alpha Widget'},
      {'fm': {'id': 'beta-ledger', 'name': 'Beta Ledger',
              'alternative_names': ['Secret Book'],
              'confidentiality': 'restricted'}, 'title': 'Beta Ledger'},
    ]
    viol = [
      {'term': 'alpha-widget', 'rule': 'R-1', 'level': 'MUST',
       'message': 'clashes with beta ledger'},
      {'term': 'alpha-widget', 'rule': 'R-2', 'level': 'MUST',
       'message': 'see the Secret Book entry'},
      {'term': 'alpha-widget', 'rule': 'R-3', 'level': 'MUST',
       'message': "duplicate name 'Alpha Widget' (also beta-ledger)"},
      {'term': 'alpha-widget', 'rule': 'R-4', 'level': 'MUST',
       'message': 'link to beta-ledgers-x is fine'},
      {'term': 'beta-ledger', 'rule': 'R-5', 'level': 'MUST',
       'message': 'hidden term finding'},
    ]
    got = public_findings(viol, terms)
    self.assertEqual([v['rule'] for v in got], ['R-1', 'R-2', 'R-3', 'R-4'])
    for v in got[:3]:
      self.assertIn('withheld', v['message'])
    self.assertEqual(got[3]['message'], 'link to beta-ledgers-x is fine')

  def test_site_prints_what_was_excluded(self):
    out = self.site.stdout
    self.assertIn('excluded', out)
    for tid in ('beta-ledger', 'gamma-queue', 'delta-record', 'odd-token'):
      self.assertIn(tid, out)

  def test_site_excludes_term_without_confidentiality(self):
    path = os.path.join(self.repo, 'terms', 'alpha-widget.md')
    with open(path, encoding='utf-8') as fh:
      orig = fh.read()
    try:
      with open(path, 'w', encoding='utf-8') as fh:
        fh.write(orig.replace('confidentiality: public\n', ''))
      out = os.path.join(self.tmp, 'out-missing')
      p = run('bg_site.py', '--repo', self.repo, '--out', out)
      data = json.load(open(os.path.join(out, 'terms.json'),
                            encoding='utf-8'))
      self.assertNotIn('alpha-widget', [t['id'] for t in data['terms']])
      self.assertIn('alpha-widget', p.stdout)
    finally:
      with open(path, 'w', encoding='utf-8') as fh:
        fh.write(orig)

  def patch(self, body):
    pfile = os.path.join(self.tmp, 'p.yaml')
    with open(pfile, 'w', encoding='utf-8') as fh:
      fh.write(body)
    return run('bg_update.py', '--repo', self.repo, '--patch', pfile,
               '--dry-run', ok=False)

  def test_update_refuses_lowering_confidentiality(self):
    p = self.patch('- id: beta-ledger\n  set: {confidentiality: public}\n')
    self.assertNotEqual(p.returncode, 0)
    self.assertIn('confidentiality', p.stdout)

  def test_update_allows_raising_confidentiality(self):
    p = self.patch('- id: alpha-widget\n  set: {confidentiality: internal}\n')
    self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

  def test_update_refuses_removing_source_refs(self):
    ref = self.term('alpha-widget')['fm']['source_refs'][0]
    p = self.patch('- id: alpha-widget\n  remove: {source_refs: [%s]}\n'
                   % json.dumps(ref))
    self.assertNotEqual(p.returncode, 0)
    self.assertIn('source_refs', p.stdout)
    p = self.patch('- id: alpha-widget\n  set: {source_refs: []}\n')
    self.assertNotEqual(p.returncode, 0)
    self.assertIn('source_refs', p.stdout)

  def test_update_allows_adding_source_refs(self):
    p = self.patch('- id: alpha-widget\n'
                   '  add: {source_refs: ["folder:extra.md"]}\n')
    self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

  def test_from_sources_proposal_raises_confidentiality(self):
    from bg_core import load_config, load_terms
    from bg_update import propose
    src = os.path.join(self.tmp, 'later')
    os.makedirs(src, exist_ok=True)
    path = os.path.join(src, 'alpha-v2.md')
    with open(path, 'w', encoding='utf-8') as fh:
      fh.write(note('Alpha Widget', 'restricted',
                    'A synthetic widget with a restricted new wording.'))
    cfg = dict(load_config(self.repo),
               sources=[{'kind': 'obsidian', 'path': src}])
    ops = [o for o in propose(self.repo, cfg, load_terms(self.repo, cfg))
           if o['id'] == 'alpha-widget']
    self.assertEqual(len(ops), 1)
    self.assertEqual(ops[0]['set'], {'confidentiality': 'restricted'})
    self.assertEqual(ops[0]['add'],
                     {'source_refs': ['obsidian:alpha-v2.md']})


if __name__ == '__main__':
  unittest.main(verbosity=2)
