"""Regression tests for the reported bugs - these must never come back."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bootstrap  # noqa: F401,E402  - sets sys.path, cwd and headless mode

import random  # noqa: E402

import pygame  # noqa: E402

import Gwint  # noqa: E402
from gwint_config import Settings  # noqa: E402
from gwint_rules import MELEE, RANGED, SIEGE, load_card_pool  # noqa: E402

checks = []


def check(label, got, expected):
    ok = got == expected
    checks.append(ok)
    print(f'{"OK  " if ok else "FAIL"} {label}: {got} (expected {expected})')


def fresh(faction='north', seed=3):
    random.seed(seed)
    app = Gwint.GwintApp('Tester', 'de', intro=False, music=False)
    app.new_game(faction)
    app.user_turn = True
    app.user.passed = app.ai.passed = False
    return app


def settle(app, limit=60):
    steps = 0
    while app.busy and steps < limit:
        app.tick_timers(0.1)
        steps += 1


pygame.init()
pool = load_card_pool()

# --- Scoia'tael muster: one card pulls its copies ---------------------------
# The original has no Tight Bond in this faction; those cards are Muster.
for name in ('Zwergen-Scharmützler', 'Elfen-Scharmützler'):
    copies = [c for c in pool['scoiatael'] if c.name == name]
    check(f'{name} exists more than once', len(copies) > 1, True)
    check(f'{name} has muster', copies[0].ability, 'muster')

    app = fresh('scoiatael')
    app.user.hand.clear()
    app.user.hand.append(copies[0])
    app.user.deck = list(copies[1:])
    app.selected = 0
    app.play_selected()
    settle(app)
    on_board = sum(1 for row in app.user.rows for c in row if c.name == name)
    check(f'{name}: all copies on the board', on_board, len(copies))
    check(f'{name}: deck emptied', len(app.user.deck), 0)

check('scoiatael has no tight bond',
      any(c.ability == 'bond' for c in pool['scoiatael']), False)

# 081, 087 and 089 carry no icon at all - checked on the originals.
for name in ('Dol-Blathanna-Späher', 'Vrihedd-Brigade', 'Mahakam-Verteidiger'):
    copies = [c for c in pool['scoiatael'] if c.name == name]
    check(f'{name} exists more than once', len(copies) > 1, True)
    check(f'{name} carries no ability', copies[0].ability, '')

    app = fresh('scoiatael')
    app.user.hand.clear()
    app.user.hand.append(copies[0])
    app.user.deck = list(copies[1:])
    app.selected = 0
    app.play_selected()
    if app.pending:                      # agile cards still ask for a row
        app.handle_key(pygame.K_RETURN)
    settle(app)
    on_board = sum(1 for row in app.user.rows for c in row if c.name == name)
    check(f'{name}: only the played copy lands', on_board, 1)
    check(f'{name}: deck untouched', len(app.user.deck), len(copies) - 1)

# --- muster groups: different names, one call ------------------------------
# The vampires and the two arachas cards share an icon but not a name.
vampires = [c for c in pool['monster'] if c.muster_group == 'vampire']
check('five vampires carry the group', len(vampires), 5)
check('vampires have different names',
      len({c.name for c in vampires}), 5)
check('vampires all muster',
      all(c.ability == 'muster' for c in vampires), True)
check('vampires share a muster key',
      len({c.muster_key for c in vampires}), 1)

app = fresh('monster')
first = vampires[0]
app.user.hand.clear()
app.user.hand.append(first)
app.user.deck = list(vampires[1:])
app.selected = 0
app.play_selected()
settle(app)
on_board = sum(1 for row in app.user.rows for c in row
               if c.muster_group == 'vampire')
check('one vampire pulls all five', on_board, 5)
check('deck emptied by the vampire muster', len(app.user.deck), 0)

arachas = [c for c in pool['monster'] if c.muster_group == 'arachas']
check('arachas group spans two names',
      len({c.name for c in arachas}) >= 2, True)

app = fresh('monster')
behemoth = next(c for c in arachas if 'Ungetüm' in c.name)
small = [c for c in arachas if c is not behemoth]
app.user.hand.clear()
app.user.hand.append(behemoth)
app.user.deck = list(small)
app.selected = 0
app.play_selected()
settle(app)
pulled = sum(1 for row in app.user.rows for c in row
             if c.muster_group == 'arachas')
check('behemoth pulls the small arachas', pulled, len(arachas))

# Muster must not cross groups
app = fresh('monster')
nekker = next(c for c in pool['monster'] if c.name == 'Nekker')
app.user.hand.clear()
app.user.hand.append(nekker)
app.user.deck = [c for c in pool['monster'] if c.muster_group == 'vampire']
app.selected = 0
app.play_selected()
settle(app)
check('nekker does not pull vampires',
      sum(1 for row in app.user.rows for c in row), 1)

# --- abilities verified against the artwork --------------------------------
archer = next(c for c in pool['nilfgaard'] if c.name == 'Bogenschütze')
check('archer is a medic (read off the card)', archer.ability, 'medic')

support = next(c for c in pool['nilfgaard'] if c.name == 'Unterstützung')
check('siege support is a medic', support.ability, 'medic')

isengrim = next(c for c in pool['scoiatael']
                if c.name == 'Isengrim Faoiltiarna')
check('isengrim is a medic (read off the card)', isengrim.ability, 'medic')
check('isengrim stays a hero', isengrim.hero, True)

# A hero medic revives others but can never be revived himself
app = fresh('scoiatael', seed=11)
other = next(c for c in pool['scoiatael'] if not c.hero and c.is_unit)
app.user.hand.clear()
app.user.hand.append(isengrim)
app.user.discard = [other]
app.selected = 0
app.play_selected()
check('isengrim opens the graveyard', app.grave_view, 'user')
app.handle_key(pygame.K_RETURN)
settle(app)
check('isengrim revived the unit',
      any(other in row for row in app.user.rows), True)
check('isengrim himself is on the board',
      any(isengrim in row for row in app.user.rows), True)

# Northern Realms and Nilfgaard keep their tight bond
check('north keeps tight bond',
      any(c.ability == 'bond' for c in pool['north']), True)
check('nilfgaard keeps tight bond',
      any(c.ability == 'bond' for c in pool['nilfgaard']), True)

# --- No cards are drawn between rounds --------------------------------------
app = fresh('scoiatael', seed=5)
before = len(app.user.hand)
app.user.rows[MELEE] = [app.user.hand.pop()]
app.user.passed = app.ai.passed = True
app.finish_round()
check('no cards drawn after a round', len(app.user.hand), before - 1)

# The AI does not draw either
app = fresh('monster', seed=6)
ai_before = len(app.ai.hand)
app.user.passed = app.ai.passed = True
app.finish_round()
check('AI draws nothing either', len(app.ai.hand), ai_before)

# --- Northern Realms bonus: one card for winning a round --------------------
app = fresh('north', seed=5)
app.user.rows[MELEE] = [[c for c in pool['north'] if c.strength == 5][0]]
before = len(app.user.hand)
app.user.passed = app.ai.passed = True
app.finish_round()
check('northern realms draw one on a win', len(app.user.hand), before + 1)

# Losing the round grants nothing
app = fresh('north', seed=5)
app.ai.rows[MELEE] = [[c for c in pool['north'] if c.strength == 5][0]]
before = len(app.user.hand)
app.user.passed = app.ai.passed = True
app.finish_round()
check('no bonus when losing the round', len(app.user.hand), before)

# Other factions never get the bonus
app = fresh('monster', seed=5)
app.user.rows[MELEE] = [[c for c in pool['monster'] if c.strength == 5][0]]
before = len(app.user.hand)
app.user.passed = app.ai.passed = True
app.finish_round()
check('monsters get no bonus', len(app.user.hand), before)

# --- the end of the game has to be noticed ---------------------------------
# GwintApp used to keep its own game_over flag that nothing ever set to True:
# the final screen never appeared and a headless game ran forever.
app = fresh('north', seed=4)
check('a fresh game is not over', app.game_over, False)

strong = next(c for c in pool['north'] if c.strength >= 8 and not c.hero)
rounds = 0
while not app.game_over and rounds < 5:
    rounds += 1
    app.ai.rows[MELEE] = [strong]
    app.user.rows = [[] for _ in app.user.rows]
    app.user.passed = app.ai.passed = True
    app.finish_round()

check('losing every round ends the game', app.game_over, True)
check('it took two lost rounds', rounds, 2)
check('the loser is out of lives', app.user.lives <= 0, True)
check('the winner is the opponent', app.game.winner() is app.ai, True)

# The flag follows the rules, it is not a copy that can drift
app = fresh('north', seed=4)
app.user.lives = 0
check('a life lost elsewhere is noticed too', app.game_over, True)

# --- Arrow keys pick targets ------------------------------------------------

agile = [c for c in pool['scoiatael'] if c.is_agile][0]

app = fresh('scoiatael')
app.user.hand.clear()
app.user.hand.append(agile)
app.selected = 0
app.play_selected()
check('agile asks for a row', app.pending[0], 'agile')
check('two options offered', len(app.target_options()), 2)
check('cursor starts at 0', app.target_index, 0)

app.handle_key(pygame.K_RIGHT)
check('arrow moves the cursor', app.target_index, 1)
check('cursor points at the ranged row', app.current_target(), RANGED)
app.handle_key(pygame.K_RETURN)
settle(app)
check('enter plays into the chosen row', agile in app.user.rows[RANGED], True)

# The cursor wraps around
app = fresh('scoiatael')
app.user.hand.clear()
app.user.hand.append([c for c in pool['scoiatael'] if c.is_agile][1])
app.selected = 0
app.play_selected()
app.handle_key(pygame.K_LEFT)
check('cursor wraps backwards', app.target_index, 1)
app.handle_key(pygame.K_RIGHT)
check('cursor wraps forwards', app.target_index, 0)

# --- Medic via the keyboard, heroes excluded --------------------------------
medic = [c for c in pool['scoiatael'] if c.ability == 'medic'][0]
hero = [c for c in pool['scoiatael'] if c.hero][0]
unit = [c for c in pool['scoiatael'] if not c.hero and c.is_unit][0]

app = fresh('scoiatael', seed=9)
app.user.hand.clear()
app.user.hand.append(medic)
app.user.discard = [hero, unit]
app.selected = 0
app.play_selected()
check('medic opens the graveyard', app.grave_view, 'user')
options = [o[1] for o in app.target_options()]
check('hero is not offered', hero in options, False)
check('unit is offered', unit in options, True)
app.handle_key(pygame.K_RETURN)
settle(app)
check('enter revives the unit',
      any(unit in row for row in app.user.rows), True)

# A graveyard holding only heroes offers nothing
app = fresh('scoiatael', seed=9)
medic2 = [c for c in pool['scoiatael'] if c.ability == 'medic'][1]
app.user.hand.clear()
app.user.hand.append(medic2)
app.user.discard = [hero]
app.selected = 0
app.play_selected()
check('heroes alone do not open the graveyard', app.grave_view, None)
settle(app)
check('medic still played as a unit',
      any(medic2 in row for row in app.user.rows), True)

# --- Horn row picking by keyboard -------------------------------------------
horn = [c for c in pool['neutral'] if c.ability == 'horn' and c.is_special][0]
app = fresh('north')
app.user.hand.clear()
app.user.hand.append(horn)
app.selected = 0
app.play_selected()
check('horn offers three rows', len(app.target_options()), 3)
app.handle_key(pygame.K_RIGHT)
app.handle_key(pygame.K_RIGHT)
check('cursor on the siege row', app.current_target(), SIEGE)
app.handle_key(pygame.K_RETURN)
settle(app)
check('horn landed in the siege slot', app.user.horns[SIEGE] is horn, True)

# --- Bilingual names come from cards.json -----------------------------------
card = [c for c in pool['scoiatael'] if c.name == 'Zwergen-Scharmützler'][0]
check('german name', card.display_name('de'), 'Zwergen-Scharmützler')
check('english name', card.display_name('en'), 'Dwarven Skirmisher')
check('canonical name stays german', card.name, 'Zwergen-Scharmützler')

# Muster matches on the canonical name, so it survives a language switch
copies = [c for c in pool['scoiatael'] if c.name == 'Zwergen-Scharmützler']
check('muster identity is language proof',
      len({c.name for c in copies}), 1)

# --- Defaults ---------------------------------------------------------------
check('default player name', Settings().name, 'Geralt')
check('AI pause is noticeable', Gwint.AI_THINK_TIME >= 1.0, True)

# --- Agile is a Scoia'tael trait -------------------------------------------
check('nilfgaard has no agile units',
      any(c.is_agile for c in pool['nilfgaard']), False)
check('scoiatael has agile units',
      any(c.is_agile for c in pool['scoiatael']), True)

pygame.quit()

print()
if all(checks):
    print(f'All {len(checks)} regression checks passed.')
else:
    print(f'{checks.count(False)} of {len(checks)} regression checks FAILED.')
    raise SystemExit(1)

