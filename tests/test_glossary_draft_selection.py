"""`bg_draft` candidate selection: a candidate vetoed with `accept: false`
is never drafted by `--top`, and the veto does not eat one of the N slots.
`--accepted` still drafts only candidates marked `accept: true`.

All content is synthetic.
Run: python3 -m unittest tests.test_glossary_draft_selection
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

CANDIDATES = """\
candidates:
- id: beta-widget
  name: Beta Widget
  definition: A synthetic widget the user vetoed.
  links: []
  sources: ['folder:notes.md']
  confidentiality: public
  exists: false
  accept: false
- id: alpha-widget
  name: Alpha Widget
  definition: A synthetic widget for the selection test.
  links: []
  sources: ['folder:notes.md']
  confidentiality: public
  exists: false
  accept: null
- id: gamma-widget
  name: Gamma Widget
  definition: Another synthetic widget for the selection test.
  links: []
  sources: ['folder:notes.md']
  confidentiality: public
  exists: false
  accept: true
"""


def run(script, *args):
  return subprocess.run([sys.executable, os.path.join(SCRIPTS, script)] +
                        list(args), capture_output=True, text=True)


class DraftSelection(unittest.TestCase):
  def setUp(self):
    self.tmp = tempfile.mkdtemp()
    self.repo = os.path.join(self.tmp, 'g')
    made = run('bg_init.py', self.repo, '--name', 'Synthetic Glossary')
    self.assertEqual(made.returncode, 0, made.stdout + made.stderr)
    with open(os.path.join(self.repo, '.glossary', 'candidates.yaml'), 'w',
              encoding='utf-8') as fh:
      fh.write(CANDIDATES)

  def tearDown(self):
    shutil.rmtree(self.tmp)

  def drafted(self):
    folder = os.path.join(self.repo, 'terms')
    return sorted(name[:-3] for name in os.listdir(folder)
                  if name.endswith('.md'))

  def test_top_skips_a_vetoed_candidate(self):
    out = run('bg_draft.py', '--repo', self.repo, '--top', '5')
    self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
    self.assertEqual(self.drafted(), ['alpha-widget', 'gamma-widget'])
    self.assertIn('skip (accept: false): beta-widget', out.stdout)

  def test_vetoed_candidate_does_not_take_a_top_slot(self):
    out = run('bg_draft.py', '--repo', self.repo, '--top', '2')
    self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
    self.assertEqual(self.drafted(), ['alpha-widget', 'gamma-widget'])

  def test_accepted_drafts_only_marked_candidates(self):
    out = run('bg_draft.py', '--repo', self.repo, '--accepted')
    self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
    self.assertEqual(self.drafted(), ['gamma-widget'])


if __name__ == '__main__':
  unittest.main()
