"""bg_update.py guards: ids, bump fields, approval fields and status are
protected in every patch op (set, add, remove). Changing status needs
--allow-status plus the human-only signal DAMAPL_HUMAN_APPROVAL=1.

Run: python3 -m unittest tests.test_bg_update_guards  (needs PyYAML).
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
from bg_core import read_term  # noqa: E402

TERM = '''---
id: sample-term
name: Sample Term
type: Concept
acronyms: []
alternative_names: []
status: Draft
source_origin: synthetic
created_by: test-author
created: '2026-01-01'
related_terms: []
relations: {}
last_reviewed: null
version: '1.0.0'
version_date: '2026-01-01'
changed_by: test-author
approved_version: null
approved_by: null
approved_on: null
---

# Sample Term

A synthetic term used only by the bg_update guard tests.

## Description Details

Synthetic.

## What it is

- synthetic
'''


def human_env(approval=None):
  env = {k: v for k, v in os.environ.items() if k != 'DAMAPL_HUMAN_APPROVAL'}
  if approval is not None:
    env['DAMAPL_HUMAN_APPROVAL'] = approval
  return env


class BgUpdateGuards(unittest.TestCase):
  def setUp(self):
    self.tmp = tempfile.mkdtemp()
    self.repo = os.path.join(self.tmp, 'g')
    p = subprocess.run([sys.executable, os.path.join(SCRIPTS, 'bg_init.py'),
                        self.repo, '--name', 'Guards'],
                       capture_output=True, text=True)
    self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
    self.path = os.path.join(self.repo, 'terms', 'sample-term.md')
    with open(self.path, 'w', encoding='utf-8') as fh:
      fh.write(TERM)

  def tearDown(self):
    shutil.rmtree(self.tmp)

  def patch(self, body, *extra, approval=None):
    pfile = os.path.join(self.tmp, 'p.yaml')
    with open(pfile, 'w', encoding='utf-8') as fh:
      fh.write('- id: sample-term\n' + body)
    return subprocess.run(
      [sys.executable, os.path.join(SCRIPTS, 'bg_update.py'),
       '--repo', self.repo, '--patch', pfile] + list(extra),
      capture_output=True, text=True, env=human_env(approval))

  def assert_refused(self, body, *extra, approval=None, word=None):
    p = self.patch(body, *extra, approval=approval)
    self.assertNotEqual(p.returncode, 0, p.stdout + p.stderr)
    if word:
      self.assertIn(word, p.stdout + p.stderr)
    with open(self.path, encoding='utf-8') as fh:
      self.assertEqual(fh.read(), TERM)

  def test_remove_id_is_refused(self):
    self.assert_refused('  remove: {id: [x]}\n', word='immutable')
    self.assert_refused('  remove: {id: [sample-term]}\n', word='immutable')

  def test_add_id_and_created_fields_are_refused(self):
    self.assert_refused('  add: {id: [other]}\n', word='immutable')
    self.assert_refused('  remove: {created_by: [test-author]}\n',
                        word='immutable')
    self.assert_refused('  add: {created: ["2026-02-02"]}\n',
                        word='immutable')

  def test_bump_fields_are_refused_in_add_and_remove(self):
    self.assert_refused('  add: {version: ["9.9.9"]}\n', word='bump')
    self.assert_refused('  remove: {changed_by: [test-author]}\n',
                        word='bump')

  def test_add_status_approved_is_refused(self):
    self.assert_refused('  add: {status: [Approved]}\n', word='status')

  def test_remove_status_is_refused(self):
    self.assert_refused('  remove: {status: [Draft]}\n', word='status')

  def test_set_status_approved_without_flag_is_refused(self):
    self.assert_refused('  set: {status: Approved}\n', word='status')

  def test_allow_status_without_human_signal_is_refused(self):
    self.assert_refused('  set: {status: Under Review}\n', '--allow-status',
                        word='DAMAPL_HUMAN_APPROVAL')
    self.assert_refused('  set: {status: Under Review}\n', '--allow-status',
                        approval='yes', word='DAMAPL_HUMAN_APPROVAL')

  def test_allow_status_with_human_signal_sets_status(self):
    p = self.patch('  set: {status: Under Review}\n', '--allow-status',
                   approval='1')
    self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
    t = read_term(self.path)
    self.assertEqual(t['fm']['status'], 'Under Review')
    self.assertEqual(t['fm']['version'], '1.1.0')

  def test_approval_fields_are_always_refused(self):
    for op in ('set: {approved_by: someone}',
               'set: {approved_on: "2026-02-02"}',
               'set: {approved_version: "1.0.0"}',
               'add: {approved_by: [someone]}',
               'remove: {approved_version: ["1.0.0"]}'):
      with self.subTest(op=op):
        self.assert_refused('  %s\n' % op, word='approv')
        self.assert_refused('  %s\n' % op, '--allow-status', approval='1',
                            word='approv')

  def tamper_profile(self, agent_status):
    prof = os.path.join(self.repo, 'rules', 'profile.yaml')
    with open(prof, encoding='utf-8') as fh:
      text = fh.read()
    self.assertIn('agent_status: Draft\n', text)
    with open(prof, 'w', encoding='utf-8') as fh:
      fh.write(text.replace('agent_status: Draft\n',
                            'agent_status: %s\n' % agent_status))

  def test_profile_agent_status_cannot_unlock_approved(self):
    self.tamper_profile('Approved')
    self.assert_refused('  set: {status: Approved}\n', word='agent_status')
    self.assert_refused('  set: {category: Sales}\n', word='agent_status')

  def test_profile_agent_status_is_refused_for_bump_only(self):
    self.tamper_profile('Approved')
    p = subprocess.run(
      [sys.executable, os.path.join(SCRIPTS, 'bg_update.py'),
       '--repo', self.repo, '--bump-only', 'sample-term'],
      capture_output=True, text=True, env=human_env())
    self.assertNotEqual(p.returncode, 0, p.stdout + p.stderr)
    self.assertIn('agent_status', p.stdout + p.stderr)
    with open(self.path, encoding='utf-8') as fh:
      self.assertEqual(fh.read(), TERM)

  def test_draft_status_and_plain_fields_still_work(self):
    p = self.patch('  set: {status: Draft, category: Sales}\n'
                   '  add: {alternative_names: [Example Term]}\n')
    self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
    t = read_term(self.path)
    self.assertEqual(t['fm']['category'], 'Sales')
    self.assertEqual(t['fm']['alternative_names'], ['Example Term'])
    self.assertEqual(t['fm']['status'], 'Draft')


if __name__ == '__main__':
  unittest.main(verbosity=2)
