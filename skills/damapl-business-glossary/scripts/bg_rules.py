"""Pluggable rule engine. Rules live in a YAML profile, not in code.

A rule names a built-in `check` plus params. Add a profile to change the
rule set; add a check function here only for a genuinely new test kind.
"""

import datetime
import re

from bg_core import REL_KEYS, as_list, rel_targets, split_sentences

SMALL = {'a', 'an', 'and', 'as', 'at', 'by', 'for', 'in', 'of', 'on', 'or',
         'the', 'to', 'vs', 'with', 'per', 'via'}
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def _val(t, field):
  fm = t['fm']
  if field in fm:
    return fm[field]
  if field == 'definition':
    return t['definition']
  return t['sections'].get(field)


def _empty(v):
  return v is None or v == '' or v == [] or v == {}


def fmt(s, opts):
  try:
    return s.format(**opts)
  except (KeyError, IndexError):
    return s


# --- term-scope checks: fn(t, ctx, p) -> list of messages --------------

def c_required(t, ctx, p):
  out = []
  for f in as_list(p.get('fields', p.get('field'))):
    if _empty(_val(t, f)):
      out.append('missing or empty `%s`' % f)
  return out


def c_regex(t, ctx, p):
  v = _val(t, p['field'])
  if _empty(v):
    return [] if p.get('optional') else ['`%s` is empty' % p['field']]
  pat = fmt(p['pattern'], ctx['opts'])
  bad = [x for x in as_list(v) if not re.search(pat, str(x))]
  return ['`%s` does not match %s' % (p['field'], pat)] if bad else []


def c_enum(t, ctx, p):
  v = _val(t, p['field'])
  allowed = p.get('values') or ctx['profile'].get(p.get('values_from'), [])
  if _empty(v):
    return ['`%s` is empty' % p['field']]
  return [] if v in allowed else [
    '`%s` = %r not in %s' % (p['field'], v, allowed)]


def c_sentence_max(t, ctx, p):
  v = _val(t, p.get('field', 'definition')) or ''
  n = len(split_sentences(v))
  return ['%d sentences, max %d' % (n, p['max'])] if n > p['max'] else []


def c_not_circular(t, ctx, p):
  d = (t['definition'] or '').strip()
  name = re.sub(r'\s*\(.*?\)', '', str(t['fm'].get('name', ''))).strip()
  if name and re.match(
      r'(?i)^(an?\s+|the\s+)?' + re.escape(name) +
      r's?\s+(is|are|means|refers to)\b', d):
    return ['definition opens with "%s is..."' % name]
  return []


def c_no_leading(t, ctx, p):
  v = (_val(t, p.get('field', 'definition')) or '').strip()
  return ['definition is stated by exclusion'] if re.match(
    p.get('pattern', r'(?i)^not\b'), v) else []


def c_section_nonempty(t, ctx, p):
  out = []
  for s in as_list(p['section']):
    if not t['sections'].get(s, '').strip():
      out.append('section `%s` missing or empty' % s)
  return out


def c_bullets_min(t, ctx, p):
  txt = t['sections'].get(p['section'], '')
  n = len([x for x in txt.split('\n') if x.lstrip().startswith(('- ', '* '))])
  return ['section `%s` has %d bullets, min %d' % (
    p['section'], n, p['min'])] if n < p['min'] else []


def c_filename_id(t, ctx, p):
  import os
  base = os.path.basename(t['path'])[:-3]
  return [] if base == t['fm'].get('id') else [
    'file name %s.md != id %r' % (base, t['fm'].get('id'))]


def c_title_case(t, ctx, p):
  name = re.sub(r'\(.*?\)', '', str(t['fm'].get('name', '')))
  for i, w in enumerate(name.split()):
    core = re.sub(r'^[^A-Za-z0-9]+', '', w)
    if not core or core.isdigit():
      continue
    if i > 0 and core.lower() in SMALL:
      continue
    if not core[0].isupper():
      return ['name is not Title Case (%r)' % w]
  return []


def c_singular(t, ctx, p):
  name = re.sub(r'\(.*?\)', '', str(t['fm'].get('name', ''))).strip()
  last = name.split()[-1] if name.split() else ''
  low = last.lower()
  if (low.endswith('s') and not low.endswith(('ss', 'us', 'is', 'ics'))
      and low not in set(p.get('allow', [])) and not last.isupper()):
    return ['name may be plural (%r)' % last]
  return []


def c_not_acronym(t, ctx, p):
  name = str(t['fm'].get('name', ''))
  core = re.sub(r'[^A-Za-z]', '', name)
  return ['name looks like an acronym; use the expanded form'] if (
    core and core.isupper() and len(core) <= p.get('max_len', 5)) else []


def c_paren_needs(t, ctx, p):
  if '(' in str(t['fm'].get('name', '')) and _empty(t['fm'].get(p['field'])):
    return ['name has a qualifier but `%s` is empty' % p['field']]
  return []


def c_when_then(t, ctx, p):
  w = p['when']
  if _val(t, w['field']) == w.get('equals') and _empty(_val(t, p['field'])):
    return ['`%s` required when %s=%s' % (
      p['field'], w['field'], w.get('equals'))]
  return []


def c_forbidden_key(t, ctx, p):
  return ['forbidden field `%s`' % k for k in as_list(p['keys'])
          if k in t['fm']]


def c_forbidden_text(t, ctx, p):
  pat = fmt(p['pattern'], ctx['opts'])
  hay = t['body'] if p.get('scope') == 'body' else t['text']
  return ['text matches forbidden pattern %s' % pat] if re.search(
    pat, hay) else []


def c_date(t, ctx, p):
  v = t['fm'].get(p['field'])
  if _empty(v):
    return [] if p.get('optional') else ['`%s` is empty' % p['field']]
  try:
    d = datetime.date.fromisoformat(str(v))
  except ValueError:
    return ['`%s` is not an ISO date' % p['field']]
  return ['`%s` is in the future' % p['field']] if d > datetime.date.today() \
    else []


def c_owner(t, ctx, p):
  v = t['fm'].get(p['field'])
  if _empty(v):
    return ['`%s` is empty' % p['field']]
  token = p.get('placeholder')
  if token and v == token:
    if p.get('placeholder_ok'):
      return []
    return ['`%s` uses placeholder' % p['field']]
  pat = fmt(p.get('pattern', EMAIL_RE.pattern), ctx['opts'])
  return [] if re.search(pat, str(v)) else [
    '`%s` = %r is not a valid owner id' % (p['field'], v)]


def c_concordance(t, ctx, p):
  out, seen = [], set()
  c = t['fm'].get('concordance')
  if c is None:
    return []
  if not isinstance(c, list):
    return ['`concordance` must be a list']
  for e in c:
    if not (isinstance(e, dict) and e.get('url') and e.get('label')):
      out.append('concordance entry needs non-empty url and label')
      continue
    if e['url'] in seen:
      out.append('duplicate concordance url %s' % e['url'])
    seen.add(e['url'])
  return out


def c_external_cites(t, ctx, p):
  fm = t['fm']
  if fm.get('term_source') == 'EXTERNAL' and _empty(fm.get('source_origin')):
    return ['EXTERNAL term must cite its source in `source_origin`']
  return []


def c_approval(t, ctx, p):
  """Approved term edited past approved_version must return to review."""
  fm = t['fm']
  av, v = fm.get('approved_version'), fm.get('version')
  try:
    if av is not None and tuple(int(x) for x in str(av).split('.')[:2]) > \
        tuple(int(x) for x in str(v).split('.')[:2]):
      return ['approved_version is ahead of version']
    if fm.get('status') == 'Approved':
      if av is None:
        return ['Approved term has no approved_version']
      if tuple(int(x) for x in str(av).split('.')[:2]) != \
          tuple(int(x) for x in str(v).split('.')[:2]):
        return ['edited since approval; status must be Under Review']
  except ValueError:
    return ['cannot compare versions']
  return []


def c_no_dash(t, ctx, p):
  body = re.sub(r'```.*?```', '', t['body'], flags=re.S)
  return ['em dash in body prose'] if '\u2014' in body else []


def c_polish(t, ctx, p):
  return ['missing `%s`' % f for f in as_list(p['fields'])
          if _empty(t['fm'].get(f))]


# --- corpus-scope checks: fn(terms, ctx, p) -> [(id, message)] ----------

def _by_id(terms):
  return {t['fm'].get('id'): t for t in terms}


def k_unique(terms, ctx, p):
  seen, out = {}, []
  for t in terms:
    for v in as_list(t['fm'].get(p['field'])):
      key = str(v).lower() if p.get('nocase') else str(v)
      if key in seen:
        out.append((t['fm'].get('id'), 'duplicate %s %r (also %s)' % (
          p['field'], v, seen[key])))
      else:
        seen[key] = t['fm'].get('id')
  return out


def k_resolves(terms, ctx, p):
  ids, out = set(_by_id(terms)), []
  for t in terms:
    fm = t['fm']
    for f in as_list(p['fields']):
      for x in as_list(fm.get(f)):
        if x not in ids:
          out.append((fm.get('id'), '`%s` -> unknown id %r' % (f, x)))
  return out


def k_bidirectional(terms, ctx, p):
  m, out = _by_id(terms), []
  f = p['field']
  for t in terms:
    me = t['fm'].get('id')
    for x in as_list(t['fm'].get(f)):
      o = m.get(x)
      if o and me not in as_list(o['fm'].get(f)):
        out.append((me, '`%s` -> %s is not reciprocated' % (f, x)))
  return out


def k_relations(terms, ctx, p):
  ids, out = set(_by_id(terms)), []
  allowed = set(p.get('keys', REL_KEYS))
  for t in terms:
    fm, me = t['fm'], t['fm'].get('id')
    rels = fm.get('relations') or {}
    if not isinstance(rels, dict):
      out.append((me, '`relations` must be a mapping'))
      continue
    for k, v in rels.items():
      if k not in allowed:
        out.append((me, 'unknown relation key %r' % k))
      for x in as_list(v):
        if x == me:
          out.append((me, '`%s` points at itself' % k))
        elif x not in ids:
          out.append((me, '`%s` -> unknown id %r' % (k, x)))
  return out


def k_tree(terms, ctx, p):
  out, parents = [], {}
  for t in terms:
    me = t['fm'].get('id')
    r = rel_targets(t['fm'])
    if len(r['is_a']) > p.get('max_is_a', 2):
      out.append((me, 'more than %d is_a parents' % p.get('max_is_a', 2)))
    both = set(r['is_a']) & set(r['has_a'])
    if both:
      out.append((me, 'in both is_a and has_a: %s' % sorted(both)))
    for x in r['is_a']:
      parents.setdefault(me, set()).add(x)
    for x in r['has_a']:
      parents.setdefault(x, set()).add(me)
  if p.get('single_parent'):
    for me, ps in parents.items():
      if len(ps) > 1:
        out.append((me, 'has %d structural parents %s' % (
          len(ps), sorted(ps))))
  return out


def k_acyclic(terms, ctx, p):
  edges = {}
  for t in terms:
    me = t['fm'].get('id')
    r = rel_targets(t['fm'])
    edges.setdefault(me, set()).update(r['is_a'])
    for x in r['has_a']:
      edges.setdefault(x, set()).add(me)
  out, state = [], {}

  def visit(n, path):
    state[n] = 1
    for m in edges.get(n, ()):
      if state.get(m) == 1:
        out.append((n, 'cycle: %s' % ' > '.join(path + [m])))
      elif m not in state:
        visit(m, path + [m])
    state[n] = 2

  for n in list(edges):
    if n not in state:
      visit(n, [n])
  return out


def k_related_oneway(terms, ctx, p):
  out, rel = [], {}
  typed = set()
  for t in terms:
    me = t['fm'].get('id')
    rel[me] = as_list(t['fm'].get('related_terms'))
    r = rel_targets(t['fm'])
    for k in REL_KEYS:
      for x in r[k]:
        typed.add(frozenset((me, x)))
  for me, lst in rel.items():
    if len(lst) > p.get('max', 2):
      out.append((me, 'related_terms has %d entries, max %d' % (
        len(lst), p.get('max', 2))))
    for x in lst:
      if me in rel.get(x, []):
        out.append((me, 'related link to %s is mirrored' % x))
      if frozenset((me, x)) in typed:
        out.append((me, 'related link to %s repeats a typed relation' % x))
  return out


def k_ids_lock(terms, ctx, p):
  lock = ctx.get('ids_lock') or {}
  have = set(_by_id(terms))
  return [(i, 'id %r existed before and is now gone (ids never change)' % i)
          for i in lock if i not in have]


TERM_CHECKS = {
  'required': c_required, 'regex': c_regex, 'enum': c_enum,
  'sentence_max': c_sentence_max, 'not_circular': c_not_circular,
  'no_leading': c_no_leading, 'section_nonempty': c_section_nonempty,
  'bullets_min': c_bullets_min, 'filename_id': c_filename_id,
  'title_case': c_title_case, 'singular': c_singular,
  'not_acronym': c_not_acronym, 'paren_needs': c_paren_needs,
  'when_then': c_when_then, 'forbidden_key': c_forbidden_key,
  'forbidden_text': c_forbidden_text, 'date': c_date, 'owner': c_owner,
  'concordance': c_concordance, 'external_cites': c_external_cites,
  'approval': c_approval, 'no_dash': c_no_dash, 'polish': c_polish,
}
CORPUS_CHECKS = {
  'unique': k_unique, 'resolves': k_resolves,
  'bidirectional': k_bidirectional, 'relations': k_relations,
  'tree': k_tree, 'acyclic': k_acyclic, 'related_oneway': k_related_oneway,
  'ids_lock': k_ids_lock,
}


def active_rules(profile, cfg):
  opts = profile.get('options') or {}
  rules = []
  for r in profile.get('rules') or []:
    if r.get('enabled') is False:
      continue
    g = r.get('group')
    if g and not opts.get(g):
      continue
    cond = r.get('option')
    if cond and not opts.get(cond):
      continue
    rules.append(r)
  langs = cfg.get('languages') or ['en']
  if 'pl' in langs and cfg.get('polish_required', False):
    rules.append({'id': 'LANG-PL', 'level': 'SHOULD', 'check': 'polish',
                  'params': {'fields': ['name_pl', 'description_pl']}})
  return rules


def evaluate(terms, profile, cfg, ctx_extra=None):
  """Return violations: list of dicts {term, rule, level, message}."""
  ctx = {'profile': profile, 'opts': profile.get('options') or {},
         'cfg': cfg}
  ctx.update(ctx_extra or {})
  out = []
  for r in active_rules(profile, cfg):
    p = dict(r.get('params') or {})
    level = r.get('level', 'MUST')
    if r.get('heuristic') and level == 'MUST':
      level = 'SHOULD'
    chk = r['check']
    if chk in TERM_CHECKS:
      for t in terms:
        w = r.get('when')
        if w and not _when(t, w):
          continue
        for msg in TERM_CHECKS[chk](t, ctx, p):
          out.append({'term': t['fm'].get('id'), 'rule': r['id'],
                      'level': level, 'message': msg})
    elif chk in CORPUS_CHECKS:
      for tid, msg in CORPUS_CHECKS[chk](terms, ctx, p):
        out.append({'term': tid, 'rule': r['id'], 'level': level,
                    'message': msg})
    else:
      out.append({'term': None, 'rule': r['id'], 'level': 'MUST',
                  'message': 'unknown check %r in profile' % chk})
  return out


def _when(t, w):
  v = _val(t, w['field'])
  if 'equals' in w:
    return v == w['equals']
  if 'in' in w:
    return v in w['in']
  if 'present' in w:
    return (not _empty(v)) == bool(w['present'])
  return True


def tiers(terms, violations, profile):
  """Return {term_id: tier name or 'Below'} per the profile's tier list."""
  spec = profile.get('tiers') or []
  failing = {}
  for v in violations:
    if v['level'] == 'MUST':
      failing.setdefault(v['term'], set()).add(v['rule'])
  res = {}
  for t in terms:
    me, got = t['fm'].get('id'), 'Below'
    for tier in spec:  # highest first
      if _tier_ok(t, tier, spec, failing.get(me, set())):
        got = tier['name']
        break
    res[me] = got
  return res


def _tier_ok(t, tier, spec, failed):
  chain = [tier]
  inc = tier.get('includes')
  while inc:
    nxt = next((x for x in spec if x['name'] == inc), None)
    if not nxt:
      break
    chain.append(nxt)
    inc = nxt.get('includes')
  for x in chain:
    if any(r in failed for r in as_list(x.get('rules'))):
      return False
    if any(_empty(_val(t, f)) for f in as_list(x.get('fields'))):
      return False
    for k, v in (x.get('equals') or {}).items():
      if t['fm'].get(k) != v:
        return False
    if x.get('all_must') and failed:
      return False
    mo = x.get('reviewed_within_months')
    if mo:
      lr = t['fm'].get('last_reviewed')
      try:
        d = datetime.date.fromisoformat(str(lr))
      except ValueError:
        return False
      if (datetime.date.today() - d).days > mo * 30.5:
        return False
  return True
