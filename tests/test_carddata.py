"""Sanity checks on the row assignments in cards.json.

These cannot verify against the printed cards - they catch structural
mistakes: rows that make no sense for a card type, factions missing a row,
and abilities that only work in certain rows.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bootstrap  # noqa: F401,E402  - sets sys.path, cwd and headless mode

import json  # noqa: E402
from collections import Counter  # noqa: E402

from gwint_rules import (MELEE, RANGED, SIEGE, ROW_NAMES,  # noqa: E402
                         load_card_pool)

checks = []


def check(label, ok, detail=''):
    checks.append(bool(ok))
    print(f'{"OK  " if ok else "FAIL"} {label}{" - " + detail if detail else ""}')


pool = load_card_pool()
with open('cards.json', encoding='utf-8') as handle:
    raw = json.load(handle)

VALID_ROWS = set(ROW_NAMES) | {'agile', 'special', 'weather'}
FACTIONS = ['north', 'nilfgaard', 'scoiatael', 'monster']

# --- 1. every row value is known -------------------------------------------
for faction, entries in raw.items():
    if faction.startswith('_'):
        continue
    for entry in entries:
        name = entry['name']['de'] if isinstance(entry['name'], dict) else entry['name']
        check(f'{name}: row "{entry["row"]}" is valid',
              entry['row'] in VALID_ROWS, entry['row'])

# --- 2. special and weather cards carry no strength ------------------------
for cards in pool.values():
    for card in cards:
        if card.is_special:
            check(f'{card.name}: special card has no strength',
                  card.strength == 0, str(card.strength))

# --- 3. units must have a positive strength (spies may be 0) ---------------
for cards in pool.values():
    for card in cards:
        if card.is_unit and card.ability != 'spy':
            check(f'{card.name}: unit has strength',
                  card.strength > 0, str(card.strength))

# --- 4. weather cards need a weather ability and the other way round -------
for cards in pool.values():
    for card in cards:
        if card.is_weather:
            check(f'{card.name}: weather card has a weather ability',
                  card.ability in ('frost', 'fog', 'rain', 'clear'), card.ability)
        elif card.ability in ('frost', 'fog', 'rain', 'clear'):
            check(f'{card.name}: weather ability only on weather cards', False,
                  card.row)

# --- 5. agile means exactly close combat plus ranged -----------------------
for cards in pool.values():
    for card in cards:
        if card.is_agile:
            check(f'{card.name}: agile covers melee and ranged',
                  card.allowed_rows == (MELEE, RANGED), str(card.allowed_rows))
            check(f'{card.name}: agile card is a unit', card.is_unit, card.row)

# --- 6. every faction needs close combat and ranged ------------------------
# A siege row is not mandatory: the artwork shows the Scoia'tael have no
# siege units at all, which is a genuine trait of that faction.
for faction in FACTIONS:
    covered = set()
    for card in pool[faction]:
        covered.update(card.allowed_rows)
    check(f'{faction}: can fill close combat and ranged',
          {MELEE, RANGED} <= covered, str(sorted(covered)))

check('at least one faction fields siege units',
      any(SIEGE in c.allowed_rows for f in FACTIONS for c in pool[f]), '')

# --- 7. a faction should not put everything in one row ---------------------
for faction in FACTIONS:
    counts = Counter()
    for card in pool[faction]:
        for row in card.allowed_rows:
            counts[row] += 1
    total = sum(counts.values())
    for row in (MELEE, RANGED, SIEGE):
        share = counts[row] / total if total else 0
        # A row may be empty; it must not swallow the whole faction
        check(f'{faction}: row {row} is not overwhelming '
              f'({counts[row]}/{total})', share <= 0.75, f'{share:.0%}')

# --- 8. tight bond and muster need more than one copy ----------------------
# Muster counts by its key: the vampires and the arachas share a group even
# though every one of them has its own name.
for faction, cards in pool.items():
    names = Counter(c.name for c in cards)
    keys = Counter(c.muster_key for c in cards)
    for card in cards:
        if card.ability == 'bond':
            check(f'{card.name}: bond needs several copies',
                  names[card.name] > 1, f'{names[card.name]}x')
        elif card.ability == 'muster':
            check(f'{card.name}: muster needs several copies',
                  keys[card.muster_key] > 1, f'{keys[card.muster_key]}x')

# --- 9. copies of one card must agree on row and ability -------------------
for faction, cards in pool.items():
    by_name = {}
    for card in cards:
        by_name.setdefault(card.name, []).append(card)
    for name, group in by_name.items():
        rows = {c.row for c in group}
        abilities = {c.ability for c in group}
        check(f'{name}: all copies share one row', len(rows) == 1, str(rows))
        check(f'{name}: all copies share one ability',
              len(abilities) == 1, str(abilities))

# --- 10. heroes are units, never special cards -----------------------------
for cards in pool.values():
    for card in cards:
        if card.hero:
            check(f'{card.name}: hero is a unit', card.is_unit, card.row)

# --- 11. siege-row abilities that only make sense there --------------------
# Morale boost cards sit in the siege row in the original
for cards in pool.values():
    for card in cards:
        if card.ability == 'morale':
            check(f'{card.name}: morale card is a unit', card.is_unit, card.row)

# --- 12. scorch_melee belongs to a melee card ------------------------------
for cards in pool.values():
    for card in cards:
        if card.ability == 'scorch_melee':
            check(f'{card.name}: melee scorch sits in close combat',
                  MELEE in card.allowed_rows, card.row)

print()
if all(checks):
    print(f'All {len(checks)} card data checks passed.')
else:
    print(f'{checks.count(False)} of {len(checks)} card data checks FAILED.')
    raise SystemExit(1)

