"""Verifies cards.json against the card artwork.

Every card carries its row symbol at a fixed spot on the left edge. This test
reads that symbol and compares it with the row recorded in cards.json, so the
data can never silently drift away from the pictures again.

Method: templates are averaged from Northern Realms cards whose rows are
beyond doubt (the archive even numbers them in row order). Cards are matched
against those templates by correlation.

Needs numpy and the generated card images. If either is missing the test
skips instead of failing, so a fresh checkout without assets still runs.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bootstrap  # noqa: F401,E402  - sets sys.path, cwd and headless mode

import json  # noqa: E402

CARD_DIR = os.path.join('cards', 'de', 'large')

try:
    import numpy as np
    import pygame
except ImportError as exc:      # pragma: no cover - depends on the environment
    print(f'SKIP artwork verification: {exc}')
    raise SystemExit(0)

if not os.path.isdir(CARD_DIR):
    print('SKIP artwork verification: run tools/build_assets.py first')
    raise SystemExit(0)

pygame.init()
pygame.display.set_mode((1, 1))

# Region holding the row symbol, found by variance analysis over the card set
BOX = (14, 112, 62, 180)

# Rows here are certain. Non-hero Northern Realms units plus the agile group
# the clustering isolated on its own.
TEMPLATES = {
    'melee':  ['008', '009', '010', '013', '014', '015', '016'],
    'ranged': ['018', '019', '020', '021', '022', '023', '024'],
    'siege':  ['025', '026', '028', '030', '031', '032', '033'],
    'agile':  ['078', '079', '080', '081', '087', '094', '119', '137', '138'],
}

# Heroes and leader artwork style the corner differently, so the symbol is not
# readable on them. They are reported, never failed.
UNREADABLE = {'113', '163', '165', '167', '168', '170'}

MATCH = 0.80        # a card must reach this to count as recognised

checks = []


def check(label, ok, detail=''):
    checks.append(bool(ok))
    print(f'{"OK  " if ok else "FAIL"} {label}{" - " + detail if detail else ""}')


cache = {}


def patch(card_id):
    if card_id not in cache:
        path = os.path.join(CARD_DIR, f'{card_id}.png')
        if not os.path.exists(path):
            cache[card_id] = None
        else:
            surface = pygame.image.load(path).convert_alpha()
            arr = pygame.surfarray.array3d(surface).astype(np.float64)
            grey = arr[BOX[0]:BOX[2], BOX[1]:BOX[3]].mean(axis=2).ravel()
            cache[card_id] = (grey - grey.mean()) / (grey.std() + 1e-6)
    return cache[card_id]


def build(exclude=None):
    out = {}
    for row, ids in TEMPLATES.items():
        vecs = [patch(i) for i in ids if i != exclude]
        vecs = [v for v in vecs if v is not None]
        if vecs:
            out[row] = np.mean(vecs, axis=0)
    return out


def classify(card_id, templates):
    vec = patch(card_id)
    if vec is None:
        return None, 0.0
    scores = {r: float(np.dot(vec, t) / len(t)) for r, t in templates.items()}
    best = max(scores, key=scores.get)
    return best, scores[best]


templates = build()

# --- 1. the templates must be internally tight -----------------------------
for row, ids in TEMPLATES.items():
    sims = []
    for card_id in ids:
        vec = patch(card_id)
        if vec is None:
            continue
        sims.append(float(np.dot(vec, templates[row]) / len(templates[row])))
    if sims:
        check(f'template {row} is sharp ({min(sims):.2f})', min(sims) > 0.80,
              f'{min(sims):.2f}')

# --- 2. leave-one-out: can a card be placed without being in its template? --
for row, ids in TEMPLATES.items():
    for card_id in ids:
        reduced = build(exclude=card_id)
        predicted, score = classify(card_id, reduced)
        check(f'{card_id} recognised as {row} without itself',
              predicted == row, f'got {predicted} at {score:.2f}')

# --- 3. special and weather cards must NOT match a row symbol --------------
with open('cards.json', encoding='utf-8') as handle:
    data = json.load(handle)

for faction, cards in data.items():
    if faction.startswith('_'):
        continue
    for card in cards:
        if card['row'] not in ('special', 'weather'):
            continue
        predicted, score = classify(card['id'], templates)
        if predicted is None:
            continue
        check(f'{card["name"]["de"][:24]}: no row symbol on a special card',
              score < 0.50, f'{score:.2f}')

# --- 4. every unit card must match the row cards.json claims ---------------
mismatches = []
unreadable = []

for faction, cards in data.items():
    if faction.startswith('_'):
        continue
    for card in cards:
        if card['row'] in ('special', 'weather'):
            continue
        predicted, score = classify(card['id'], templates)
        if predicted is None:
            continue
        if score < MATCH:
            unreadable.append((card, predicted, score))
            continue
        if predicted != card['row']:
            mismatches.append((card, predicted, score))

for card, predicted, score in mismatches:
    check(f'{card["id"]} {card["name"]["de"][:24]}: row matches the artwork',
          False, f'json={card["row"]} artwork={predicted} ({score:.2f})')

check(f'all readable cards agree with their artwork ({len(mismatches)} off)',
      not mismatches)

# --- 5. the unreadable ones must be the known exceptions -------------------
unexpected = [c for c, _, _ in unreadable if c['id'] not in UNREADABLE]
check('only the known cards are unreadable',
      not unexpected,
      ', '.join(f'{c["id"]} {c["name"]["de"][:18]}' for c in unexpected[:4]))

if unreadable:
    print(f'\n     {len(unreadable)} cards with an unreadable symbol '
          f'(heroes and leader artwork):')
    for card, predicted, score in unreadable:
        print(f'       {card["id"]}  {card["name"]["de"][:28]:28s} '
              f'{card["row"]:7s} best guess {predicted} at {score:.2f}')

# --- 6. abilities ----------------------------------------------------------
# The ability icon sits below the row symbol. Its box also catches part of the
# card frame, which differs per faction, so each faction's own median is
# subtracted first - what remains is the icon.
ABILITY_BOX_F = (0.065, 0.440, 0.220, 0.550)
ABILITY_SEED = {
    'spy':    ['011', '012', '032', '042', '043', '048'],
    'medic':  ['031', '110', '041'],
    'muster': ['140', '143', '121', '130'],
    'bond':   ['013', '015', '022', '025'],
}
ABILITY_MATCH = 0.66
# Real icons cluster at 0.73 and above; cards without one peak at 0.59.
# That upper value is a row artifact - every agile card scores alike whatever
# its ability. 081, 087 and 089 sit in that band: the originals show no icon,
# so they are plain cards and must stay below the cut like any other.

print('\n--- ability icons ---')

raw_patch, owner = {}, {}
for faction, cards in data.items():
    if faction.startswith('_'):
        continue
    for card in cards:
        if card['row'] in ('special', 'weather'):
            continue
        path = os.path.join(CARD_DIR, f'{card["id"]}.png')
        if not os.path.exists(path):
            continue
        surface = pygame.image.load(path).convert_alpha()
        arr = pygame.surfarray.array3d(surface).astype(np.float64)
        w, h = surface.get_size()
        box = (int(w * ABILITY_BOX_F[0]), int(h * ABILITY_BOX_F[1]),
               int(w * ABILITY_BOX_F[2]), int(h * ABILITY_BOX_F[3]))
        raw_patch[card['id']] = arr[box[0]:box[2], box[1]:box[3]].mean(axis=2)
        owner[card['id']] = (faction, card)

if raw_patch:
    per_faction = {}
    for card_id, (faction, card) in owner.items():
        per_faction.setdefault(faction, []).append(raw_patch[card_id])
    frame = {f: np.median(np.stack(v), axis=0) for f, v in per_faction.items()}

    def ability_vector(card_id):
        diff = raw_patch[card_id] - frame[owner[card_id][0]]
        flat = diff.ravel()
        return (flat - flat.mean()) / (flat.std() + 1e-6)

    ability_templates = {}
    for ability, ids in ABILITY_SEED.items():
        vecs = [ability_vector(i) for i in ids if i in raw_patch]
        if vecs:
            ability_templates[ability] = np.mean(vecs, axis=0)

    # Plain cards must stay below the threshold, or the icon box is wrong
    plain_peak = 0.0
    for card_id, (faction, card) in owner.items():
        if card.get('ability'):
            continue
        vec = ability_vector(card_id)
        peak = max(float(np.dot(vec, t) / len(t))
                   for t in ability_templates.values())
        plain_peak = max(plain_peak, peak)

    check(f'cards without an ability stay below the cut ({plain_peak:.2f})',
          plain_peak < ABILITY_MATCH, f'{plain_peak:.2f}')

    ability_wrong, ability_ok = [], 0
    for card_id, (faction, card) in sorted(owner.items()):
        vec = ability_vector(card_id)
        scores = {a: float(np.dot(vec, t) / len(t))
                  for a, t in ability_templates.items()}
        best = max(scores, key=scores.get)
        if scores[best] < ABILITY_MATCH:
            continue        # no readable icon, nothing to compare
        if best != card.get('ability', ''):
            ability_wrong.append((card, best, scores[best]))

    for card, predicted, score in ability_wrong:
        check(f'{card["id"]} {card["name"]["de"][:22]}: ability matches',
              False,
              f'json={card.get("ability") or "-"} artwork={predicted} ({score:.2f})')

    check(f'every readable ability icon agrees ({len(ability_wrong)} off)',
          not ability_wrong)

    # The cards that prompted this check
    for card_id, expected in (('064', 'medic'), ('071', 'medic'),
                              ('133', 'muster'), ('154', 'muster')):
        if card_id in owner:
            check(f'{card_id} {owner[card_id][1]["name"]["de"][:20]} is {expected}',
                  owner[card_id][1].get('ability') == expected,
                  owner[card_id][1].get('ability') or '-')

    # Isengrim is a hero: the golden frame swallows his icon, so the box
    # reads nothing. Checked by eye on the original - he is a medic.
    if '076' in raw_patch:
        vec = ability_vector('076')
        peak = max(float(np.dot(vec, t) / len(t))
                   for t in ability_templates.values())
        check(f'076 Isengrim icon is unreadable on a hero frame ({peak:.2f})',
              peak < ABILITY_MATCH, f'{peak:.2f}')
        check('076 Isengrim is a medic in cards.json',
              owner['076'][1].get('ability') == 'medic',
              owner['076'][1].get('ability') or '-')

pygame.quit()

print()
if all(checks):
    print(f'All {len(checks)} artwork checks passed.')
else:
    print(f'{checks.count(False)} of {len(checks)} artwork checks FAILED.')
    raise SystemExit(1)

