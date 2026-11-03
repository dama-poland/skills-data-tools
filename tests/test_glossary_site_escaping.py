"""bg_site output is safe to open and to import: the repo name is escaped in
<title>, concordance links allow only http(s) urls, and CSV cells that start
with = + - @ are neutralised. All names and urls are synthetic.
Run: python3 -m unittest tests.test_glossary_site_escaping
"""

import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), 'skills',
                       'damapl-business-glossary', 'scripts')

TERM = '''---
id: %(id)s
name: "%(name)s"
type: Concept
status: Draft
confidentiality: public
definition_note: synthetic
concordance:
  - url: "https://example.org/ok"
    label: "Good source"
  - url: "http://example.org/plain"
    label: "Plain http"
  - url: "javascript:alert(1)"
    label: "Script source"
  - url: "  JaVaScRiPt:alert(2)"
    label: "Padded script source"
  - url: "data:text/html;base64,AAAA"
    label: "Data source"
  - url: "//example.org/relative"
    label: "Protocol relative"
---

# %(name)s

%(definition)s
'''

TERMS = [
  {'id': 'formula-term', 'name': '=SUM(A1:A2)',
   'definition': '+cmd synthetic definition that starts with a plus sign.'},
  {'id': 'minus-term', 'name': '-minus name',
   'definition': '@mention synthetic definition that starts with an at sign.'},
  {'id': 'plain-term', 'name': 'Plain Term',
   'definition': 'A synthetic definition with a hyphen - inside and = too.'},
]


def run(script, *args):
  p = subprocess.run([sys.executable, os.path.join(SCRIPTS, script)] +
                     list(args), capture_output=True, text=True)
  if p.returncode != 0:
    raise AssertionError('%s failed:\n%s%s' % (script, p.stdout, p.stderr))
  return p


class SiteEscaping(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.tmp = tempfile.mkdtemp()
    cls.repo = os.path.join(cls.tmp, 'g')
    cls.name = 'Synthetic </title><script>alert(1)</script> & "Co"'
    run('bg_init.py', cls.repo, '--name', cls.name)
    for t in TERMS:
      with open(os.path.join(cls.repo, 'terms', t['id'] + '.md'), 'w',
                encoding='utf-8') as fh:
        fh.write(TERM % t)
    run('bg_site.py', '--repo', cls.repo)
    cls.out = os.path.join(cls.repo, 'generated')

  @classmethod
  def tearDownClass(cls):
    shutil.rmtree(cls.tmp)

  def read(self, rel):
    with open(os.path.join(self.out, rel), encoding='utf-8') as fh:
      return fh.read()

  def test_title_is_escaped(self):
    html = self.read('site/index.html')
    title = re.search(r'<title>(.*?)</title>', html, re.S).group(1)
    self.assertNotIn('<', title)
    self.assertNotIn('"', title)
    self.assertIn('&lt;/title&gt;&lt;script&gt;', title)
    self.assertIn('&amp;', title)
    self.assertEqual(html.count('<title>'), 1)

  def test_title_in_data_is_still_the_plain_name(self):
    data = json.loads(self.read('terms.json'))
    self.assertEqual(data['title'], self.name)

  def test_only_http_and_https_concordance_urls_survive(self):
    data = json.loads(self.read('terms.json'))
    for term in data['terms']:
      urls = [c['url'] for c in term['concordance'] if c['url']]
      self.assertEqual(urls, ['https://example.org/ok',
                              'http://example.org/plain'])
      for c in term['concordance']:
        if c['url']:
          self.assertTrue(re.match(r'https?://', c['url']), c['url'])

  def test_labels_of_dropped_urls_stay_as_plain_text(self):
    data = json.loads(self.read('terms.json'))
    labels = [c['label'] for c in data['terms'][0]['concordance']]
    self.assertEqual(labels, ['Good source', 'Plain http', 'Script source',
                              'Padded script source', 'Data source',
                              'Protocol relative'])
    self.assertEqual([c['url'] for c in data['terms'][0]['concordance']
                      if c['label'] == 'Script source'], [''])

  def test_template_guards_the_href_too(self):
    tpl = os.path.join(os.path.dirname(SCRIPTS), 'assets',
                       'site_template.html')
    with open(tpl, encoding='utf-8') as fh:
      text = fh.read()
    self.assertIn('https?:', text)

  def test_no_script_url_in_any_output(self):
    for rel in ('terms.json', 'site/index.html', 'glossary.csv', 'a-z.md'):
      text = self.read(rel).lower()
      self.assertNotIn('javascript:', text, rel)
      self.assertNotIn('data:text/html', text, rel)

  def test_csv_cells_starting_with_formula_characters_are_neutralised(self):
    with open(os.path.join(self.out, 'glossary.csv'), encoding='utf-8',
              newline='') as fh:
      rows = list(csv.DictReader(fh))
    by_id = {r['id']: r for r in rows}
    self.assertEqual(by_id['formula-term']['name'], "'=SUM(A1:A2)")
    self.assertEqual(by_id['formula-term']['definition'][:2], "'+")
    self.assertEqual(by_id['minus-term']['name'], "'-minus name")
    self.assertEqual(by_id['minus-term']['definition'][:2], "'@")
    for row in rows:
      for value in row.values():
        self.assertFalse(value[:1] in ('=', '+', '-', '@', '\t', '\r'),
                         value)

  def test_csv_leaves_ordinary_cells_unchanged(self):
    with open(os.path.join(self.out, 'glossary.csv'), encoding='utf-8',
              newline='') as fh:
      rows = {r['id']: r for r in csv.DictReader(fh)}
    plain = rows['plain-term']
    self.assertEqual(plain['name'], 'Plain Term')
    self.assertTrue(plain['definition'].startswith('A synthetic definition'))


if __name__ == '__main__':
  unittest.main()
