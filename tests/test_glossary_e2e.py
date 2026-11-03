"""End-to-end tests. Run: python3 tests/test_glossary_e2e.py  (needs PyYAML).

A synthetic second-brain vault (tests/fixtures/second-brain) runs end to end
(init, discover, draft, validate, update, relations, site) under both the
the `minimal` profile. The `standard` profile is planned (SPEC.md 5.3).
"""

import hashlib
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SK = os.path.join(os.path.dirname(HERE), 'skills', 'damapl-business-glossary')
SCRIPTS = os.path.join(SK, 'scripts')
FIX = os.path.join(HERE, 'fixtures')
sys.path.insert(0, SCRIPTS)
from bg_core import read_term  # noqa: E402


def run(script, *args, ok=True):
  p = subprocess.run([sys.executable, os.path.join(SCRIPTS, script)] +
                     list(args), capture_output=True, text=True)
  if ok and p.returncode != 0:
    raise AssertionError('%s failed:\n%s%s' % (script, p.stdout, p.stderr))
  return p


def rd(path):
  with open(path, encoding='utf-8') as fh:
    return fh.read()


def wr(path, text):
  with open(path, 'w', encoding='utf-8') as fh:
    fh.write(text)


def digest(d):
  h = hashlib.sha256()
  for n in sorted(os.listdir(d)):
    with open(os.path.join(d, n), 'rb') as fh:
      h.update(fh.read())
  return h.hexdigest()


class SecondBrain(unittest.TestCase):
  PROFILE = 'minimal'

  @classmethod
  def setUpClass(cls):
    cls.tmp = tempfile.mkdtemp()
    cls.repo = os.path.join(cls.tmp, 'g')
    run('bg_init.py', cls.repo, '--name', 'SB', '--languages', 'en,pl',
        '--profile', cls.PROFILE)
    run('bg_discover.py', '--repo', cls.repo, '--source',
        'obsidian:' + os.path.join(FIX, 'second-brain'),
        '--source', 'csv:' + os.path.join(FIX, 'terms-list.csv'))
    run('bg_draft.py', '--repo', cls.repo, '--top', '30')

  @classmethod
  def tearDownClass(cls):
    shutil.rmtree(cls.tmp)

  def terms(self):
    d = os.path.join(self.repo, 'terms')
    return sorted(f for f in os.listdir(d) if f.endswith('.md'))

  def test_01_discovery_and_dedupe(self):
    names = self.terms()
    self.assertIn('customer-journey.md', names)
    self.assertIn('net-promoter-score.md', names)       # glossary bullet
    self.assertIn('service-level-agreement.md', names)  # glossary table
    self.assertIn('onboarding.md', names)               # csv
    self.assertNotIn('2026-10-01.md', names)            # daily note junk
    t = read_term(os.path.join(self.repo, 'terms', 'customer-journey.md'))
    self.assertIn('Buyer Journey', t['fm']['alternative_names'])
    self.assertEqual(len(t['fm']['source_origin'].split(',')), 2)  # merged

  def test_02_spot_check_ten_percent(self):
    names = self.terms()
    rnd = random.Random(7)
    for n in rnd.sample(names, max(1, len(names) // 10)):
      t = read_term(os.path.join(self.repo, 'terms', n))
      self.assertEqual(t['fm']['id'] + '.md', n)
      self.assertEqual(t['title'], t['fm']['name'])
      self.assertEqual(t['fm']['status'], 'Draft')
      self.assertNotIn('[[', t['text'])
      self.assertTrue(t['definition'])

  def test_03_validate_clean_of_must(self):
    p = run('bg_validate.py', '--repo', self.repo, '--strict')
    self.assertIn('0 MUST', p.stdout)

  def test_04_one_way_related(self):
    p = run('bg_validate.py', '--repo', self.repo, '--format', 'json')
    v = json.loads(p.stdout)['violations']
    self.assertFalse([x for x in v if x['rule'] == 'REL-08'])

  def test_05_update_is_surgical(self):
    path = os.path.join(self.repo, 'terms', 'persona.md')
    before = rd(path)
    patch = os.path.join(self.tmp, 'p.yaml')
    wr(patch,
       '- id: persona\n  add: {alternative_names: [Buyer Persona]}\n'
       '  sections: {What it is: "- A customer archetype"}\n')
    run('bg_update.py', '--repo', self.repo, '--patch', patch)
    after = rd(path)
    import difflib
    changed = [l for l in difflib.unified_diff(
      before.splitlines(), after.splitlines(), lineterm='', n=0)
      if l[:1] in '+-' and l[:3] not in ('+++', '---')]
    self.assertLess(len(changed), 12)
    t = read_term(path)
    self.assertEqual(t['fm']['version'], '1.1.0')
    self.assertEqual(t['fm']['id'], 'persona')
    self.assertIn('Buyer Persona', t['fm']['alternative_names'])

  def test_06_id_is_immutable(self):
    patch = os.path.join(self.tmp, 'bad.yaml')
    wr(patch, '- id: metric\n  set: {id: kpi}\n')
    p = run('bg_update.py', '--repo', self.repo, '--patch', patch, ok=False)
    self.assertNotEqual(p.returncode, 0)
    self.assertIn('immutable', p.stdout)

  def test_07_ghost_id_detected(self):
    run('bg_validate.py', '--repo', self.repo, '--lock')
    old = os.path.join(self.repo, 'terms', 'metric.md')
    new = os.path.join(self.repo, 'terms', 'kpi.md')
    text = rd(old)
    os.remove(old)
    with open(new, 'w') as fh:       # simulate an id change (ghost term)
      fh.write(text.replace('id: metric', 'id: kpi'))
    p = run('bg_validate.py', '--repo', self.repo, '--strict', ok=False)
    self.assertNotEqual(p.returncode, 0)
    self.assertIn('ID-03', p.stdout)
    os.remove(new)
    with open(old, 'w') as fh:
      fh.write(text)

  def test_08_site_offline_bundle(self):
    run('bg_site.py', '--repo', self.repo)
    html = rd(os.path.join(
      self.repo, 'generated', 'site', 'index.html'))
    self.assertNotIn('http://cdn', html)
    self.assertNotIn('src="http', html)
    self.assertIn('d3js.org', html)       # vendored library is inlined
    data = json.loads(rd(os.path.join(
      self.repo, 'generated', 'terms.json')))
    self.assertEqual(len(data['terms']), len(self.terms()))
    self.assertTrue(os.path.isfile(os.path.join(
      self.repo, 'generated', 'a-z.md')))

  def test_09_dry_run_writes_nothing(self):
    before = digest(os.path.join(self.repo, 'terms'))
    run('bg_relations.py', '--repo', self.repo, '--dry-run')
    run('bg_update.py', '--repo', self.repo, '--bump-only', 'persona',
        '--dry-run')
    self.assertEqual(before, digest(os.path.join(self.repo, 'terms')))


class StandardProfilePlanned(unittest.TestCase):
  def test_standard_profile_is_rejected_with_clear_message(self):
    tmp = tempfile.mkdtemp()
    try:
      p = run('bg_init.py', os.path.join(tmp, 'g'), '--profile', 'standard',
              ok=False)
      self.assertNotEqual(p.returncode, 0)
      self.assertIn('planned', p.stdout + p.stderr)
    finally:
      shutil.rmtree(tmp)


if __name__ == '__main__':
  unittest.main(verbosity=2)
