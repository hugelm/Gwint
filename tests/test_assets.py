"""Checks that every image referenced by cards.json actually exists."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bootstrap  # noqa: F401,E402  - sets sys.path, cwd and headless mode

from gwint_i18n import LANGUAGES  # noqa: E402
from gwint_rules import load_card_pool  # noqa: E402

checks = []

def check(label, ok, detail=''):
    checks.append(bool(ok))
    print(f'{"OK  " if ok else "FAIL"} {label}{" - " + detail if detail else ""}')

pool = load_card_pool()
ids = sorted({c.id for cards in pool.values() for c in cards})
print(f'{len(ids)} distinct card ids in cards.json\n')

for lang in LANGUAGES:
    base = os.path.join('cards', lang)
    if not os.path.isdir(base):
        check(f'{lang}: folder present', False, 'run tools/build_assets.py')
        continue

    for size in ('small', 'large'):
        missing = [i for i in ids
                   if not os.path.exists(os.path.join(base, size, f'{i}.png'))]
        check(f'{lang}/{size}: every image present', not missing,
              ', '.join(missing[:8]))

    check(f'{lang}: card back present',
          os.path.exists(os.path.join(base, 'small', 'back.png')))

# Both languages have to ship the same set of files
if all(os.path.isdir(os.path.join('cards', l)) for l in LANGUAGES):
    sets = {}
    for lang in LANGUAGES:
        sets[lang] = {f for f in os.listdir(os.path.join('cards', lang, 'small'))
                      if f.endswith('.png')}
    first, second = LANGUAGES[0], LANGUAGES[1]
    diff = sets[first] ^ sets[second]
    check('both languages ship the same files', not diff,
          ', '.join(sorted(diff)[:8]))

# The launcher previews need their leader artwork
try:
    from launcher import FACTION_ART
    for code, card_id in FACTION_ART.items():
        path = os.path.join('cards', 'de', 'large', f'{card_id}.png')
        check(f'launcher leader artwork for {code}', os.path.exists(path), path)
except ImportError:
    pass

# The game icon, written next to the launcher tiles
for name in ('icon.png', 'icon_64.png'):
    path = os.path.join('cards', 'tiles', name)
    check(f'{name} present', os.path.exists(path), 'run tools/make_icon.py')

print()
if all(checks):
    print(f'All {len(checks)} asset checks passed.')
else:
    print(f'{checks.count(False)} of {len(checks)} asset checks FAILED.')
    raise SystemExit(1)

