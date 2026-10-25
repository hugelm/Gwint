"""Checks that the source code is documented in English.

Keeps the project consistent: German only lives in the translation catalogue
(gwint_i18n.py) and in cards.json, never in comments or docstrings.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bootstrap  # noqa: F401,E402  - sets sys.path, cwd and headless mode

import ast
import io
import re
import tokenize

SOURCES = [
    'Gwint.py', 'gwint_ui.py', 'gwint_game.py', 'gwint_rules.py',
    'gwint_i18n.py', 'gwint_config.py', 'launcher.py', 'run_tests.py',
    os.path.join('tools', 'build_assets.py'),
    os.path.join('tools', 'make_icon.py'),
] + sorted(os.path.join('tests', f) for f in os.listdir('tests')
           if f.startswith('test_') and f.endswith('.py'))

# Words that only occur in German prose. Proper nouns and Witcher terms are
# deliberately absent so they never trigger a false positive.
GERMAN_WORDS = {
    'aber', 'auch', 'beim', 'damit', 'dann', 'diese', 'durch', 'eine', 'einen',
    'eines', 'fuer', 'für', 'gibt', 'haben', 'hier', 'jede', 'jeder', 'kann',
    'karte', 'karten', 'keine', 'liefert', 'mehrere', 'nicht', 'nur', 'oder',
    'ohne', 'reihe', 'reihen', 'sich', 'sind', 'spieler', 'und', 'vom', 'von',
    'werden', 'wird', 'zum', 'zur', 'zurueck', 'zurück', 'auswahl',
    'ausspielen', 'faehigkeit', 'fähigkeit', 'gegner', 'punkte', 'wetter',
    'zeichnen', 'schreibt', 'liest', 'erzeugt', 'entfernt', 'belegt',
    'ablage', 'friedhof', 'gespielt', 'geloescht', 'gelöscht', 'nachziehen',
    'aufraeumen', 'aufräumen', 'ueberspringen', 'überspringen',
}

checks = []

def check(label, ok, detail=''):
    checks.append(bool(ok))
    print(f'{"OK  " if ok else "FAIL"} {label}{" - " + detail if detail else ""}')

def comments_and_docstrings(path):
    """Yield (line number, text) for every comment and docstring in a file."""
    source = open(path, encoding='utf-8').read()

    readline = io.StringIO(source).readline
    for token in tokenize.generate_tokens(readline):
        if token.type == tokenize.COMMENT:
            yield token.start[0], token.string.lstrip('#').strip()

    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node)
            if doc:
                yield getattr(node, 'lineno', 1), doc

for path in SOURCES:
    if not os.path.exists(path):
        check(f'{path} exists', False)
        continue

    hits = []
    for lineno, block in comments_and_docstrings(path):
        words = {w.lower() for w in re.findall(r"[A-Za-zÄÖÜäöüß]+", block)}
        found = words & GERMAN_WORDS
        if found:
            hits.append(f'line {lineno}: {sorted(found)[:3]}')

    check(f'{path}: comments and docstrings are English', not hits,
          '; '.join(hits[:3]))

# The README has to be English as well
if os.path.exists('README.md'):
    readme = open('README.md', encoding='utf-8').read()
    # Skip fenced code blocks and inline code - card names may stay German
    prose = re.sub(r'```.*?```', '', readme, flags=re.S)
    prose = re.sub(r'`[^`]*`', '', prose)
    words = {w.lower() for w in re.findall(r'[A-Za-zÄÖÜäöüß]+', prose)}
    hits = words & GERMAN_WORDS
    check('README.md is English', not hits, ', '.join(sorted(hits)[:5]))

    # --- markdown GitHub renders differently than a local preview ----------
    # The file was once written out as cp1252 and read back as UTF-8, which
    # turned every dash and box drawing character into "a-euro-quote". An
    # editor still shows something; GitHub shows the mojibake.
    mojibake = [n for n, line in enumerate(readme.split('\n'), 1)
                if '\u00e2\u20ac' in line
                or re.search('\u00c3[\u0080-\u00ff]', line)]
    check('README.md is not doubly encoded', not mojibake,
          f'lines {mojibake[:5]}')

    lines = readme.split('\n')
    fences = [n for n, line in enumerate(lines, 1)
              if line.strip().startswith('```')]
    check('README.md code fences pair up', len(fences) % 2 == 0,
          f'{len(fences)} fences')

    # Tables need a separator row and an even column count, otherwise
    # GitHub prints the raw pipes instead of drawing a table.
    bad_tables = []
    inside = False
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        if stripped.startswith('```'):
            inside = not inside
            index += 1
            continue
        if inside or not stripped.startswith('|'):
            index += 1
            continue
        start = index
        block = []
        while index < len(lines) and lines[index].strip().startswith('|'):
            block.append(lines[index].strip())
            index += 1
        if len(block) < 2 or not re.match(r'^\|[\s:|-]+\|$', block[1]):
            bad_tables.append(f'line {start + 1}: no separator row')
            continue
        width = block[0].count('|')
        for offset, row in enumerate(block):
            if row.count('|') != width:
                bad_tables.append(f'line {start + 1 + offset}: '
                                  f'{row.count("|") - 1} of {width - 1} columns')

    check('README.md tables are well formed', not bad_tables,
          '; '.join(bad_tables[:3]))

    # An odd number of asterisks in a table cell opens an emphasis that
    # swallows the rest of the row - "Poor F***ing Infantry" did exactly that.
    loose = []
    for lineno, line in enumerate(lines, 1):
        if not line.strip().startswith('|'):
            continue
        for cell in line.split('|'):
            if re.sub(r'`[^`]*`', '', cell).count('*') % 2:
                loose.append(str(lineno))
                break

    check('README.md has no unbalanced emphasis in tables', not loose,
          f'lines {loose[:5]}')

# German user-facing text must still exist - in the catalogue only
from gwint_i18n import TEXT  # noqa: E402
check('german strings live in gwint_i18n.py',
      all('de' in entry for entry in TEXT.values()))

print()
if all(checks):
    print(f'All {len(checks)} source checks passed.')
else:
    print(f'{checks.count(False)} of {len(checks)} source checks FAILED.')
    raise SystemExit(1)

