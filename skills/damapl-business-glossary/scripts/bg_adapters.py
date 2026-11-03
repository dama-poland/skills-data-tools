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

TEXT_EXT = ('.md', '.markdown', '.txt', '.rst')
WIKILINK = re.compile(r'\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]')
DEF_LINE = re.compile(
  r'^\s*(?:[-*]\s+)?(?:\*\*|__)?([A-Z][\w /&()\'-]{1,60}?)(?:\*\*|__)?'
  r'\s*(?::|\u2013|\u2014| - )\s+(.{15,400})$')
SKIP_DIRS = {'.git', '.obsidian', '.trash', 'node_modules', '__pycache__',
             '.graphify', '.glossary'}
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


def title_from_filename(path):
  b = os.path.splitext(os.path.basename(path))[0]
  b = re.sub(r'^\d{4}-\d{2}-\d{2}[ _-]*', '', b)
  return re.sub(r'[_]+', ' ', b).strip()


def first_paragraph(body):
  for para in re.split(r'\n\s*\n', body.strip()):
    p = para.strip()
    if not p or p.startswith(('#', '```', '|', '---', '![', '>')):
      continue
    if re.match(r'^[-*]\s', p) or p.startswith('<'):
      continue
    return re.sub(r'\s+', ' ', p)
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


def inline_defs(rel, text, kind, force):
  """`**Term**: definition` lines and glossary table rows inside a note.
  Plain `Term: text` lines only count in glossary-like notes (`force`).
  Each candidate inherits the note's confidentiality and source_id."""
  fm = _split_fm(text)[0]
  meta = {'confidentiality': fm.get('confidentiality'),
          'source_id': fm.get('source_id')}
  for ln in text.split('\n'):
    m = DEF_LINE.match(ln)
    if m and (force or '**' in ln):
      yield dict(meta, **{
        'name': m.group(1).strip(), 'definition': m.group(2).strip(),
        'source': kind, 'aliases': [], 'links': [], 'tags': [],
        'bullets': [], 'type_hint': guess_type(m.group(2)),
        'source_ref': rel, 'text': ''})
    row = [x.strip() for x in ln.strip().strip('|').split('|')]
    if ln.strip().startswith('|') and len(row) >= 2 and force and \
        row[0] and not set(row[0]) <= set('-: ') and \
        row[0].lower() not in ('term', 'name'):
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


class _Text(html.parser.HTMLParser):
  def __init__(self):
    super().__init__()
    self.title, self.paras, self.cur, self.tag = '', [], [], None
    self.h1 = ''

  def handle_starttag(self, tag, attrs):
    self.tag = tag

  def handle_endtag(self, tag):
    if tag in ('p', 'li') and self.cur:
      self.paras.append(' '.join(''.join(self.cur).split()))
      self.cur = []
    self.tag = None

  def handle_data(self, data):
    if self.tag == 'title':
      self.title += data
    elif self.tag == 'h1':
      self.h1 += data
    elif self.tag in ('p', 'li', 'span', 'strong', 'em', 'a', 'td', None):
      self.cur.append(data)


def a_confluence(path, opts):
  """Confluence HTML export folder: page title = term, first paragraph =
  definition. Sidebar/breadcrumb boilerplate is skipped by length."""
  root = path if os.path.isdir(path) else os.path.dirname(path)
  for f in _walk(path, ('.html', '.htm')):
    raw = read_source_text(f)
    p = _Text()
    p.feed(raw)
    name = (p.h1 or p.title).strip()
    name = re.sub(r'^.*? : ', '', name)
    paras = [x for x in p.paras if len(x) > 25]
    if not name or name.lower() in ('index', 'home'):
      continue
    defn = paras[0] if paras else ''
    yield {'name': name, 'definition': defn, 'source': 'confluence',
           'aliases': [], 'type_hint': guess_type(defn), 'links': [],
           'tags': [], 'bullets': paras[1:5],
           'source_ref': os.path.relpath(f, root), 'text': ' '.join(paras)}


def a_docx(path, opts):
  w = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
  for f in _walk(path, ('.docx',)):
    try:
      with zipfile.ZipFile(f) as z:
        root = ET.fromstring(z.read('word/document.xml'))
    except (zipfile.BadZipFile, KeyError, ET.ParseError) as exc:
      raise SourceError('cannot read %s: not a valid .docx file (%s)' % (
        f, exc))
    paras = [''.join(t.text or '' for t in p.iter(w + 't'))
             for p in root.iter(w + 'p')]
    paras = [x.strip() for x in paras if x.strip()]
    for ln in paras:
      m = DEF_LINE.match(ln)
      if m:
        yield {'name': m.group(1).strip(), 'definition': m.group(2).strip(),
               'source': 'docx', 'aliases': [], 'links': [], 'tags': [],
               'bullets': [], 'type_hint': guess_type(m.group(2)),
               'source_ref': os.path.basename(f), 'text': ''}
    if paras:
      body = [x for x in paras[1:] if len(x) > 25]
      yield {'name': paras[0][:80], 'definition': body[0] if body else '',
             'source': 'docx', 'aliases': [], 'links': [], 'tags': [],
             'bullets': body[1:4], 'type_hint': guess_type(' '.join(body)),
             'source_ref': os.path.basename(f), 'text': ' '.join(paras)}


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
