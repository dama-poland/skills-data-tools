"""A glossary repo made by bg_init is portable: the committed Makefile and
glossary.yaml hold no absolute skill path and no user name or email. The skill
path lives in .glossary/local.mk (gitignored); the author is resolved when a
term is written. All names are synthetic.
Run: python3 -m unittest tests.test_glossary_portability
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.join(os.path.dirname(HERE), 'skills',
                     'damapl-business-glossary')
SCRIPTS = os.path.join(SKILL, 'scripts')
sys.path.insert(0, SCRIPTS)
from bg_core import default_author, load_yaml  # noqa: E402

USER = 'synthetic-login'
EMAIL = 'synthetic.person@example.org'


def read(*parts):
  with open(os.path.join(*parts), encoding='utf-8') as fh:
    return fh.read()


class Portable(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.tmp = tempfile.mkdtemp()
    cls.gitconfig = os.path.join(cls.tmp, 'gitconfig')
    with open(cls.gitconfig, 'w', encoding='utf-8') as fh:
      fh.write('[user]\n\temail = %s\n' % EMAIL)
    cls.env = dict(os.environ, USER=USER, GIT_CONFIG_GLOBAL=cls.gitconfig,
                   GIT_CONFIG_NOSYSTEM='1')
    cls.env.pop('BG_AUTHOR', None)
    cls.repo = os.path.join(cls.tmp, 'g')
    p = subprocess.run(
      [sys.executable, os.path.join(SCRIPTS, 'bg_init.py'), cls.repo,
       '--name', 'Portable'], capture_output=True, text=True, env=cls.env)
    assert p.returncode == 0, p.stdout + p.stderr

  @classmethod
  def tearDownClass(cls):
    shutil.rmtree(cls.tmp)

  def test_makefile_has_no_absolute_path_or_user(self):
    text = read(self.repo, 'Makefile')
    self.assertNotIn(SKILL, text)
    self.assertNotIn(os.path.expanduser('~'), text)
    self.assertNotIn(USER, text)
    self.assertNotIn('/Users', text)
    self.assertIn('-include .glossary/local.mk', text)

  def test_config_has_no_absolute_path_user_or_email(self):
    text = read(self.repo, 'glossary.yaml')
    for word in (SKILL, USER, EMAIL, '@'):
      self.assertNotIn(word, text)
    self.assertNotIn('author', load_yaml(
      os.path.join(self.repo, 'glossary.yaml')).get('defaults') or {})

  def test_skill_path_lives_in_a_gitignored_local_file(self):
    self.assertIn(SCRIPTS, read(self.repo, '.glossary', 'local.mk'))
    self.assertIn('.glossary/local.mk',
                  read(self.repo, '.gitignore').splitlines())

  @unittest.skipUnless(shutil.which('make'), 'make is not installed')
  def test_make_uses_the_local_file(self):
    p = subprocess.run(['make', '-n', 'validate'], cwd=self.repo,
                       capture_output=True, text=True)
    self.assertEqual(p.returncode, 0, p.stderr)
    self.assertIn(os.path.join(SCRIPTS, 'bg_validate.py'), p.stdout)

  @unittest.skipUnless(shutil.which('make'), 'make is not installed')
  def test_make_without_local_file_explains_what_to_set(self):
    copy = os.path.join(self.tmp, 'copy')
    shutil.copytree(self.repo, copy)
    os.remove(os.path.join(copy, '.glossary', 'local.mk'))
    p = subprocess.run(['make', '-n', 'validate'], cwd=copy,
                       capture_output=True, text=True)
    self.assertNotEqual(p.returncode, 0)
    self.assertIn('SK', p.stderr)
    ok = subprocess.run(['make', '-n', 'validate', 'SK=/x/scripts'],
                        cwd=copy, capture_output=True, text=True)
    self.assertEqual(ok.returncode, 0, ok.stderr)
    self.assertIn('/x/scripts/bg_validate.py', ok.stdout)

  def test_author_is_resolved_when_a_term_is_written(self):
    cfg = load_yaml(os.path.join(self.repo, 'glossary.yaml'))
    # Run outside any checkout so a local git user.email cannot leak in.
    cwd = os.getcwd()
    os.chdir(self.tmp)
    self.addCleanup(os.chdir, cwd)
    with mock.patch.dict(os.environ, self.env, clear=True):
      self.assertEqual(default_author(cfg), EMAIL)
    with mock.patch.dict(os.environ, dict(self.env, BG_AUTHOR='Named Person'),
                         clear=True):
      self.assertEqual(default_author(cfg), 'Named Person')
    with mock.patch.dict(os.environ, dict(
        self.env, GIT_CONFIG_GLOBAL=os.devnull), clear=True):
      self.assertEqual(default_author(cfg), USER)

  def test_configured_author_beats_git_and_user(self):
    cfg = {'defaults': {'author': 'Configured Steward'}}
    with mock.patch.dict(os.environ, self.env, clear=True):
      self.assertEqual(default_author(cfg), 'Configured Steward')

  def test_init_keeps_an_explicit_bg_author(self):
    repo = os.path.join(self.tmp, 'h')
    p = subprocess.run(
      [sys.executable, os.path.join(SCRIPTS, 'bg_init.py'), repo],
      capture_output=True, text=True, env=dict(self.env, BG_AUTHOR='Chosen'))
    self.assertEqual(p.returncode, 0, p.stderr)
    self.assertEqual(load_yaml(os.path.join(repo, 'glossary.yaml'))[
      'defaults']['author'], 'Chosen')


if __name__ == '__main__':
  unittest.main()
