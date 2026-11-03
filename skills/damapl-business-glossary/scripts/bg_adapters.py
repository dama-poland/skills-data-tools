"""Source adapters: turn a knowledge-base source into candidate terms.

Every adapter yields dicts:
  name, definition, aliases[], type_hint, links[], tags[], bullets[],
  source (adapter kind), source_ref (path or url), text (note body),
  confidentiality (frontmatter value or None), source_id (or None)
Add an adapter by writing a function and registering it in ADAPTERS.
The `folder` adapter is the fallback for any unknown kind.
"""

import codecs
import csv
import html.parser
import io
import os
import re
import zipfile
import xml.etree.ElementTree as ET

import yaml

from bg_core import name_key

TEXT_EXT = ('.md', '.markdown', '.txt', '.rst')
WIKILINK = re.compile(r'\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]')
DEF_LINE = re.compile(
  r'^\s*(?:[-*]\s+)?(?:\*\*|__)?([A-Z][\w /&()\'-]{1,60}?)(?:\*\*|__)?'
  r'\s*(?::|\u2013|\u2014| - )\s+(.{15,400})$')
SKIP_DIRS = {'.git', '.obsidian', '.trash', 'node_modules', '__pycache__',
             '.graphify', '.glossary'}
# Labels that open a `Label: text` line but are not terms.
LABELS = frozenset((
  'note notes status owner author date source sources tags tag type '
  'version created updated modified reviewed example examples see todo '
  'warning tip summary description purpose context scope question answer '
  'reference references link links contact priority department team '
  'title abstract caveat important remark comment comments reviewer '
  'approver revision changelog history').split()) | {'see also'}
# Headings and page furniture that name a section, not a concept.
GENERIC_NAMES = frozenset((
  'overview', 'introduction', 'summary', 'contents', 'table of contents',
  'references', 'appendix', 'notes', 'navigation', 'changelog', 'history',
  'agenda', 'background', 'description', 'resources', 'related pages',
  'see also', 'faq', 'links', 'glossary', 'terms', 'definitions'))
BOILERPLATE = re.compile(
  r'(?i)^(table of contents|contents\b|on this page|skip to |go to (the )?'
  r'(start|end) of|created by|last (modified|updated|edited|reviewed)|'
  r'modified by|updated by|powered by|page (id|history|tree|info)\b|'
  r'breadcrumbs?\b|back to\b|navigation\b|related (pages|articles|content)'
  r'|see also\b|labels?:|attachments?\b|no labels|\d+ comments?|was this '
  r'(page|article) helpful|copyright|all rights reserved|todo\b|tbd\b|'
  r'lorem ipsum|home\b.{0,3}$)')
LINKS_ONLY = re.compile(
  r'\[\[.*?\]\]|!?\[[^\]]*\]\([^)]*\)|https?://\S+')
CRUMB_SEP = re.compile(r'\s(?:>|\u00bb|\u203a|\||/)\s|\s?\u00bb\s?')
HEADING_STYLE = re.compile(r'(?i)^(heading|title|nag[\u0142l]owek)')
TYPE_HINTS = (
  ('Role', r'\b(role|owner|manager|lead|steward|officer|persona)\b'),
  ('Event', r'\b(event|happened|occurs|when a|triggered)\b'),
  ('Metric', r'\b(metric|rate|ratio|score|kpi|count of|percentage)\b'),
  ('Process', r'\b(process|workflow|procedure|activity|steps?)\b'),
  ('Record', r'\b(record|document|report|log|row|message)\b'),
  ('Component', r'\b(service|system|application|api|database|platform)\b'),
)


class SourceError(Exception):
  """A source file cannot be read; the message names the file."""


def read_source_text(path):
  """Read a text source as UTF-8 (or UTF-16 with a byte order mark).
  Anything else raises SourceError; nothing is decoded with replacement
  characters and no file is skipped silently."""
  try:
    with open(path, 'rb') as fh:
      data = fh.read()
  except OSError as exc:
    raise SourceError('cannot read %s: %s' % (path, exc.strerror or exc))
  if data.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
    enc = 'utf-16'
  elif b'\x00' in data:
    raise SourceError(
      'cannot read %s: contains NUL bytes (binary file, or UTF-16 without '
      'a byte order mark); save it as UTF-8' % path)
  else:
    enc = 'utf-8-sig'
  try:
    return data.decode(enc)
  except UnicodeDecodeError as exc:
    raise SourceError(
      'cannot read %s: not valid %s (byte %d); save it as UTF-8' % (
        path, 'UTF-16' if enc == 'utf-16' else 'UTF-8', exc.start))


def guess_type(text):
  t = re.split(r'(?<=[.!?])\s', text.strip())[0].lower()
  for name, pat in TYPE_HINTS:
    if re.search(pat, t):
      return name
  return 'Concept'


def is_boilerplate(text):
  """True for navigation, breadcrumbs, page metadata and placeholders:
  text that must never be taken as a definition."""
  t = ' '.join(str(text).split())
  if not t or BOILERPLATE.match(re.sub(r'^[^\w\[]+', '', t)):
    return True
  if not re.search(r'\w{2,}', re.sub(r'\[\[.*?\]\]', '', LINKS_ONLY.sub(
      ' ', t)).replace('|', ' ')):
    return True  # nothing left once the links are taken out
  if len(CRUMB_SEP.findall(t)) >= 2 and not re.search(r'[.!?]\s*$', t):
    return True
  return False


def is_generic_name(name):
  return name_key(name) in GENERIC_NAMES


def title_from_filename(path):
  b = os.path.splitext(os.path.basename(path))[0]
  b = re.sub(r'^\d{4}-\d{2}-\d{2}[ _-]*', '', b)
  return re.sub(r'[_]+', ' ', b).strip()


def first_paragraph(body):
  """First prose paragraph. Heading lines inside a paragraph are dropped,
  navigation and boilerplate paragraphs are skipped."""
  body = re.sub(r'```.*?```', '', body, flags=re.S)
  for para in re.split(r'\n\s*\n', body.strip()):
    p = '\n'.join(x for x in para.split('\n')
                  if not x.lstrip().startswith('#')).strip()
    if not p or p.startswith(('|', '---', '![', '>')):
      continue
    if re.match(r'^[-*]\s', p) or p.startswith('<'):
      continue
    p = re.sub(r'\s+', ' ', p)
    if is_boilerplate(p):
      continue
    return p
  return ''


def bullets_of(body):
  return [re.sub(r'^[-*]\s+', '', ln.strip()) for ln in body.split('\n')
          if re.match(r'^\s*[-*]\s+\S', ln)][:8]


def _walk(root, exts):
  if os.path.isfile(root):
    yield root
    return
  for dp, dns, fns in os.walk(root):
    dns[:] = sorted(d for d in dns if d not in SKIP_DIRS)
    for fn in sorted(fns):
      if fn.lower().endswith(exts) and not fn.startswith('.'):
        yield os.path.join(dp, fn)


def _split_fm(text):
  m = re.match(r'\A---\n(.*?)\n---\n?(.*)\Z', text, re.S)
  if not m:
    return {}, text
  try:
    fm = yaml.safe_load(m.group(1)) or {}
  except yaml.YAMLError:
    fm = {}
  return (fm if isinstance(fm, dict) else {}), m.group(2)


def _list(v):
  if v is None:
    return []
  return [str(x) for x in (v if isinstance(v, list) else [v])]


def note_candidate(path, text, kind, root=None):
  fm, body = _split_fm(text)
  h1 = re.search(r'^#\s+(.+)$', body, re.M)
  name = str(fm.get('title') or fm.get('name') or
             (h1.group(1).strip() if h1 else title_from_filename(path)))
  defn = str(fm.get('definition') or fm.get('summary') or
             fm.get('description') or '') or first_paragraph(
               re.sub(r'^#\s+.+$', '', body, count=1, flags=re.M))
  tags = [t.lstrip('#') for t in _list(fm.get('tags'))]
  tags += re.findall(r'(?<![\w/])#([A-Za-z][\w/-]+)', body)[:5]
  return {
    'name': name.strip(), 'definition': defn, 'source': kind,
    'aliases': _list(fm.get('aliases') or fm.get('alias')),
    'type_hint': str(fm.get('type') or '') or guess_type(defn),
    'links': sorted({x.strip() for x in WIKILINK.findall(body)}),
    'tags': sorted(set(tags)), 'bullets': bullets_of(body),
    'source_ref': os.path.relpath(path, root) if root else path,
    'text': body, 'confidentiality': fm.get('confidentiality'),
    'source_id': fm.get('source_id'),
  }


def a_obsidian(path, opts):
  """Obsidian vault: one note = one candidate; wikilinks become links."""
  root = path if os.path.isdir(path) else os.path.dirname(path)
  min_chars = int(opts.get('min_chars', 0))
  for f in _walk(path, ('.md', '.markdown')):
    text = read_source_text(f)
    c = note_candidate(f, text, 'obsidian', root)
    rel = os.path.relpath(f, root)
    gl = is_glossary_note(rel, c['name'])
    if not gl and len(c['text']) >= min_chars and c['name']:
      yield c
    yield from inline_defs(rel, text, 'obsidian', gl)


def _prose_lines(text):
  """Lines of a note without its frontmatter and fenced code blocks."""
  body = _split_fm(text)[1] if text.startswith('---\n') else text
  out, fence = [], False
  for ln in body.split('\n'):
    if ln.lstrip().startswith('```'):
      fence = not fence
      out.append('')
    else:
      out.append('' if fence else ln)
  return out


def _def_match(lines, i):
  if not 0 <= i < len(lines):
    return None
  m = DEF_LINE.match(lines[i])
  return m if m and m.group(1).strip().lower() not in LABELS else None


TABLE_SEP = re.compile(r'^\s*\|?[\s:|-]*-[\s:|-]*\|?\s*$')
TABLE_HEADS = frozenset((
  'term', 'name', 'concept', 'word', 'abbreviation', 'acronym', 'title',
  'termin', 'pojęcie', 'nazwa'))


def inline_defs(rel, text, kind, force):
  """`**Term**: definition` lines and glossary table rows inside a note.
  In glossary-like notes (`force`) a plain `Term: text` line also counts,
  but only as a list item or inside a block of two or more such lines, so
  a lone `Note: ...` sentence is not a term; label words (Note, Status,
  Owner...) never are. Frontmatter and code fences are not scanned. Each
  candidate inherits the note's confidentiality and source_id."""
  fm = _split_fm(text)[0]
  meta = {'confidentiality': fm.get('confidentiality'),
          'source_id': fm.get('source_id')}
  lines = _prose_lines(text)
  for i, ln in enumerate(lines):
    m = _def_match(lines, i)
    if m:
      bold = '**' in ln or '__' in ln
      listed = re.match(r'\s*[-*]\s', ln)
      block = _def_match(lines, i - 1) or _def_match(lines, i + 1)
      if bold or (force and (listed or block)):
        yield dict(meta, **{
          'name': m.group(1).strip(), 'definition': m.group(2).strip(),
          'source': kind, 'aliases': [], 'links': [], 'tags': [],
          'bullets': [], 'type_hint': guess_type(m.group(2)),
          'source_ref': rel, 'text': ''})
    row = [x.strip() for x in ln.strip().strip('|').split('|')]
    nxt = lines[i + 1] if i + 1 < len(lines) else ''
    if ln.strip().startswith('|') and len(row) >= 2 and force and \
        row[0] and not set(row[0]) <= set('-: ') and \
        row[0].lower() not in TABLE_HEADS and not TABLE_SEP.match(nxt):
      yield dict(meta, **{
        'name': row[0].strip('*_ '), 'definition': row[1],
        'source': kind, 'aliases': [], 'links': [], 'tags': [],
        'bullets': [], 'type_hint': guess_type(row[1]),
        'source_ref': rel, 'text': ''})


def is_glossary_note(rel, name):
  return bool(re.search(r'(?i)glossary|terms|definitions', rel + name))


def a_folder(path, opts):
  """Plain folder of notes. Notes become candidates; `Term: definition`
  lines and glossary tables inside notes yield extra candidates."""
  root = path if os.path.isdir(path) else os.path.dirname(path)
  for f in _walk(path, TEXT_EXT):
    text = read_source_text(f)
    rel = os.path.relpath(f, root)
    c = note_candidate(f, text, 'folder', root)
    gl = is_glossary_note(rel, c['name'])
    if not gl:
      yield c
    yield from inline_defs(rel, text, 'folder', gl)


def _row_candidate(row, kind, ref):
  low = {str(k).strip().lower(): v for k, v in row.items() if k}

  def pick(*keys):
    for k in keys:
      if low.get(k) not in (None, ''):
        return str(low[k]).strip()
    return ''
  name = pick('term', 'name', 'title', 'term name')
  if not name:
    return None
  defn = pick('definition', 'description', 'meaning', 'summary')
  return {
    'name': name, 'definition': defn, 'source': kind, 'source_ref': ref,
    'aliases': [x.strip() for x in re.split(
      r'[;,|]', pick('aliases', 'synonyms', 'alternative names',
                     'alternative_names')) if x.strip()],
    'type_hint': pick('type', 'category') or guess_type(defn),
    'links': [], 'tags': [], 'bullets': [], 'text': '',
    'name_pl': pick('name_pl', 'polish', 'termin'),
    'definition_pl': pick('definition_pl', 'definicja'),
  }


def a_csv(path, opts):
  for f in _walk(path, ('.csv', '.tsv')):
    text = read_source_text(f)
    sample = text[:4096]
    delim = '\t' if f.endswith('.tsv') else (
      ';' if sample.count(';') > sample.count(',') else ',')
    reader = csv.DictReader(io.StringIO(text, newline=''), delimiter=delim)
    for i, row in enumerate(reader, 2):
      c = _row_candidate(row, 'csv', '%s:%d' % (os.path.basename(f), i))
      if c:
        yield c


def _xlsx_rows(path):
  ns = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
  with zipfile.ZipFile(path) as z:
    shared = []
    if 'xl/sharedStrings.xml' in z.namelist():
      root = ET.fromstring(z.read('xl/sharedStrings.xml'))
      for si in root.findall('m:si', ns):
        shared.append(''.join(t.text or '' for t in si.iter(
          '{%s}t' % ns['m'])))
    sheet = sorted(n for n in z.namelist()
                   if n.startswith('xl/worksheets/sheet'))[0]
    root = ET.fromstring(z.read(sheet))
    for row in root.iter('{%s}row' % ns['m']):
      cells = {}
      for c in row.findall('m:c', ns):
        col = re.match(r'[A-Z]+', c.get('r')).group(0)
        v = c.find('m:v', ns)
        if c.get('t') == 's' and v is not None:
          val = shared[int(v.text)]
        elif c.get('t') == 'inlineStr':
          val = ''.join(t.text or '' for t in c.iter('{%s}t' % ns['m']))
        else:
          val = v.text if v is not None else ''
        cells[col] = val
      yield cells


def a_xlsx(path, opts):
  for f in _walk(path, ('.xlsx',)):
    try:
      rows = list(_xlsx_rows(f))
    except (zipfile.BadZipFile, KeyError, IndexError, ET.ParseError) as exc:
      raise SourceError('cannot read %s: not a valid .xlsx file (%s)' % (
        f, exc))
    if not rows:
      continue
    cols = sorted(rows[0], key=lambda c: (len(c), c))
    head = {c: rows[0][c] for c in cols}
    for i, r in enumerate(rows[1:], 2):
      row = {head[c]: r.get(c, '') for c in cols}
      c = _row_candidate(row, 'xlsx', '%s:%d' % (os.path.basename(f), i))
      if c:
        yield c


class _Page(html.parser.HTMLParser):
  """Text of an HTML page split into headings and paragraphs. Navigation,
  breadcrumbs, page metadata, scripts and styles are dropped. Each
  paragraph records how many h1 headings came before it."""
  VOID = frozenset(('br', 'hr', 'img', 'input', 'link', 'meta', 'col',
                    'area', 'base', 'source', 'wbr'))
  DROP_TAGS = frozenset(('script', 'style', 'nav', 'header', 'footer',
                         'aside', 'noscript', 'template'))
  DROP_ATTR = re.compile(r'(?i)breadcrumb|sidebar|navigation|\bnav\b|'
                         r'footer|metadata|\btoc\b|page-labels|comment')
  BLOCKS = frozenset(('p', 'li', 'td', 'th', 'tr', 'div', 'section', 'ul',
                      'ol', 'table', 'blockquote', 'pre', 'article'))
  HEADS = ('h1', 'h2', 'h3', 'h4', 'h5', 'h6')

  def __init__(self):
    super().__init__()
    self.title, self.headings, self.paras = '', [], []
    self.stack, self.cur, self.head = [], [], None
    self.h1_seen, self.in_title = 0, False

  def _dropped(self):
    return any(d for _, d in self.stack)

  def _flush(self):
    text = ' '.join(''.join(self.cur).split())
    self.cur = []
    if text and not self._dropped():
      self.paras.append((self.h1_seen, text))

  def handle_starttag(self, tag, attrs):
    if tag in self.VOID:
      return
    a = dict(attrs)
    drop = tag in self.DROP_TAGS or bool(self.DROP_ATTR.search(
      '%s %s' % (a.get('class') or '', a.get('id') or '')))
    if tag in self.BLOCKS or tag in self.HEADS:
      self._flush()
    self.stack.append((tag, drop))
    if tag == 'title':
      self.in_title = True
    elif tag in self.HEADS and not self._dropped():
      self.head = (int(tag[1]), [])
      if tag == 'h1':
        self.h1_seen += 1

  def handle_endtag(self, tag):
    if tag in self.VOID or not any(t == tag for t, _ in self.stack):
      return
    if tag in self.BLOCKS and self.head is None:
      self._flush()
    while self.stack:
      t, _ = self.stack.pop()
      if t == tag:
        break
    if tag == 'title':
      self.in_title = False
    elif self.head and tag == 'h%d' % self.head[0]:
      text = ' '.join(''.join(self.head[1]).split())
      if text:
        self.headings.append((self.head[0], text))
      self.head = None

  def handle_data(self, data):
    if self.in_title:
      self.title += data
    elif self._dropped():
      return
    elif self.head is not None:
      self.head[1].append(data)
    else:
      self.cur.append(data)

  def close(self):
    super().close()
    self._flush()


def a_confluence(path, opts):
  """Confluence HTML export folder: first h1 (else <title>, first heading,
  file name) = term, first prose paragraph after it = definition.
  Navigation, breadcrumbs, metadata and boilerplate are skipped."""
  root = path if os.path.isdir(path) else os.path.dirname(path)
  for f in _walk(path, ('.html', '.htm')):
    p = _Page()
    p.feed(read_source_text(f))
    p.close()
    h1 = next((t for lvl, t in p.headings if lvl == 1), '')
    first = p.headings[0][1] if p.headings else ''
    name = (h1 or p.title.strip() or first or title_from_filename(f)).strip()
    name = re.sub(r'^.*? : ', '', ' '.join(name.split()))
    if not name or name.lower() in ('index', 'home'):
      continue
    heads = {t.lower() for _, t in p.headings}
    anchor = 1 if h1 else 0
    paras = [t for seen, t in p.paras
             if seen >= anchor and len(t) > 25 and t.lower() not in heads
             and not is_boilerplate(t)]
    defn = paras[0] if paras else ''
    yield {'name': name, 'definition': defn, 'source': 'confluence',
           'aliases': [], 'type_hint': guess_type(defn), 'links': [],
           'tags': [], 'bullets': paras[1:5],
           'source_ref': os.path.relpath(f, root), 'text': ' '.join(paras)}


def a_docx(path, opts):
  """Word documents: `Term: definition` paragraphs, plus the first title or
  heading (else the first paragraph) as one candidate whose definition is
  the first body paragraph. Heading paragraphs are never definitions."""
  w = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
  for f in _walk(path, ('.docx',)):
    try:
      with zipfile.ZipFile(f) as z:
        root = ET.fromstring(z.read('word/document.xml'))
    except (zipfile.BadZipFile, KeyError, ET.ParseError) as exc:
      raise SourceError('cannot read %s: not a valid .docx file (%s)' % (
        f, exc))
    paras = []  # (is_heading, text)
    for p in root.iter(w + 'p'):
      text = ''.join(t.text or '' for t in p.iter(w + 't')).strip()
      style = p.find('%spPr/%spStyle' % (w, w))
      val = style.get(w + 'val') if style is not None else ''
      if text:
        paras.append((bool(HEADING_STYLE.match(val or '')), text))
    if not paras:
      continue
    ref = os.path.basename(f)
    for is_head, ln in paras:
      m = DEF_LINE.match(ln)
      if m and not is_head and m.group(1).strip().lower() not in LABELS:
        yield {'name': m.group(1).strip(), 'definition': m.group(2).strip(),
               'source': 'docx', 'aliases': [], 'links': [], 'tags': [],
               'bullets': [], 'type_hint': guess_type(m.group(2)),
               'source_ref': ref, 'text': ''}
    i = next((k for k, (h, _) in enumerate(paras) if h), 0)
    body = [t for k, (h, t) in enumerate(paras)
            if k != i and not h and len(t) > 25 and not is_boilerplate(t)
            and not (DEF_LINE.match(t) and DEF_LINE.match(t).group(
              1).strip().lower() in LABELS)]
    yield {'name': paras[i][1][:80], 'definition': body[0] if body else '',
           'source': 'docx', 'aliases': [], 'links': [], 'tags': [],
           'bullets': body[1:4], 'type_hint': guess_type(' '.join(body)),
           'source_ref': ref, 'text': ' '.join(t for _, t in paras)}


ADAPTERS = {
  'obsidian': a_obsidian, 'folder': a_folder, 'csv': a_csv, 'tsv': a_csv,
  'xlsx': a_xlsx, 'confluence': a_confluence, 'docx': a_docx,
}
KIND_HELP = {
  'obsidian': 'Obsidian vault (wikilinks, aliases, tags)',
  'folder': 'plain folder of .md/.txt notes (fallback for anything else)',
  'csv': 'CSV/TSV with a term/name and definition column',
  'xlsx': 'Excel sheet 1 with a term/name and definition column',
  'confluence': 'Confluence HTML export folder',
  'docx': 'Word documents (Term: definition lines, first heading)',
}


def run_adapter(kind, path, opts=None):
  fn = ADAPTERS.get(kind, a_folder)
  return list(fn(os.path.expanduser(path), opts or {}))


def detect_kind(path):
  p = os.path.expanduser(path)
  if os.path.isdir(p) and os.path.isdir(os.path.join(p, '.obsidian')):
    return 'obsidian'
  ext = os.path.splitext(p)[1].lower()
  if ext in ('.csv', '.tsv'):
    return 'csv'
  if ext == '.xlsx':
    return 'xlsx'
  if ext == '.docx':
    return 'docx'
  if os.path.isdir(p):
    for _, _, fns in os.walk(p):
      if any(x.endswith(('.html', '.htm')) for x in fns):
        return 'confluence'
      break
  return 'folder'
