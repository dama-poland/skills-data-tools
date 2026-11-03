"""Validation strictness in the business glossary: a term with a DRAFT-TODO
placeholder never reaches Silver or Gold, `--strict` fails on SHOULD
findings too (use `--level MUST` for MUST only), and a term whose YAML does
not parse is a MUST finding that keeps it below every tier.

All content is synthetic.
Run: python3 -m unittest tests.test_glossary_validation
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


def run(script, *args):
  return subprocess.run([sys.executable, os.path.join(SCRIPTS, script)] +
                        list(args), capture_output=True, text=True)


SOURCE = ('---\nconfidentiality: public\n---\n# Churn Rate\n\n'
          'The share of customers who stop buying in a period. '
          'It is reviewed monthly.\n')


class Validation(unittest.TestCase):
  def setUp(self):
    self.tmp = tempfile.mkdtemp()
    src = os.path.join(self.tmp, 'v')
    os.makedirs(src)
    with open(os.path.join(src, 'c.md'), 'w', encoding='utf-8') as fh:
      fh.write(SOURCE)
    self.repo = os.path.join(self.tmp, 'g')
    for args in (('bg_init.py', self.repo, '--name', 'T'),
                 ('bg_discover.py', '--repo', self.repo, '--source',
                  'folder:' + src),
                 ('bg_draft.py', '--repo', self.repo, '--top', '3')):
      p = run(*args)
      self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
    self.path = os.path.join(self.repo, 'terms', 'churn-rate.md')

  def tearDown(self):
    shutil.rmtree(self.tmp)

  def edit(self, fn):
    with open(self.path, encoding='utf-8') as fh:
      text = fh.read()
    with open(self.path, 'w', encoding='utf-8') as fh:
      fh.write(fn(text))

  def finish_draft(self):
    self.edit(lambda t: t.replace(
      'TODO: add rationale, usage or scope.', 'Reviewed monthly by owners.'
    ).replace('- TODO: essential trait', '- A share, not a count'))

  def report(self, *args):
    p = run('bg_validate.py', '--repo', self.repo, '--format', 'json', *args)
    return p, json.loads(p.stdout)

  def test_todo_placeholder_blocks_silver(self):
    _, rep = self.report()
    self.assertIn('DRAFT-TODO', [v['rule'] for v in rep['violations']])
    self.assertEqual(rep['tiers']['churn-rate'], 'Bronze')

  def test_finished_term_reaches_silver(self):
    self.finish_draft()
    _, rep = self.report()
    self.assertEqual(rep['violations'], [])
    self.assertEqual(rep['tiers']['churn-rate'], 'Silver')

  def test_one_remaining_todo_is_enough_to_block_silver(self):
    self.finish_draft()
    self.edit(lambda t: t.replace('A share, not a count',
                                  'A share, TODO: refine this trait'))
    _, rep = self.report()
    self.assertEqual(rep['tiers']['churn-rate'], 'Bronze')

  def test_todo_placeholder_blocks_gold(self):
    self.edit(lambda t: t.replace('status: Draft', 'status: Approved')
              .replace('last_reviewed: null',
                       'last_reviewed: ' + _today()))
    _, rep = self.report()
    self.assertNotIn(rep['tiers']['churn-rate'], ('Gold', 'Silver'))

  def test_strict_fails_on_should_findings(self):
    p = run('bg_validate.py', '--repo', self.repo, '--strict')
    self.assertNotEqual(p.returncode, 0, p.stdout)
    self.assertIn('DRAFT-TODO', p.stdout)

  def test_strict_with_level_must_ignores_should_findings(self):
    p = run('bg_validate.py', '--repo', self.repo, '--strict', '--level',
            'MUST')
    self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

  def test_strict_passes_when_there_are_no_findings(self):
    self.finish_draft()
    p = run('bg_validate.py', '--repo', self.repo, '--strict')
    self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

  def test_non_strict_run_still_exits_zero_with_should_findings(self):
    self.assertEqual(run('bg_validate.py', '--repo', self.repo).returncode, 0)

  def test_yaml_parse_error_is_a_must_finding(self):
    self.edit(lambda t: t.replace('name: Churn Rate',
                                  'name: Churn: Rate: [unclosed'))
    p, rep = self.report()
    found = [v for v in rep['violations'] if v['rule'] == 'YAML-01']
    self.assertEqual(len(found), 1, rep['violations'])
    self.assertEqual(found[0]['level'], 'MUST')
    self.assertEqual(found[0]['term'], 'churn-rate')
    self.assertEqual(rep['tiers']['churn-rate'], 'Below')
    strict = run('bg_validate.py', '--repo', self.repo, '--strict',
                 '--level', 'MUST')
    self.assertNotEqual(strict.returncode, 0)
    self.assertIn('YAML-01', strict.stdout)

  def test_term_without_frontmatter_is_a_must_finding(self):
    self.edit(lambda t: t.split('---\n', 2)[2])
    _, rep = self.report()
    self.assertIn('YAML-01', [v['rule'] for v in rep['violations']])


def _today():
  import datetime
  return datetime.date.today().isoformat()


if __name__ == '__main__':
  unittest.main()
