"""Gwent rules engine.

Deliberately free of pygame so the whole rule set stays unit-testable.
Contains the card model, deck building and score calculation including
weather, commander's horn, tight bond, morale boost and hero immunity.
"""
import json
import os
import random

MELEE, RANGED, SIEGE = 0, 1, 2
ROW_NAMES = {'melee': MELEE, 'ranged': RANGED, 'siege': SIEGE}

# Agile units may be placed in close combat or in the ranged row
AGILE_ROWS = (MELEE, RANGED)

# Which weather ability disables which row
WEATHER_ROW = {'frost': MELEE, 'fog': RANGED, 'rain': SIEGE}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Card(object):
    __slots__ = ('id', 'names', 'strength', 'row', 'ability', 'hero', 'faction',
                 'muster_group')

    def __init__(self, id, name, strength, row, ability='', hero=False,
                 faction='', name_en=None, muster_group=''):
        # Names live on the card itself, not in the translation catalogue.
        # The German name is the identity muster and tight bond compare on.
        if isinstance(name, dict):
            self.names = {'de': name.get('de', ''), 'en': name.get('en', '')}
        else:
            self.names = {'de': name, 'en': name_en or name}
        self.id = id
        self.strength = strength
        self.row = row
        self.ability = ability
        self.hero = hero
        self.faction = faction
        # Cards sharing this value muster together despite different names
        self.muster_group = muster_group

    @property
    def name(self):
        """Canonical name - stays German so card identity is language proof."""
        return self.names['de']

    @property
    def muster_key(self):
        """What muster matches on: the shared group, or the name."""
        return self.muster_group or self.names['de']

    def musters_with(self, other):
        """True when both cards are pulled by the same muster card."""
        return self.muster_key == other.muster_key

    def display_name(self, language='de'):
        return self.names.get(language) or self.names['de']

    @property
    def is_weather(self):
        return self.row == 'weather'

    @property
    def is_special(self):
        return self.row in ('special', 'weather')

    @property
    def is_unit(self):
        return not self.is_special

    @property
    def is_agile(self):
        """True for units that can go into close combat or ranged."""
        return self.row == 'agile'

    @property
    def row_index(self):
        """Default row for units, None for special cards.

        Agile cards default to close combat; the player picks the row when
        playing them.
        """
        if self.row == 'agile':
            return MELEE
        return ROW_NAMES.get(self.row)

    @property
    def allowed_rows(self):
        """Every row this card may legally be placed in."""
        if self.is_special:
            return ()
        if self.is_agile:
            return AGILE_ROWS
        return (ROW_NAMES[self.row],)

    def __repr__(self):
        return f'<Card {self.name} {self.strength} {self.row} {self.ability}>'


def load_card_pool(path=None):
    """Read cards.json and return {faction: [Card, ...]} with counts expanded."""
    path = path or os.path.join(BASE_DIR, 'cards.json')
    with open(path, encoding='utf-8') as handle:
        raw = json.load(handle)

    pool = {}
    for faction, entries in raw.items():
        if faction.startswith('_'):
            continue
        cards = []
        for entry in entries:
            for _ in range(entry.get('count', 1)):
                cards.append(Card(
                    id=entry['id'],
                    name=entry['name'],          # {'de': ..., 'en': ...}
                    strength=entry.get('strength', 0),
                    row=entry['row'],
                    ability=entry.get('ability', ''),
                    hero=entry.get('hero', False),
                    faction=faction,
                    muster_group=entry.get('muster_group', ''),
                ))
        pool[faction] = cards
    return pool


def build_deck(faction, pool=None, neutral_count=6, rng=None):
    """Build a deck from one faction plus a random pick of neutral cards."""
    pool = pool if pool is not None else load_card_pool()
    rng = rng or random

    if faction not in pool:
        raise ValueError(f'Unknown faction: {faction}')

    deck = list(pool[faction])

    neutrals = list(pool.get('neutral', []))
    rng.shuffle(neutrals)
    deck += neutrals[:neutral_count]

    rng.shuffle(deck)
    return deck


def row_values(cards, weather=False, horn=False):
    """Return [(card, effective value), ...] for every unit in the row.

    Order of operations follows the original game:
    weather -> tight bond -> morale boost -> commander's horn.
    Heroes ignore weather only.
    """
    bond_counts = {}
    for card in cards:
        if card.ability == 'bond':
            bond_counts[card.name] = bond_counts.get(card.name, 0) + 1

    morale = sum(1 for card in cards if card.ability == 'morale')
    horn_active = bool(horn) or any(card.ability == 'horn' for card in cards)

    values = []
    for card in cards:
        if card.is_special:
            continue

        value = 1 if (weather and not card.hero) else card.strength

        if card.ability == 'bond':
            value *= bond_counts[card.name]

        # Morale boost applies to every other card in the row
        value += morale - 1 if card.ability == 'morale' else morale

        if horn_active and card.ability != 'horn':
            value *= 2

        values.append((card, value))

    return values


def row_score(cards, weather=False, horn=False):
    """Total score of a single row."""
    return sum(value for _, value in row_values(cards, weather, horn))


def card_value(card, cards, weather=False, horn=False):
    """Effective strength of one card inside its row (used by scorch/UI)."""
    for entry, value in row_values(cards, weather, horn):
        if entry is card:
            return value
    return 0

