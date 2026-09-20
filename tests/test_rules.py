"""Tests for gwint_rules - runs without pygame."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bootstrap  # noqa: F401,E402  - sets sys.path, cwd and headless mode

import random

from gwint_rules import (MELEE, RANGED, SIEGE, Card, build_deck, card_value,
                         load_card_pool, row_score)

checks = []

def check(label, got, expected):
    ok = got == expected
    checks.append(ok)
    print(f'{"OK  " if ok else "FAIL"} {label}: {got} (expected {expected})')

def unit(name, strength, ability='', hero=False):
    return Card(id='000', name=name, strength=strength, row='melee',
                ability=ability, hero=hero)

# --- basics -----------------------------------------------------------------
check('empty row', row_score([]), 0)
check('three units 5+6+7', row_score([unit('a', 5), unit('b', 6), unit('c', 7)]), 18)

# --- weather ----------------------------------------------------------------
check('weather drops units to 1',
      row_score([unit('a', 5), unit('b', 6), unit('c', 7)], weather=True), 3)
check('hero ignores weather',
      row_score([unit('a', 5), unit('h', 10, hero=True)], weather=True), 11)

# --- tight bond -------------------------------------------------------------
check('bond 3x4 -> 3*3*4', row_score([unit('BS', 4, 'bond')] * 3), 36)
check('bond 2x8 -> 2*2*8', row_score([unit('K', 8, 'bond')] * 2), 32)
check('single bond card stays 4', row_score([unit('BS', 4, 'bond')]), 4)
check('bond only for identical names',
      row_score([unit('BS', 4, 'bond'), unit('PFI', 4, 'bond')]), 8)
check('bond under weather (1*3 each)',
      row_score([unit('BS', 4, 'bond')] * 3, weather=True), 9)

# --- morale boost -----------------------------------------------------------
check('morale 3x1 -> 9', row_score([unit('KBE', 1, 'morale')] * 3), 9)
check('morale gives others +1',
      row_score([unit('KBE', 1, 'morale'), unit('a', 5)]), 7)

# --- commander's horn -------------------------------------------------------
check('horn doubles the row', row_score([unit('a', 5), unit('b', 6)], horn=True), 22)
check('horn unit boosts others but not itself',
      row_score([unit('Dandelion', 2, 'horn'), unit('a', 5)]), 12)
check('horn + weather', row_score([unit('a', 5), unit('b', 6)],
                                  weather=True, horn=True), 4)
check('horn + hero', row_score([unit('h', 10, hero=True)], horn=True), 20)

# --- special cards score nothing -------------------------------------------
special = Card(id='157', name='Horn', strength=0, row='special', ability='horn')
check('special card scores nothing', row_score([unit('a', 5), special]), 10)

# --- card_value -------------------------------------------------------------
row = [unit('BS', 4, 'bond') for _ in range(3)]
check('card_value of a bond card', card_value(row[0], row), 12)
row2 = [unit('a', 5), unit('b', 7)]
check('card_value plain', card_value(row2[1], row2), 7)
check('card_value under weather', card_value(row2[1], row2, weather=True), 1)
check('card_value with horn', card_value(row2[1], row2, horn=True), 14)

# --- card pool and deck building -------------------------------------------
pool = load_card_pool()
check('factions loaded', sorted(pool.keys()),
      ['monster', 'neutral', 'nilfgaard', 'north', 'scoiatael'])

# Every faction has to be playable
for faction in ('north', 'nilfgaard', 'scoiatael', 'monster'):
    cards = pool[faction]
    check(f'{faction}: enough cards', len(cards) >= 22, True)
    check(f'{faction}: has heroes', any(c.hero for c in cards), True)
    # Close combat and ranged are mandatory, a siege row is not:
    # the artwork shows the Scoia'tael field no siege units at all.
    covered = set()
    for card in cards:
        covered.update(card.allowed_rows)
    check(f'{faction}: covers melee and ranged',
          {MELEE, RANGED} <= covered, True)
    deck = build_deck(faction, pool, 6, random.Random(3))
    check(f'{faction}: deck buildable', len(deck) == len(cards) + 6, True)

north = pool['north']
check('northern realms card count', len(north), 35)
check('heroes in the northern deck', sum(1 for c in north if c.hero), 2)
check('spies in the northern deck', sum(1 for c in north if c.ability == 'spy'), 3)

neutral = pool['neutral']
check('weather cards in the pool', sum(1 for c in neutral if c.is_weather), 12)
check('decoys in the pool', sum(1 for c in neutral if c.ability == 'decoy'), 3)

deck = build_deck('north', pool, neutral_count=6, rng=random.Random(42))
check('deck size', len(deck), 41)
check('deck holds only north + neutral',
      sorted({c.faction for c in deck}), ['neutral', 'north'])

# Deck building has to be reproducible
d1 = build_deck('north', pool, 6, random.Random(7))
d2 = build_deck('north', pool, 6, random.Random(7))
check('deck building reproducible', [c.id for c in d1], [c.id for c in d2])

# --- Grave Hag is a ranged unit (matches the printed card) ------------------
hags = [c for c in pool['monster'] if c.name == 'Gruftweib']
check('grave hag exists', len(hags), 1)
if hags:
    check('grave hag is ranged', hags[0].row, 'ranged')

# --- row mapping ------------------------------------------------------------
check('melee -> 0', Card('0', 'x', 1, 'melee').row_index, 0)
check('ranged -> 1', Card('0', 'x', 1, 'ranged').row_index, 1)
check('siege -> 2', Card('0', 'x', 1, 'siege').row_index, 2)
check('special -> None', Card('0', 'x', 0, 'special').row_index, None)

# --- agile units ------------------------------------------------------------
agile = Card('079', 'Yaevinn', 10, 'agile')
plain = Card('025', 'Catapult', 8, 'siege')
spec = Card('157', 'Horn', 0, 'special', 'horn')

check('agile card is flagged', agile.is_agile, True)
check('plain card is not agile', plain.is_agile, False)
check('agile counts as a unit', agile.is_unit, True)
check('agile defaults to close combat', agile.row_index, MELEE)
check('agile allows melee and ranged', agile.allowed_rows, (MELEE, RANGED))
check('plain card allows one row', plain.allowed_rows, (SIEGE,))
check('special card allows no row', spec.allowed_rows, ())

# Agile cards score like any other unit
check('agile card scores normally', row_score([agile]), 10)
check('agile card under weather', row_score([agile], weather=True), 1)

# The card pool really contains agile units
agile_cards = [c for cards in pool.values() for c in cards if c.is_agile]
check('pool contains agile units', len(agile_cards) > 0, True)
check('every agile unit allows both rows',
      all(c.allowed_rows == (MELEE, RANGED) for c in agile_cards), True)
check('agile units are never special',
      any(c.is_special for c in agile_cards), False)

print()
if all(checks):
    print(f'All {len(checks)} rule checks passed.')
else:
    print(f'{checks.count(False)} of {len(checks)} rule checks FAILED.')
    raise SystemExit(1)

