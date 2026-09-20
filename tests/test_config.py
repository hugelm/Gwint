"""Tests for gwint_config - settings file and command line hand-off."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bootstrap  # noqa: F401,E402  - sets sys.path, cwd and headless mode

import json
import tempfile

import gwint_config  # noqa: E402
from gwint_config import Settings, config_dir, config_path, from_command_line  # noqa: E402

checks = []

def check(label, got, expected):
    ok = got == expected
    checks.append(ok)
    print(f'{"OK  " if ok else "FAIL"} {label}: {got} (expected {expected})')

# --- defaults ---------------------------------------------------------------
s = Settings()
check('default name', s.name, 'Geralt')
check('default faction', s.faction, 'north')
check('default language', s.language, 'de')
check('default intro', s.intro, True)
check('default music', s.music, True)
check('default fullscreen', s.fullscreen, False)

# --- validation -------------------------------------------------------------
check('invalid language falls back', Settings(language='klingon').language, 'de')
check('valid language kept', Settings(language='en').language, 'en')
check('fullscreen coerced to bool', Settings(fullscreen=1).fullscreen, True)
check('None uses the default', Settings(name=None).name, 'Geralt')

# --- the settings file lives outside the project ----------------------------
project = _bootstrap.PROJECT_ROOT
check('config dir is not the project folder',
      os.path.abspath(config_dir()).startswith(project), False)
check('config file is called settings.json',
      os.path.basename(config_path()), 'settings.json')

# --- save and load ----------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    path = os.path.join(tmp, 'sub', 'settings.json')

    original = Settings(name='Marius', faction='monster', language='en',
                        fullscreen=True, music=False, intro=False)
    check('save reports success', original.save(path), True)
    check('file was created', os.path.exists(path), True)

    loaded = Settings.load(path)
    check('name round trip', loaded.name, 'Marius')
    check('faction round trip', loaded.faction, 'monster')
    check('language round trip', loaded.language, 'en')
    check('fullscreen round trip', loaded.fullscreen, True)
    check('music round trip', loaded.music, False)
    check('intro round trip', loaded.intro, False)

    # The file has to be readable JSON
    with open(path, encoding='utf-8') as handle:
        raw = json.load(handle)
    check('stored as a dict', isinstance(raw, dict), True)
    check('no leftover temp file', os.path.exists(path + '.tmp'), False)

    # Broken files must not crash the game
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write('{ this is not json')
    check('broken file falls back to defaults', Settings.load(path).name, 'Geralt')

    with open(path, 'w', encoding='utf-8') as handle:
        handle.write('[1, 2, 3]')
    check('wrong type falls back', Settings.load(path).faction, 'north')

    # Missing file
    check('missing file falls back',
          Settings.load(os.path.join(tmp, 'nope.json')).language, 'de')

# --- command line -----------------------------------------------------------
s = Settings(name='Ada', faction='scoiatael', language='en')
argv = s.to_argv()
check('argv carries the name', '--name' in argv and 'Ada' in argv, True)
check('argv carries the faction', argv[argv.index('--faction') + 1], 'scoiatael')
check('argv carries the language', argv[argv.index('--language') + 1], 'en')
check('no flags when everything is default', '--no-intro' in argv, False)

s2 = Settings(fullscreen=True, music=False, intro=False)
argv2 = s2.to_argv()
check('fullscreen flag', '--fullscreen' in argv2, True)
check('no-music flag', '--no-music' in argv2, True)
check('no-intro flag', '--no-intro' in argv2, True)

# Command line wins over the stored file
parsed = from_command_line(['--name', 'Zoltan', '--language', 'en',
                            '--faction', 'monster'])
check('command line name wins', parsed.name, 'Zoltan')
check('command line language wins', parsed.language, 'en')
check('command line faction wins', parsed.faction, 'monster')

# An empty command line keeps the stored values
empty = from_command_line([])
check('empty command line yields settings', isinstance(empty, Settings), True)

# Round trip: settings -> argv -> settings
source = Settings(name='Yennefer', faction='nilfgaard', language='en',
                  fullscreen=True, music=False, intro=False)
restored = from_command_line(source.to_argv())
check('round trip name', restored.name, 'Yennefer')
check('round trip faction', restored.faction, 'nilfgaard')
check('round trip language', restored.language, 'en')
check('round trip fullscreen', restored.fullscreen, True)
check('round trip music', restored.music, False)
check('round trip intro', restored.intro, False)

# --- the old hand-off file is gone ------------------------------------------
check('game_data.txt no longer used', os.path.exists('game_data.txt'), False)

# Only look at real code, a docstring may still mention the old approach
import ast  # noqa: E402

def code_without_docstrings(path):
    tree = ast.parse(open(path, encoding='utf-8').read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            # Skip docstrings, keep real string literals
            continue
        if isinstance(node, ast.Str):  # pragma: no cover - older ASTs
            continue
    literals = [n.value for n in ast.walk(tree)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    return literals

uses_old_file = False
for path in ('Gwint.py', 'launcher.py'):
    if not os.path.exists(path):
        continue
    if any('game_data' in literal for literal in code_without_docstrings(path)):
        uses_old_file = True

check('no code opens game_data.txt', uses_old_file, False)

print()
if all(checks):
    print(f'All {len(checks)} config checks passed.')
else:
    print(f'{checks.count(False)} of {len(checks)} config checks FAILED.')
    raise SystemExit(1)

