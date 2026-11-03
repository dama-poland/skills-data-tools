"""Ids in the business glossary: Polish and other Latin diacritics are
transliterated, a name that has no letters still gets a valid id, and two
different names never share an id (the later one gets a stable suffix).

All names are synthetic.
Run: python3 -m unittest tests.test_glossary_slug
"""

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
from bg_core import SLUG_RE, load_yaml, name_key, slugify  # noqa: E402


def run(script, *args, ok=True):
  p = subprocess.run([sys.executable, os.path.join(SCRIPTS, script)] +
                     list(args), capture_output=True, text=True)
  if ok and p.returncode != 0:
    raise AssertionError('%s failed:\n%s%s' % (script, p.stdout, p.stderr))
  return p


class Slugify(unittest.TestCase):
  def test_polish_letters_are_transliterated(self):
    self.assertEqual(slugify('Żółć'), 'zolc')
    self.assertEqual(slugify('Łódź'), 'lodz')
    self.assertEqual(slugify('Zażółć gęślą jaźń'), 'zazolc-gesla-jazn')
    self.assertEqual(slugify('ĄĆĘŁŃÓŚŹŻ'), 'acelnoszz')

  def test_other_latin_diacritics(self):
    self.assertEqual(slugify('Café Crème'), 'cafe-creme')
    self.assertEqual(slugify('Straße'), 'strasse')

  def test_ascii_behaviour_is_unchanged(self):
    self.assertEqual(slugify('Customer Journey'), 'customer-journey')
    self.assertEqual(slugify('Churn (Process)'), 'churn')

  def test_name_without_latin_letters_never_gives_empty_id(self):
    for name in ('日本語', 'Клиент', '(only qualifier)', '+++'):
      sid = slugify(name)
      self.assertTrue(SLUG_RE.match(sid), (name, sid))
    self.assertEqual(slugify('日本語'), slugify('日本語'))
    self.assertNotEqual(slugify('日本語'), slugify('Клиент'))


def note(name, definition):
  return '---\ntitle: %s\nconfidentiality: public\n---\n\n# %s\n\n%s\n' % (
    name, name, definition)


NOTES = {
  'a.md': ('Żółć', 'A synthetic bile description for the slug tests.'),
  'b.md': ('Zolc', 'A synthetic plain spelling that folds to the same id.'),
  'c.md': ('Łódź', 'A synthetic city description for the slug tests.'),
  'd.md': ('żółć', 'The same name in lower case describes the first term.'),
  'e.md': ('日本語', 'A synthetic name without any Latin letter inside.'),
  'f.md': ('Клиент', 'Another synthetic name without any Latin letter.'),
}


class DiscoverIds(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.tmp = tempfile.mkdtemp()
    cls.vault = os.path.join(cls.tmp, 'vault')
    os.makedirs(cls.vault)
    for fn, (name, defn) in NOTES.items():
      with open(os.path.join(cls.vault, fn), 'w', encoding='utf-8') as fh:
        fh.write(note(name, defn))

  @classmethod
  def tearDownClass(cls):
    shutil.rmtree(cls.tmp)

  def setUp(self):
    self.repo = tempfile.mkdtemp(dir=self.tmp)
    shutil.rmtree(self.repo)
    run('bg_init.py', self.repo, '--name', 'Slug')

  def discover(self):
    run('bg_discover.py', '--repo', self.repo, '--source',
        'obsidian:' + self.vault)
    return load_yaml(os.path.join(
      self.repo, '.glossary', 'candidates.yaml'))['candidates']

  def test_ids_are_valid_and_unique(self):
    cands = self.discover()
    ids = [c['id'] for c in cands]
    self.assertEqual(len(ids), len(set(ids)))
    for c in cands:
      self.assertTrue(SLUG_RE.match(c['id']), c)
    names = sorted(c['name'] for c in cands)
    # Zolc and Żółć are two names; żółć is a case variant of Żółć.
    self.assertEqual(len(cands), 5, names)
    self.assertIn('lodz', ids)
    self.assertIn('zolc', ids)

  def test_ids_do_not_depend_on_source_order(self):
    first = {name_key(c['name']): c['id'] for c in self.discover()}
    os.rename(os.path.join(self.vault, 'a.md'),
              os.path.join(self.vault, 'z.md'))
    try:
      second = {name_key(c['name']): c['id'] for c in self.discover()}
    finally:
      os.rename(os.path.join(self.vault, 'z.md'),
                os.path.join(self.vault, 'a.md'))
    self.assertEqual(first, second)

  def test_drafted_terms_validate_without_must(self):
    self.discover()
    run('bg_draft.py', '--repo', self.repo, '--top', '20')
    files = sorted(os.listdir(os.path.join(self.repo, 'terms')))
    self.assertIn('lodz.md', files)
    p = run('bg_validate.py', '--repo', self.repo, '--level', 'MUST')
    self.assertIn('0 MUST', p.stdout)

  def test_existing_term_with_other_name_is_not_reused(self):
    self.discover()
    run('bg_draft.py', '--repo', self.repo, '--ids', 'zolc')
    cands = {c['name']: c for c in self.discover()}
    self.assertTrue(cands['Zolc']['exists'])
    self.assertFalse(cands['Żółć']['exists'])
    self.assertNotEqual(cands['Żółć']['id'], 'zolc')

  def test_rediscovery_keeps_ids_and_marks_all_existing(self):
    first = {c['name']: c['id'] for c in self.discover()}
    run('bg_draft.py', '--repo', self.repo, '--top', '20')
    again = self.discover()
    self.assertTrue(all(c['exists'] for c in again))
    self.assertEqual({name_key(n): i for n, i in first.items()},
                     {name_key(c['name']): c['id'] for c in again})

  def test_from_sources_ignores_a_different_name_with_the_same_slug(self):
    from bg_core import load_config, load_terms
    from bg_update import propose
    self.discover()
    run('bg_draft.py', '--repo', self.repo, '--ids', 'zolc')
    other = os.path.join(self.tmp, 'other')
    os.makedirs(other, exist_ok=True)
    with open(os.path.join(other, 'n.md'), 'w', encoding='utf-8') as fh:
      fh.write(note('Żółć', 'A synthetic different wording of another '
                    'name that only shares the slug.'))
    cfg = dict(load_config(self.repo),
               sources=[{'kind': 'obsidian', 'path': other}])
    self.assertEqual(propose(self.repo, cfg, load_terms(self.repo, cfg)), [])


if __name__ == '__main__':
  unittest.main()
