"""Tests for the interaction layer: animation order, medic picking, slots."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bootstrap  # noqa: F401,E402  - sets sys.path, cwd and headless mode

import random

import pygame  # noqa: E402

import Gwint  # noqa: E402
from gwint_rules import MELEE, RANGED, SIEGE, Card  # noqa: E402

checks = []

def check(label, got, expected):
    ok = got == expected
    checks.append(ok)
    print(f'{"OK  " if ok else "FAIL"} {label}: {got} (expected {expected})')

def fresh(language='de'):
    random.seed(4)
    app = Gwint.GwintApp('Tester', language, intro=False)
    app.user_turn = True
    app.user.passed = app.ai.passed = False
    return app

def settle(app, seconds=1.5, step=0.05):
    """Run the timers until every animation has landed."""
    elapsed = 0.0
    while elapsed < seconds and app.busy:
        app.tick_timers(step)
        elapsed += step

pygame.init()

# --- a played card appears only after its flight ----------------------------
app = fresh()
card = Card('009', 'Ves', 5, 'melee')
app.user.hand.clear()
app.user.hand.append(card)
app.selected = 0
app.play_selected()

check('card is in flight', card in app.flying, True)
check('board still empty during flight', len(app.user.rows[MELEE]), 0)
check('card hidden from hand', card in app.visible_hand(), False)
check('an animation is running', len(app.animations) >= 1, True)
check('game busy during flight', app.busy, True)

app.tick_timers(0.2)
check('board still empty mid flight', len(app.user.rows[MELEE]), 0)

settle(app)
check('card on the board after landing', len(app.user.rows[MELEE]), 1)
check('flight list empty', app.flying, [])
check('points counted after landing', app.user.total_points(app.game.weather), 5)

# --- weather card lands in the weather slot ---------------------------------
app = fresh()
frost = Card('159', 'Klirrende Kälte', 0, 'weather', 'frost')
app.user.hand.clear()
app.user.hand.append(frost)
app.selected = 0
app.play_selected()
check('weather not active during flight', app.game.weather, set())
settle(app)
check('weather active after landing', MELEE in app.game.weather, True)
check('weather card kept for drawing',
      app.game.weather_cards.get(MELEE) is frost, True)

# --- commander's horn needs a row and lands in the horn slot ----------------
app = fresh()
horn = Card('157', 'Horn des Kommandanten', 0, 'special', 'horn')
app.user.hand.clear()
app.user.hand.append(horn)
app.selected = 0
app.play_selected()
check('horn asks for a row', app.pending[0] if app.pending else None, 'horn')
check('horn not played yet', app.user.horns, [None, None, None])

# Click the siege row slot
slot_index = Gwint.ROW_LAYOUT.index(('user', SIEGE))
app.handle_click(app.layout.horn_slot(slot_index).center)
settle(app)
check('horn in the siege slot', app.user.horns[SIEGE] is horn, True)
check('horn target cleared', app.pending, None)

# --- medic: graveyard opens and the click revives the chosen card -----------
app = fresh()
medic = Card('031', 'Heilerin', 5, 'siege', 'medic')
wanted = Card('025', 'Katapult', 8, 'siege')
app.user.hand.clear()
app.user.hand.append(medic)
app.user.discard.extend([Card('016', 'Fusssoldat', 1, 'melee'), wanted])
app.selected = 0
app.play_selected()

check('medic opens the graveyard', app.grave_view, 'user')
check('medic waits for a pick', app.pending[0] if app.pending else None, 'medic')
rects = app.grave_rects()
check('graveyard shows both cards', len(rects), 2)

target_rect = [r for c, r in rects if c is wanted][0]
app.handle_click(target_rect.center)
settle(app)
check('chosen card was revived', wanted in app.user.rows[SIEGE], True)
check('other card stays in the graveyard', len(app.user.discard), 1)
check('graveyard closed again', app.grave_view, None)

# --- medic with an empty graveyard just plays the unit ----------------------
app = fresh()
medic2 = Card('031', 'Heilerin', 5, 'siege', 'medic')
app.user.hand.clear()
app.user.hand.append(medic2)
app.user.discard.clear()
app.selected = 0
app.play_selected()
check('no graveyard for an empty pile', app.grave_view, None)
settle(app)
check('medic played as a normal unit', medic2 in app.user.rows[SIEGE], True)

# --- heroes cannot be revived ----------------------------------------------
app = fresh()
medic3 = Card('031', 'Heilerin', 5, 'siege', 'medic')
app.user.hand.clear()
app.user.hand.append(medic3)
app.user.discard.append(Card('163', 'Geralt', 15, 'melee', hero=True))
app.selected = 0
app.play_selected()
check('hero alone does not open the graveyard', app.grave_view, None)

# --- spy reveals the drawn cards --------------------------------------------
app = fresh()
spy = Card('032', 'Thaler', 1, 'siege', 'spy')
app.user.hand.clear()
app.user.hand.append(spy)
app.user.deck = [Card('026', 'Tribok', 6, 'siege'), Card('028', 'Ballista', 6, 'siege')]
app.selected = 0
app.play_selected()
settle(app)
check('spy landed with the opponent', len(app.ai.rows[SIEGE]), 1)
check('drawn cards are revealed', len(app.spy_reveal), 2)

# --- AI moves animate as well ----------------------------------------------
app = fresh()
app.user_turn = False
app.ai.hand.clear()
ai_card = Card('009', 'Ves', 5, 'melee')
app.ai.hand.append(ai_card)
app.ai_move()
check('AI card in flight', ai_card in app.flying, True)
check('AI board empty during flight', len(app.ai.rows[MELEE]), 0)
settle(app)
check('AI card on the board after landing', len(app.ai.rows[MELEE]), 1)

# --- no input while a card is flying ----------------------------------------
app = fresh()
c1 = Card('009', 'Ves', 5, 'melee')
c2 = Card('010', 'Siegfried', 5, 'melee')
app.user.hand.clear()
app.user.hand.extend([c1, c2])
app.selected = 0
app.play_selected()
app.selected = 0
app.play_selected()     # must be ignored
check('only one card in flight', len(app.flying), 1)
settle(app)
check('exactly one card landed', len(app.user.rows[MELEE]), 1)

# --- turn handover: after your move the opponent must act -------------------
app = fresh()
c1 = Card('009', 'Ves', 5, 'melee')
app.user.hand.clear()
app.user.hand.append(c1)
app.user.hand.append(Card('010', 'Siegfried', 5, 'melee'))
app.ai.hand.clear()
app.ai.hand.append(Card('011', 'Yarpen', 2, 'melee'))
app.selected = 0
app.play_selected()
settle(app)
check('after your move it is the opponent turn', app.user_turn, False)

app.ai_move()
settle(app)
check('after the AI move it is your turn again', app.user_turn, True)
check('AI actually played a card', len(app.ai.rows[Gwint.MELEE]), 1)

# A passed opponent hands the turn straight back
app = fresh()
app.user.hand.clear()
app.user.hand.extend([Card('009', 'Ves', 5, 'melee'),
                      Card('010', 'Siegfried', 5, 'melee')])
app.ai.passed = True
app.selected = 0
app.play_selected()
settle(app)
check('passed opponent gives the turn back', app.user_turn, True)

# The AI keeps playing over several exchanges
app = fresh()
app.user.hand.clear()
app.ai.hand.clear()
for i in range(4):
    app.user.hand.append(Card('009', f'U{i}', 5, 'melee'))
    app.ai.hand.append(Card('011', f'A{i}', 4, 'melee'))

exchanges = 0
for _ in range(8):
    if app.user_turn and app.user.hand:
        app.selected = 0
        app.play_selected()
        settle(app)
    elif not app.ai.passed and app.ai.hand:
        app.ai_move()
        settle(app)
        exchanges += 1
    if app.game_over:
        break
check('AI played in several exchanges', exchanges >= 3, True)
# The board may already be cleared by a finished round, so check the log
log = ' | '.join(app.game.log)
check('both sides appear in the log',
      app.user.name in log and app.ai.name in log, True)

# --- agile cards can go into close combat or ranged -------------------------
app = fresh()
agile = Card('079', 'Yaevinn', 10, 'agile')
check('agile card knows both rows', agile.allowed_rows, (MELEE, RANGED))
app.user.hand.clear()
app.user.hand.append(agile)
app.selected = 0
app.play_selected()
check('agile card asks for a row', app.pending[0] if app.pending else None, 'agile')
check('agile card not played yet', len(app.user.rows[MELEE]), 0)

ranged_index = Gwint.ROW_LAYOUT.index(('user', RANGED))
app.handle_click(app.layout.row_rect(ranged_index).center)
settle(app)
check('agile card landed in the ranged row', agile in app.user.rows[RANGED], True)
check('melee row stayed empty', len(app.user.rows[MELEE]), 0)

# The same card into close combat
app = fresh()
agile2 = Card('079', 'Yaevinn', 10, 'agile')
app.user.hand.clear()
app.user.hand.append(agile2)
app.selected = 0
app.play_selected()
melee_index = Gwint.ROW_LAYOUT.index(('user', MELEE))
app.handle_click(app.layout.row_rect(melee_index).center)
settle(app)
check('agile card landed in close combat', agile2 in app.user.rows[MELEE], True)

# The siege row must not accept it
app = fresh()
agile3 = Card('079', 'Yaevinn', 10, 'agile')
app.user.hand.clear()
app.user.hand.append(agile3)
app.selected = 0
app.play_selected()
siege_index = Gwint.ROW_LAYOUT.index(('user', SIEGE))
app.handle_click(app.layout.row_rect(siege_index).center)
check('siege row rejects an agile card', app.pending is not None, True)
check('agile card still in hand', agile3 in app.user.hand, True)

# The AI picks a row for agile cards too
app = fresh()
app.user_turn = False
app.ai.hand.clear()
ai_agile = Card('079', 'Yaevinn', 10, 'agile')
app.ai.hand.append(ai_agile)
app.ai_move()
settle(app)
check('AI placed the agile card',
      ai_agile in app.ai.rows[MELEE] or ai_agile in app.ai.rows[RANGED], True)

# --- intro blocks play and can be skipped -----------------------------------

random.seed(1)
app = Gwint.GwintApp('Tester', 'de', intro=True)
check('intro is running', app.intro_running, True)
app.user_turn = True
before = len(app.user.hand)
app.selected = 0
app.play_selected()
check('no move during the intro', len(app.user.hand), before)
app.handle_click((10, 10))
check('click skips the intro', app.intro_running, False)

# --- layout offers weather and horn slots -----------------------------------
lay = app.layout
for i in range(6):
    w = lay.weather_slot(i)
    h = lay.horn_slot(i)
    row = lay.row_rect(i)
    checks.append(row.contains(w) and row.contains(h))
print(f'OK   weather and horn slots sit inside their rows')
checks.append(True)

# --- rendering works in both languages --------------------------------------
for lang in ('de', 'en'):
    app.tr.language = lang
    app.render()
print('OK   render works in both languages')
checks.append(True)

pygame.quit()

print()
if all(checks):
    print(f'All {len(checks)} interaction checks passed.')
else:
    print(f'{checks.count(False)} of {len(checks)} interaction checks FAILED.')
    raise SystemExit(1)

