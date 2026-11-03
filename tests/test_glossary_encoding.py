"""Input encoding in the business glossary: a source that is not UTF-8 is
named and rejected, never decoded with replacement characters or skipped.
UTF-16 with a byte order mark is detected and read correctly.

All content is synthetic.
Run: python3 -m unittest tests.test_glossary_encoding
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
from bg_core import load_yaml  # noqa: E402

GOOD = ('---\ntitle: Ünïcode Widget\n---\n\n# Ünïcode Widget\n\n'
        'A synthetic widget with accents in its description text.\n')
CSV = 'term;definition\nZażółć Test;A synthetic Polish test definition.\n'


def run(script, *args):
  return subprocess.run([sys.executable, os.path.join(SCRIPTS, script)] +
                        list(args), capture_output=True, text=True)


class Encoding(unittest.TestCase):
  def setUp(self):
    self.tmp = tempfile.mkdtemp()
    self.src = os.path.join(self.tmp, 'src')
    os.makedirs(self.src)
    self.repo = os.path.join(self.tmp, 'g')
    p = run('bg_init.py', self.repo, '--name', 'Enc')
    self.assertEqual(p.returncode, 0, p.stderr)

  def tearDown(self):
    shutil.rmtree(self.tmp)

  def put(self, name, data):
    with open(os.path.join(self.src, name), 'wb') as fh:
      fh.write(data)

  def discover(self, kind='folder'):
    return run('bg_discover.py', '--repo', self.repo, '--source',
               '%s:%s' % (kind, self.src))

  def candidates_path(self):
    return os.path.join(self.repo, '.glossary', 'candidates.yaml')

  def assert_rejected(self, p, filename):
    self.assertNotEqual(p.returncode, 0, p.stdout + p.stderr)
    self.assertIn(filename, p.stdout + p.stderr)
    self.assertNotIn('Traceback', p.stderr)
    self.assertFalse(os.path.exists(self.candidates_path()))

  def test_latin1_note_is_rejected_with_file_name(self):
    self.put('ok.md', GOOD.encode('utf-8'))
    self.put('old.md', GOOD.encode('latin-1'))
    p = self.discover()
    self.assert_rejected(p, 'old.md')
    self.assertIn('UTF-8', p.stdout + p.stderr)

  def test_utf16_without_bom_is_rejected(self):
    self.put('wide.md', GOOD.encode('utf-16-le'))
    self.assert_rejected(self.discover(), 'wide.md')

  def test_binary_note_is_rejected(self):
    self.put('blob.md', bytes(range(256)) * 4)
    self.assert_rejected(self.discover(), 'blob.md')

  def test_utf16_with_bom_is_decoded(self):
    self.put('wide.md', GOOD.encode('utf-16'))
    p = self.discover()
    self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
    cands = load_yaml(self.candidates_path())['candidates']
    self.assertEqual([c['name'] for c in cands], ['Ünïcode Widget'])
    with open(self.candidates_path(), encoding='utf-8') as fh:
      self.assertNotIn('\ufffd', fh.read())

  def test_utf8_bom_is_accepted(self):
    self.put('bom.md', b'\xef\xbb\xbf' + GOOD.encode('utf-8'))
    p = self.discover()
    self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
    cands = load_yaml(self.candidates_path())['candidates']
    self.assertEqual([c['name'] for c in cands], ['Ünïcode Widget'])

  def test_csv_in_latin1_is_rejected(self):
    self.put('t.csv', CSV.encode('latin-1', errors='replace')
             .replace(b'?', b'\xf3'))
    self.assert_rejected(self.discover('csv'), 't.csv')

  def test_csv_in_utf16_with_bom_is_decoded(self):
    self.put('t.csv', CSV.encode('utf-16'))
    p = self.discover('csv')
    self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
    cands = load_yaml(self.candidates_path())['candidates']
    self.assertEqual([c['name'] for c in cands], ['Zażółć Test'])

  def test_corrupt_office_files_are_rejected(self):
    self.put('bad.docx', b'this is not a zip archive at all')
    self.assert_rejected(self.discover('docx'), 'bad.docx')

  def test_corrupt_xlsx_is_rejected(self):
    self.put('bad.xlsx', b'this is not a zip archive at all')
    self.assert_rejected(self.discover('xlsx'), 'bad.xlsx')

  def test_term_file_that_is_not_utf8_is_rejected(self):
    self.put('ok.md', GOOD.encode('utf-8'))
    self.assertEqual(self.discover().returncode, 0)
    run('bg_draft.py', '--repo', self.repo, '--top', '5')
    term = 'unicode-widget.md'
    path = os.path.join(self.repo, 'terms', term)
    self.assertTrue(os.path.isfile(path))
    with open(path, 'rb') as fh:
      data = fh.read()
    with open(path, 'wb') as fh:
      fh.write(data.replace(b'Description', b'Descr\xe9ption', 1))
    p = run('bg_validate.py', '--repo', self.repo)
    self.assertNotEqual(p.returncode, 0)
    self.assertIn(term, p.stdout + p.stderr)
    self.assertNotIn('Traceback', p.stderr)


if __name__ == '__main__':
  unittest.main()
