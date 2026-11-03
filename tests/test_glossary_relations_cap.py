"""The `related_terms` cap is three everywhere: the minimal profile's
REL-08, `bg_relations` without `--max`, `bg_draft` and the term schema agree.
A term over the cap is reported by `bg_validate` as a finding for a human;
no script trims it on its own.

All content is synthetic.
Run: python3 -m unittest tests.test_glossary_relations_cap
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPTS = os.path.join(ROOT, 'skills', 'damapl-business-glossary', 'scripts')
PROFILE = os.path.join(ROOT, 'skills', 'damapl-business-glossary', 'assets',
                       'profiles', 'minimal.yaml')
SCHEMA = os.path.join(ROOT, 'shared', 'references', 'term-schema.md')

NAMES = ['Alpha Item', 'Beta Item', 'Gamma Item', 'Delta Item',
         'Epsilon Item']
OVER_CAP = ['beta-item', 'gamma-item', 'delta-item', 'epsilon-item']


def run(script, *args):
  return subprocess.run([sys.executable, os.path.join(SCRIPTS, script)] +
                        list(args), capture_output=True, text=True)


def frontmatter(path):
  text = Path(path).read_text(encoding='utf-8')
  return yaml.safe_load(text[4:text.find('\n---\n', 4)]) or {}


class RelationsCap(unittest.TestCase):
  def setUp(self):
    self.tmp = tempfile.mkdtemp()
    sources = os.path.join(self.tmp, 'notes')
    os.makedirs(sources)
    for name in NAMES:
      with open(os.path.join(sources, name.lower().replace(' ', '-') + '.md'),
                'w', encoding='utf-8') as fh:
        fh.write('# %s\n\nA synthetic item for the relations cap test. '
                 'It has no other purpose.\n' % name)
    self.repo = os.path.join(self.tmp, 'g')
    for args in (('bg_init.py', self.repo, '--name', 'Synthetic Glossary'),
                 ('bg_discover.py', '--repo', self.repo, '--source',
                  'folder:' + sources),
                 ('bg_draft.py', '--repo', self.repo, '--top', '10')):
      done = run(*args)
      self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
    self.path = os.path.join(self.repo, 'terms', 'alpha-item.md')
    text = Path(self.path).read_text(encoding='utf-8')
    links = ''.join('\n- %s' % x for x in OVER_CAP)
    with open(self.path, 'w', encoding='utf-8') as fh:
      fh.write(text.replace('related_terms: []', 'related_terms:' + links))

  def tearDown(self):
    shutil.rmtree(self.tmp)

  def test_validator_reports_a_term_over_the_cap(self):
    done = run('bg_validate.py', '--repo', self.repo, '--format', 'json')
    report = yaml.safe_load(done.stdout)
    found = [v for v in report['violations']
             if v['rule'] == 'REL-08' and v['term'] == 'alpha-item']
    self.assertEqual(len(found), 1, report['violations'])
    self.assertEqual(found[0]['level'], 'SHOULD')
    self.assertIn('max 3', found[0]['message'])

  def test_validator_does_not_trim_the_term(self):
    run('bg_validate.py', '--repo', self.repo)
    self.assertEqual(frontmatter(self.path)['related_terms'], OVER_CAP)

  def test_relations_caps_at_three_by_default(self):
    done = run('bg_relations.py', '--repo', self.repo)
    self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
    self.assertEqual(frontmatter(self.path)['related_terms'], OVER_CAP[:3])

  def test_profile_and_schema_document_the_same_cap(self):
    profile = yaml.safe_load(Path(PROFILE).read_text(encoding='utf-8'))
    rel_08 = [r for r in profile['rules'] if r['id'] == 'REL-08']
    self.assertEqual(rel_08[0]['params']['max'], 3)
    schema = Path(SCHEMA).read_text(encoding='utf-8')
    self.assertIn('| `related_terms` | at most 3, one-way |', schema)


if __name__ == '__main__':
  unittest.main()
