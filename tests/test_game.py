"""Tests for gwint_game - card effects and round logic. Runs without pygame."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bootstrap  # noqa: F401,E402  - sets sys.path, cwd and headless mode

import random

from gwint_game import Game, Player
from gwint_rules import MELEE, RANGED, SIEGE, Card

checks = []

def check(label, got, expected):
    ok = got == expected
    checks.append(ok)
    print(f'{"OK  " if ok else "FAIL"} {label}: {got} (expected {expected})')

def unit(name, strength, row='melee', ability='', hero=False):
    return Card(id='000', name=name, strength=strength, row=row,
                ability=ability, hero=hero)

def special(name, ability, row='special'):
    return Card(id='000', name=name, strength=0, row=row, ability=ability)

def new_game(seed=1):
    a = Player('A', [])
    b = Player('B', [])
    return Game(a, b, rng=random.Random(seed)), a, b

# --- playing a unit ---------------------------------------------------------
g, a, b = new_game()
c = unit('Ves', 5)
a.hand.append(c)
check('play a unit', g.play(a, c), True)
check('unit sits in the melee row', len(a.rows[MELEE]), 1)
check('hand is empty', len(a.hand), 0)
check('score', a.total_points(g.weather), 5)

# --- weather ----------------------------------------------------------------
g, a, b = new_game()
a.rows[MELEE] = [unit('x', 7), unit('y', 6)]
b.rows[MELEE] = [unit('z', 10)]
frost = special('Biting Frost', 'frost', 'weather')
a.hand.append(frost)
g.play(a, frost)
check('frost hits both sides (A)', a.total_points(g.weather), 2)
check('frost hits both sides (B)', b.total_points(g.weather), 1)
check('frost card stays on the board', g.weather_cards.get(MELEE) is frost, True)
check('ranged row untouched', RANGED in g.weather, False)

clear = special('Clear Weather', 'clear', 'weather')
a.hand.append(clear)
g.play(a, clear)
check('clear weather resets the board', a.total_points(g.weather), 13)
check('clear weather discards the frost card', frost in a.discard, True)

# Hero ignores weather
g, a, b = new_game()
a.rows[MELEE] = [unit('Hero', 10, hero=True), unit('x', 7)]
fog = special('Frost', 'frost', 'weather')
a.hand.append(fog)
g.play(a, fog)
check('hero ignores frost', a.total_points(g.weather), 11)

# --- commander's horn -------------------------------------------------------
g, a, b = new_game()
a.rows[SIEGE] = [unit('Catapult', 8, 'siege')]
horn = special("Commander's Horn", 'horn')
a.hand.append(horn)
g.play(a, horn, target_row=SIEGE)
check('horn doubles the target row', a.total_points(g.weather), 16)
check('horn slot holds the card', a.horns[SIEGE] is horn, True)
check('horn is not on the discard pile', horn in a.discard, False)

# Dandelion is a unit, not a horn slot
g, a, b = new_game()
a.rows[MELEE] = [unit('x', 5)]
dandelion = unit('Dandelion', 2, 'melee', 'horn')
a.hand.append(dandelion)
g.play(a, dandelion)
check('dandelion lands as a unit', len(a.rows[MELEE]), 2)
check('dandelion takes no horn slot', a.horns[MELEE], None)
check('dandelion doubles others (5*2 + 2)', a.total_points(g.weather), 12)

# --- scorch -----------------------------------------------------------------
g, a, b = new_game()
a.rows[MELEE] = [unit('small', 3)]
b.rows[RANGED] = [unit('big', 11), unit('medium', 4)]
scorch = special('Scorch', 'scorch')
a.hand.append(scorch)
g.play(a, scorch)
check('scorch hits the strongest card', len(b.rows[RANGED]), 1)
check('weaker card survives', b.rows[RANGED][0].name, 'medium')
check('own weak card stays', len(a.rows[MELEE]), 1)

# Scorch hits every card sharing the top value, including your own
g, a, b = new_game()
a.rows[MELEE] = [unit('tie', 9)]
b.rows[MELEE] = [unit('tie2', 9), unit('small', 2)]
s2 = special('Scorch', 'scorch')
a.hand.append(s2)
g.play(a, s2)
check('scorch hits both sides', (len(a.rows[MELEE]), len(b.rows[MELEE])), (0, 1))

# Heroes are immune
g, a, b = new_game()
b.rows[MELEE] = [unit('Geralt', 15, hero=True), unit('normal', 6)]
s3 = special('Scorch', 'scorch')
a.hand.append(s3)
g.play(a, s3)
check('hero survives scorch', len(b.rows[MELEE]), 1)
check('hero stayed on the board', b.rows[MELEE][0].name, 'Geralt')
check('scorch reports its victims',
      [c.name for c in g.last_effect.get('scorched', [])], ['normal'])

# --- spy --------------------------------------------------------------------
g, a, b = new_game()
a.deck = [unit('d1', 1), unit('d2', 2), unit('d3', 3)]
spy = unit('Thaler', 1, 'siege', 'spy')
a.hand.append(spy)
g.play(a, spy)
check('spy lands with the opponent', len(b.rows[SIEGE]), 1)
check('spy draws 2 cards', len(a.hand), 2)
check('deck shrank by 2', len(a.deck), 1)
check('spy reports the drawn cards', len(g.last_effect.get('drawn', [])), 2)
check('drawn cards are in hand',
      all(c in a.hand for c in g.last_effect['drawn']), True)

# Spy with an empty deck
g, a, b = new_game()
sp2 = unit('Thaler', 1, 'siege', 'spy')
a.hand.append(sp2)
g.play(a, sp2)
check('spy with an empty deck', len(g.last_effect.get('drawn', [])), 0)

# --- medic ------------------------------------------------------------------
g, a, b = new_game()
a.discard = [unit('dead', 6, 'ranged')]
medic = unit('Medic', 5, 'siege', 'medic')
a.hand.append(medic)
g.play(a, medic)
check('medic sits on the board', len(a.rows[SIEGE]), 1)
check('revived card in the ranged row', len(a.rows[RANGED]), 1)
check('graveyard emptied', len(a.discard), 0)

# Medic with an empty graveyard must not crash
g, a, b = new_game()
m2 = unit('Medic', 5, 'siege', 'medic')
a.hand.append(m2)
check('medic without a graveyard', g.play(a, m2), True)

# Medic with an explicit pick
g, a, b = new_game()
wanted = unit('Catapult', 8, 'siege')
a.discard = [unit('other', 1, 'melee'), wanted, unit('another', 2, 'melee')]
m3 = unit('Medic', 5, 'siege', 'medic')
a.hand.append(m3)
g.play(a, m3, medic_target=wanted)
check('medic revives the chosen card', wanted in a.rows[SIEGE], True)
check('medic reports the revival', g.last_effect.get('revived') is wanted, True)
check('other cards stay in the graveyard', len(a.discard), 2)

# Heroes and special cards cannot be revived
g, a, b = new_game()
a.discard = [unit('Geralt', 15, 'melee', hero=True)]
check('heroes not revivable', g.revivable(a), [])

g, a, b = new_game()
a.discard = [special('Scorch', 'scorch')]
check('special cards not revivable', g.revivable(a), [])

# A revived muster card triggers again
g, a, b = new_game()
dead = unit('Nekker', 2, 'melee', 'muster')
a.discard = [dead]
a.deck = [unit('Nekker', 2, 'melee', 'muster')]
m4 = unit('Medic', 5, 'siege', 'medic')
a.hand.append(m4)
g.play(a, m4, medic_target=dead)
check('revived muster pulls again', len(a.rows[MELEE]), 2)

# --- decoy ------------------------------------------------------------------
g, a, b = new_game()
target = unit('Catapult', 8, 'siege')
a.rows[SIEGE] = [target]
decoy = special('Decoy', 'decoy')
a.hand.append(decoy)
check('play the decoy', g.play(a, decoy, decoy_target=target), True)
check('decoy sits on the board', a.rows[SIEGE][0].name, 'Decoy')
check('unit returned to hand', a.hand[0].name, 'Catapult')
check('decoy scores nothing', a.total_points(g.weather), 0)

g, a, b = new_game()
d2 = special('Decoy', 'decoy')
a.hand.append(d2)
check('decoy without a target rejected', g.play(a, d2), False)
check('decoy stays in hand', len(a.hand), 1)

# --- Villentretenmerth ------------------------------------------------------
g, a, b = new_game()
b.rows[MELEE] = [unit('big', 12), unit('thin', 3)]
villen = unit('Villentretenmerth', 7, 'melee', 'scorch_melee', hero=True)
a.hand.append(villen)
g.play(a, villen)
check('villentretenmerth burns the strongest melee card', len(b.rows[MELEE]), 1)
check('weak card stays', b.rows[MELEE][0].name, 'thin')

g, a, b = new_game()
b.rows[MELEE] = [unit('small', 4)]
v2 = unit('Villentretenmerth', 7, 'melee', 'scorch_melee', hero=True)
a.hand.append(v2)
g.play(a, v2)
check('villentretenmerth idle below 10 points', len(b.rows[MELEE]), 1)

# --- muster -----------------------------------------------------------------
g, a, b = new_game()
n1 = unit('Nekker', 2, 'melee', 'muster')
n2 = unit('Nekker', 2, 'melee', 'muster')
n3 = unit('Nekker', 2, 'melee', 'muster')
other = unit('Ghoul', 1, 'melee', 'muster')
a.hand.extend([n1, n2])
a.deck.extend([n3, other])
g.play(a, n1)
check('muster pulls every copy', len(a.rows[MELEE]), 3)
check('muster clears duplicates from hand', n2 in a.hand, False)
check('muster pulls from the deck', n3 in a.deck, False)
check('muster leaves other cards alone', other in a.deck, True)
check('muster score 3x2', a.total_points(g.weather), 6)
check('muster reports the pulled cards', len(g.last_effect.get('mustered', [])), 2)

g, a, b = new_game()
solo = unit('Nekker', 2, 'melee', 'muster')
a.hand.append(solo)
g.play(a, solo)
check('single muster card', len(a.rows[MELEE]), 1)

# --- rounds -----------------------------------------------------------------
g, a, b = new_game()
a.rows[MELEE] = [unit('x', 10)]
b.rows[MELEE] = [unit('y', 5)]
a.passed = b.passed = True
check('round is over', g.round_over(), True)
winner = g.resolve_round()
check('A wins the round', winner is a, True)
check('B loses a life', b.lives, 1)
check('board cleared', (len(a.rows[MELEE]), len(b.rows[MELEE])), (0, 0))
check('graveyards filled', (len(a.discard), len(b.discard)), (1, 1))
check('passed flags reset', (a.passed, b.passed), (False, False))

# Horn cards also go to the graveyard at the end of a round
g, a, b = new_game()
horn2 = special("Commander's Horn", 'horn')
a.hand.append(horn2)
g.play(a, horn2, target_row=MELEE)
a.passed = b.passed = True
g.resolve_round()
check('horn discarded at the end of the round', horn2 in a.discard, True)
check('horn slot cleared', a.horns[MELEE], None)

# A draw costs both players a life
g, a, b = new_game()
a.rows[MELEE] = [unit('x', 7)]
b.rows[MELEE] = [unit('y', 7)]
check('draw has no winner', g.resolve_round(), None)
check('both lose a life', (a.lives, b.lives), (1, 1))

# End of game
g, a, b = new_game()
a.lives = 1
b.rows[MELEE] = [unit('y', 7)]
g.resolve_round()
check('game over', g.game_over, True)
check('B wins the game', g.winner() is b, True)

# Weather is cleared between rounds
g, a, b = new_game()
w = special('Frost', 'frost', 'weather')
a.hand.append(w)
g.play(a, w)
g.resolve_round()
check('weather cleared after the round', len(g.weather), 0)
check('weather card discarded', w in a.discard, True)

# --- drawing past the end of the deck ---------------------------------------
p = Player('X', [unit('a', 1)])
p.draw(5, random.Random(1))
check('drawing past the deck size', (len(p.hand), len(p.deck)), (1, 0))

print()
if all(checks):
    print(f'All {len(checks)} game checks passed.')
else:
    print(f'{checks.count(False)} of {len(checks)} game checks FAILED.')
    raise SystemExit(1)

