"""Source adapters of the business glossary: headings, navigation and
boilerplate never become definitions, a Confluence page with several h1
headings or no <title> still gets a sound name, and plain `Word: text`
lines in a glossary note are not all terms.

All content is synthetic.
Run: python3 -m unittest tests.test_glossary_adapters
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), 'skills',
                       'damapl-business-glossary', 'scripts')
sys.path.insert(0, SCRIPTS)
from bg_adapters import run_adapter  # noqa: E402
from bg_core import load_yaml  # noqa: E402

CHURN = 'Churn is the share of customers who stop buying in a period.'


class Case(unittest.TestCase):
  def setUp(self):
    self.tmp = tempfile.mkdtemp()

  def tearDown(self):
    shutil.rmtree(self.tmp)

  def put(self, name, text):
    path = os.path.join(self.tmp, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
      fh.write(text)
    return path

  def cands(self, kind):
    return run_adapter(kind, self.tmp)

  def by_name(self, kind):
    return {c['name']: c for c in self.cands(kind)}


class Markdown(Case):
  def test_text_right_under_a_heading_is_the_definition(self):
    self.put('Churn.md', '# Churn\n%s\n' % CHURN)
    for kind in ('obsidian', 'folder'):
      self.assertEqual(self.by_name(kind)['Churn']['definition'], CHURN)

  def test_section_heading_is_never_the_definition(self):
    self.put('Churn.md', '# Churn\n## Overview\n%s\n' % CHURN)
    for kind in ('obsidian', 'folder'):
      self.assertEqual(self.by_name(kind)['Churn']['definition'], CHURN)
    self.put('Only.md', '# Only Heading\n\n## Section about something\n')
    self.assertEqual(self.by_name('folder')['Only Heading']['definition'], '')

  def test_navigation_and_boilerplate_paragraphs_are_skipped(self):
    for i, first in enumerate((
        '[[Home]] | [[Glossary]] | [[Index]]',
        '\u00ab Back to [[Glossary]]',
        'Home > Glossary > Metrics > Churn',
        '[Up](../index.md)',
        'Table of contents',
        'Last updated by the data team on 2026-01-01',
        'TODO')):
      self.put('n%d.md' % i, '# Navtest %d\n\n%s\n\n%s\n' % (i, first, CHURN))
    for kind in ('obsidian', 'folder'):
      got = self.by_name(kind)
      for i in range(7):
        self.assertEqual(got['Navtest %d' % i]['definition'], CHURN,
                         (kind, i))

  def test_second_h1_is_not_used_as_name_or_definition(self):
    self.put('Churn.md', '# Churn\n\n%s\n\n# Related pages\n\n'
             'A longer paragraph that belongs to the second section.\n'
             % CHURN)
    got = self.by_name('obsidian')
    self.assertEqual(list(got), ['Churn'])
    self.assertEqual(got['Churn']['definition'], CHURN)


GLOSSARY = """# Glossary

Note: this glossary is maintained by the data team every quarter.
Status: Draft version of the glossary that is open for review now.
Owner: Data Governance team, reachable through the usual channel.

- **Churn**: The share of customers who stop buying in a period.
- Retention: The share of customers who keep buying in a period.

Revenue: Money received from customers for products in a period.

Margin: Revenue left after the direct costs of the products sold.
Backlog: The ordered list of work items that the team plans to do.

| Concept | Meaning |
|---------|---------|
| Cohort | A group of customers that joined in the same period. |
"""


class GlossaryNotes(Case):
  def test_plain_label_lines_are_not_terms(self):
    self.put('Glossary.md', GLOSSARY)
    for kind in ('obsidian', 'folder'):
      names = set(self.by_name(kind))
      for label in ('Note', 'Status', 'Owner'):
        self.assertNotIn(label, names, (kind, label))
      self.assertIn('Churn', names)
      self.assertIn('Retention', names)

  def test_lone_plain_line_is_not_a_term_but_a_block_is(self):
    self.put('Glossary.md', GLOSSARY)
    names = set(self.by_name('folder'))
    self.assertNotIn('Revenue', names)
    self.assertIn('Margin', names)
    self.assertIn('Backlog', names)

  def test_table_header_row_is_not_a_term(self):
    self.put('Glossary.md', GLOSSARY)
    names = set(self.by_name('folder'))
    self.assertIn('Cohort', names)
    self.assertNotIn('Concept', names)

  def test_frontmatter_and_code_fences_are_not_scanned(self):
    self.put('Glossary.md', '---\nTitle: Some synthetic glossary file here\n'
             'Owner: Somebody who maintains this synthetic file\n---\n'
             '# Glossary\n\n```\nSample: a line inside a code block fence\n'
             'Other: another line inside the same code block fence\n```\n'
             '\n- **Churn**: %s\n' % CHURN)
    self.assertEqual(set(self.by_name('folder')), {'Churn'})


def page(body, title=None, head=''):
  t = '<title>%s</title>' % title if title is not None else ''
  return '<html><head>%s%s</head><body>%s</body></html>' % (head, t, body)


class Confluence(Case):
  def test_multiple_h1_use_the_first_one_as_name(self):
    self.put('a.html', page(
      '<h1>Customer Churn</h1><p>%s</p><h1>Related pages</h1>'
      '<p>A longer paragraph that belongs to the second section.</p>'
      % CHURN))
    got = self.by_name('confluence')
    self.assertEqual(list(got), ['Customer Churn'])
    self.assertEqual(got['Customer Churn']['definition'], CHURN)

  def test_breadcrumbs_and_navigation_are_not_definitions(self):
    self.put('a.html', page(
      '<nav><ul><li>Home and the whole glossary space overview page</li>'
      '</ul></nav><div id="breadcrumb-section"><ol><li><a href="x">'
      'Glossary of all the terms used by the team</a></li></ol></div>'
      '<div class="page-metadata">Created by Alice, last modified on '
      'Monday</div><h1>Churn</h1><p>Skip to end of metadata and go on '
      'with reading</p><p>%s</p>' % CHURN, title='Space : Churn'))
    got = self.by_name('confluence')
    self.assertEqual(got['Churn']['definition'], CHURN)

  def test_section_headings_with_inline_markup_are_not_definitions(self):
    self.put('a.html', page(
      '<h1><span id="t"> Space : Churn</span></h1>'
      '<h2><span>Overview of the measurement approach used</span></h2>'
      '<p>%s</p>' % CHURN))
    got = self.by_name('confluence')
    self.assertEqual(got['Churn']['definition'], CHURN)

  def test_page_without_title_uses_first_heading_then_filename(self):
    self.put('one.html', page('<h2>Retention Rate</h2><p>%s</p>' % CHURN))
    self.put('Customer Lifetime.html', page('<p>%s</p>' % CHURN))
    self.put('index.html', page('<p>%s</p>' % CHURN))
    names = set(self.by_name('confluence'))
    self.assertEqual(names, {'Retention Rate', 'Customer Lifetime'})


def docx(path, paras):
  w = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
  body = ''
  for style, text in paras:
    ppr = '<w:pPr><w:pStyle w:val="%s"/></w:pPr>' % style if style else ''
    body += '<w:p>%s<w:r><w:t>%s</w:t></w:r></w:p>' % (ppr, text)
  xml = ('<?xml version="1.0"?><w:document xmlns:w="%s"><w:body>%s'
         '</w:body></w:document>' % (w, body))
  with zipfile.ZipFile(path, 'w') as z:
    z.writestr('word/document.xml', xml)


class Docx(Case):
  def test_headings_are_not_definitions_and_notes_are_not_terms(self):
    docx(os.path.join(self.tmp, 'c.docx'), [
      ('Title', 'Customer Churn'),
      ('Heading1', 'A long section heading about how churn is measured'),
      (None, 'Note: this text is only a remark for the reader of it.'),
      (None, CHURN)])
    got = self.by_name('docx')
    self.assertEqual(list(got), ['Customer Churn'])
    self.assertEqual(got['Customer Churn']['definition'], CHURN)


class DiscoverRanking(Case):
  def test_generic_headings_are_ranked_below_real_terms(self):
    for name in ('Introduction', 'Zebra Metric'):
      self.put('%s.md' % name, '# %s\n\n%s\n' % (name, CHURN))
    repo = os.path.join(self.tmp, 'g')
    for args in ((os.path.join(SCRIPTS, 'bg_init.py'), repo, '--name', 'R'),
                 (os.path.join(SCRIPTS, 'bg_discover.py'), '--repo', repo,
                  '--source', 'folder:' + self.tmp)):
      p = subprocess.run([sys.executable] + list(args),
                         capture_output=True, text=True)
      self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
    cands = load_yaml(os.path.join(
      repo, '.glossary', 'candidates.yaml'))['candidates']
    self.assertEqual([c['id'] for c in cands],
                     ['zebra-metric', 'introduction'])


if __name__ == '__main__':
  unittest.main()
