"""bg_draft status: a drafted term is always Draft and never carries
approval fields, whatever the repo profile's template or agent_status says.
A profile is a repo file an agent can edit, so it cannot grant approval.

All content is synthetic.
Run: python3 -m unittest tests.test_bg_draft_status
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

CANDIDATES = """\
candidates:
- id: alpha-widget
  name: Alpha Widget
  definition: A synthetic widget for the draft status test.
  links: []
  sources: ['folder:notes.md']
  confidentiality: public
  exists: false
"""


def run(script, *args):
  return subprocess.run([sys.executable, os.path.join(SCRIPTS, script)] +
                        list(args), capture_output=True, text=True)


class DraftStatus(unittest.TestCase):
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

  def test_tampered_profile_template_still_drafts_draft(self):
    prof = os.path.join(self.repo, 'rules', 'profile.yaml')
    with open(prof, encoding='utf-8') as fh:
      text = fh.read()
    for old in ('agent_status: Draft\n', '  status: Draft\n'):
      self.assertIn(old, text)
    text = text.replace('agent_status: Draft\n', 'agent_status: Approved\n')
    text = text.replace('  status: Draft\n',
                        "  status: Approved\n"
                        "  approved_by: someone\n"
                        "  approved_on: '2026-01-01'\n"
                        "  approved_version: '1.0.0'\n")
    with open(prof, 'w', encoding='utf-8') as fh:
      fh.write(text)
    p = run('bg_draft.py', '--repo', self.repo, '--ids', 'alpha-widget')
    self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
    fm = read_term(os.path.join(self.repo, 'terms',
                                'alpha-widget.md'))['fm']
    self.assertEqual(fm['status'], 'Draft')
    for k in ('approved_by', 'approved_on', 'approved_version'):
      self.assertNotIn(k, fm)


if __name__ == '__main__':
  unittest.main(verbosity=2)
