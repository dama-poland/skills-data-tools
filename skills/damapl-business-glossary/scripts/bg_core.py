"""Shared core for the business-glossary skill (PyYAML + stdlib only).

Term files are Markdown with YAML frontmatter. The repo is canonical; all
other outputs are derived views. Edits to existing files are surgical:
only the touched frontmatter block or body section changes.
"""

import datetime
import difflib
import os
import re
import sys

try:
  import yaml
except ImportError:  # pragma: no cover
  sys.exit('PyYAML is required: pip install pyyaml')

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILES_DIR = os.path.join(SKILL_DIR, 'assets', 'profiles')
CONFIG_NAME = 'glossary.yaml'
FM_RE = re.compile(r'\A---\n(.*?)\n---\n?(.*)\Z', re.S)
SLUG_RE = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')
REL_KEYS = ('is_a', 'has_a', 'values', 'realized_by', 'implemented_by')
# Lowest to highest. A source without a classification counts as
# UNCLASSIFIED; an unknown value counts as the highest (fail-safe).
CLASSIFICATIONS = ('public', 'internal', 'restricted')
UNCLASSIFIED = 'internal'


def today():
  return datetime.date.today().isoformat()


def slugify(text):
  s = re.sub(r'\(.*?\)', ' ', text.lower())
  s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
  return s


def normalize_classification(value):
  """Map a confidentiality value to one of CLASSIFICATIONS."""
  if value is None or str(value).strip() == '':
    return UNCLASSIFIED
  v = str(value).strip().lower()
  return v if v in CLASSIFICATIONS else CLASSIFICATIONS[-1]


def highest_classification(values):
  """Highest classification among `values` (UNCLASSIFIED when empty)."""
  ranks = [CLASSIFICATIONS.index(normalize_classification(v))
           for v in values]
  return CLASSIFICATIONS[max(ranks)] if ranks else UNCLASSIFIED


def source_ref_of(cand):
  """Stable reference of a raw candidate: its source_id, else kind:path."""
  if cand.get('source_id'):
    return str(cand['source_id'])
  return '%s:%s' % (cand['source'], cand['source_ref'])


def section_key(title):
  return re.sub(r'[^a-z0-9]+', '_', title.lower()).strip('_')


def load_yaml(path):
  with open(path, encoding='utf-8') as fh:
    return yaml.safe_load(fh) or {}


def dump_yaml(obj):
  return yaml.safe_dump(
    obj, sort_keys=False, allow_unicode=True, default_flow_style=False,
    width=78)


def find_repo(start=None):
  d = os.path.abspath(start or os.getcwd())
  while True:
    if os.path.isfile(os.path.join(d, CONFIG_NAME)):
      return d
    parent = os.path.dirname(d)
    if parent == d:
      return None
    d = parent


def load_config(repo):
  cfg = load_yaml(os.path.join(repo, CONFIG_NAME))
  cfg.setdefault('languages', ['en'])
  cfg.setdefault('terms_dir', 'terms')
  cfg.setdefault('profile', 'rules/profile.yaml')
  cfg.setdefault('profile_options', {})
  return cfg


def load_profile(repo, cfg):
  path = os.path.join(repo, cfg['profile'])
  if not os.path.isfile(path):
    name = os.path.basename(cfg['profile'])
    path = os.path.join(PROFILES_DIR, name)
  prof = load_yaml(path)
  opts = dict(prof.get('options') or {})
  opts.update(cfg.get('profile_options') or {})
  prof['options'] = opts
  return prof


def split_term(text):
  """Return (frontmatter_text, body_text)."""
  m = FM_RE.match(text)
  if not m:
    return '', text
  return m.group(1), m.group(2)


def parse_body(body):
  """Return (title, definition, sections{key: text}, titles{key: title})."""
  lines = body.split('\n')
  title = ''
  i = 0
  while i < len(lines) and not lines[i].strip():
    i += 1
  if i < len(lines) and lines[i].startswith('# '):
    title = lines[i][2:].strip()
    i += 1
  defn, sections, titles, cur = [], {}, {}, None
  fence = False
  for ln in lines[i:]:
    if ln.lstrip().startswith('```'):
      fence = not fence
    if not fence and ln.startswith('## '):
      cur = section_key(ln[3:])
      titles[cur] = ln[3:].strip()
      sections[cur] = []
      continue
    (defn if cur is None else sections[cur]).append(ln)
  return (title, '\n'.join(defn).strip(),
          {k: '\n'.join(v).strip() for k, v in sections.items()}, titles)


def read_term(path):
  with open(path, encoding='utf-8') as fh:
    text = fh.read()
  fm_text, body = split_term(text)
  try:
    fm = yaml.safe_load(fm_text) or {}
  except yaml.YAMLError as exc:
    fm = {'_parse_error': str(exc)}
  if not isinstance(fm, dict):
    fm = {'_parse_error': 'frontmatter is not a mapping'}
  title, defn, sections, titles = parse_body(body)
  return {
    'id': fm.get('id'), 'fm': fm, 'path': path, 'text': text,
    'body': body, 'title': title, 'definition': defn,
    'sections': sections, 'titles': titles,
  }


def terms_dir(repo, cfg):
  return os.path.join(repo, cfg['terms_dir'])


def load_terms(repo, cfg):
  d = terms_dir(repo, cfg)
  out = []
  if not os.path.isdir(d):
    return out
  for name in sorted(os.listdir(d)):
    if name.endswith('.md') and not name.startswith('_'):
      out.append(read_term(os.path.join(d, name)))
  return out


def as_list(v):
  if v is None or v == '':
    return []
  return v if isinstance(v, list) else [v]


def rel_targets(fm):
  rels = fm.get('relations') or {}
  out = {}
  for k in REL_KEYS:
    out[k] = [x for x in as_list(rels.get(k))]
  return out


# --- surgical frontmatter editing -------------------------------------

def _block_span(lines, key):
  """Return (start, end) line span of top-level `key:` block, or None."""
  pat = re.compile(r'^' + re.escape(key) + r':(\s|$)')
  for i, ln in enumerate(lines):
    if pat.match(ln):
      j = i + 1
      while j < len(lines) and (
          lines[j].startswith((' ', '\t', '- ')) or not lines[j].strip()):
        j += 1
      while j > i + 1 and not lines[j - 1].strip():
        j -= 1
      return i, j
  return None


def set_fm_field(text, key, value):
  """Replace or insert one top-level frontmatter field; touch nothing else."""
  m = FM_RE.match(text)
  if not m:
    raise ValueError('no frontmatter')
  lines = m.group(1).split('\n')
  new = dump_yaml({key: value}).rstrip('\n').split('\n')
  span = _block_span(lines, key)
  if span and span[1] - span[0] == 1 and isinstance(value, str) and \
      '\n' not in value and '"' not in value and "'" not in value:
    old = lines[span[0]].split(':', 1)[1].strip()
    if old[:1] in ('"', "'"):  # keep the file's quote style
      new = ['%s: %s%s%s' % (key, old[0], value, old[0])]
  if span:
    lines[span[0]:span[1]] = new
  else:
    lines.extend(new)
  return '---\n' + '\n'.join(lines) + '\n---\n' + m.group(2)


def set_section(text, title, content):
  """Replace the body of `## title` (append the section if missing)."""
  m = FM_RE.match(text)
  head, body = ('', text) if not m else (text[:m.start(2)], m.group(2))
  lines = body.split('\n')
  want = section_key(title)
  start = None
  fence = False
  for i, ln in enumerate(lines):
    if ln.lstrip().startswith('```'):
      fence = not fence
    if not fence and ln.startswith('## ') and section_key(ln[3:]) == want:
      start = i
      break
  block = ['## ' + title, ''] + content.strip('\n').split('\n') + ['']
  if start is None:
    while lines and not lines[-1].strip():
      lines.pop()
    lines += [''] + block
  else:
    end = len(lines)
    fence = False
    for j in range(start + 1, len(lines)):
      if lines[j].lstrip().startswith('```'):
        fence = not fence
      if not fence and lines[j].startswith('## '):
        end = j
        break
    lines[start:end] = block
  return head + '\n'.join(lines).rstrip('\n') + '\n'


def set_definition(text, content):
  """Replace the definition paragraph(s) between H1 and first H2."""
  m = FM_RE.match(text)
  head, body = ('', text) if not m else (text[:m.start(2)], m.group(2))
  lines = body.split('\n')
  i = 0
  while i < len(lines) and not lines[i].strip():
    i += 1
  if i < len(lines) and lines[i].startswith('# '):
    i += 1
  j = i
  while j < len(lines) and not lines[j].startswith('## '):
    j += 1
  lines[i:j] = [''] + content.strip().split('\n') + ['']
  return head + '\n'.join(lines).rstrip('\n') + '\n'


def unified(old, new, path):
  return ''.join(difflib.unified_diff(
    old.splitlines(True), new.splitlines(True),
    'a/' + path, 'b/' + path))


def write_text(path, text, dry=False):
  if dry:
    return
  os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
  with open(path, 'w', encoding='utf-8') as fh:
    fh.write(text)


def split_sentences(text):
  t = re.sub(r'\s+', ' ', text.strip())
  if not t:
    return []
  parts = re.split(r'(?<=[.!?])\s+(?=[A-Z0-9"\'(])', t)
  return [p for p in parts if p]


def bump_version(version, level):
  a, b, c = (int(x) for x in str(version).split('.'))
  if level == 'a':
    return '%d.0.0' % (a + 1)
  if level == 'b':
    return '%d.%d.0' % (a, b + 1)
  return '%d.%d.%d' % (a, b, c + 1)


def default_author(cfg):
  d = (cfg.get('defaults') or {})
  return (os.environ.get('BG_AUTHOR') or d.get('author')
          or os.environ.get('USER', 'unknown'))


def common_args(ap):
  ap.add_argument('--repo', default=None,
                  help='glossary repo root (default: search upward)')
  ap.add_argument('--dry-run', action='store_true',
                  help='show what would change; write nothing')


def need_repo(args):
  repo = find_repo(args.repo)
  if not repo:
    sys.exit('no %s found; run bg_init.py first' % CONFIG_NAME)
  return repo


def bump_text(text, level, author, prof=None, today_s=None):
  """Bump version (+version_date, changed_by) surgically. Approved terms
  edited at level a/b return to Under Review when the profile says so."""
  fm_text, _ = split_term(text)
  fm = yaml.safe_load(fm_text) or {}
  if 'version' not in fm:
    return text
  text = set_fm_field(text, 'version', bump_version(fm['version'], level))
  if 'version_date' in fm:
    text = set_fm_field(text, 'version_date', today_s or today())
  if 'changed_by' in fm:
    text = set_fm_field(text, 'changed_by', author)
  if (prof and prof.get('approval_reset') and level in ('a', 'b')
      and fm.get('status') == 'Approved'):
    text = set_fm_field(text, 'status', 'Under Review')
  return text
