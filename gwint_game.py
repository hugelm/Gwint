"""Gwent game state: players, board and card effects.

Also free of pygame so the whole flow stays unit-testable.
"""
import random

from gwint_rules import MELEE, RANGED, SIEGE, WEATHER_ROW, row_score, row_values

ROW_COUNT = 3


class Player(object):
    def __init__(self, name, deck, lives=2):
        self.name = name
        self.deck = list(deck)
        self.hand = []
        self.rows = [[] for _ in range(ROW_COUNT)]
        # Holds the actual horn card per row (or None) so the UI can draw it
        self.horns = [None] * ROW_COUNT
        self.discard = []
        self.lives = lives
        self.passed = False
        self.rounds_won = 0
        self.faction = ''

    # --- cards -------------------------------------------------------------
    def draw(self, count=1, rng=None):
        rng = rng or random
        drawn = []
        for _ in range(count):
            if not self.deck:
                break
            card = self.deck.pop(rng.randrange(len(self.deck)))
            self.hand.append(card)
            drawn.append(card)
        return drawn

    # --- scoring -----------------------------------------------------------
    def row_points(self, index, weather):
        return row_score(self.rows[index], index in weather, bool(self.horns[index]))

    def total_points(self, weather):
        return sum(self.row_points(i, weather) for i in range(ROW_COUNT))

    def units(self, weather):
        """Every unit on the board with its effective value and row index."""
        result = []
        for index in range(ROW_COUNT):
            values = row_values(self.rows[index], index in weather,
                                bool(self.horns[index]))
            for card, value in values:
                result.append((card, value, index))
        return result

    # --- end of round ------------------------------------------------------
    def clear_board(self):
        for row in self.rows:
            self.discard.extend(row)
        for horn in self.horns:
            if horn is not None:
                self.discard.append(horn)
        self.rows = [[] for _ in range(ROW_COUNT)]
        self.horns = [None] * ROW_COUNT
        self.passed = False


class Game(object):
    def __init__(self, player, opponent, rng=None):
        self.players = [player, opponent]
        # Row index -> weather card currently affecting that row
        self.weather_cards = {}
        self.rng = rng or random
        self.round = 1
        self.log = []
        self.last_effect = {}

    @property
    def weather(self):
        """Set of row indices currently under bad weather."""
        return set(self.weather_cards)

    def opponent_of(self, player):
        return self.players[1] if player is self.players[0] else self.players[0]

    def revivable(self, player):
        """Cards in the graveyard a medic is allowed to bring back."""
        return [c for c in player.discard if c.is_unit and not c.hero]

    # --- playing a card ----------------------------------------------------
    def play(self, player, card, target_row=None, decoy_target=None,
             medic_target=None):
        """Play a card from hand. Returns True when the move was legal.

        Side effects are reported through self.last_effect:
            {'drawn': [...]}     spy
            {'revived': card}    medic
            {'scorched': [...]}  scorch
            {'mustered': [...]}  muster
        """
        if card not in player.hand:
            return False

        self.last_effect = {}
        opponent = self.opponent_of(player)

        if card.ability == 'decoy':
            if not self._play_decoy(player, card, decoy_target):
                return False
            self.log.append(f'{player.name}: {card.name}')
            return True

        player.hand.remove(card)

        if card.is_weather:
            self._play_weather(player, card)
        elif card.ability == 'horn' and card.is_special:
            # The Commander's Horn occupies a row's horn slot.
            # Dandelion is a unit and falls through to the else branch.
            self._play_horn(player, card, target_row)
        elif card.ability == 'scorch':
            self._play_scorch()
            player.discard.append(card)
        elif card.ability == 'spy':
            row = target_row if target_row is not None else card.row_index
            opponent.rows[row].append(card)
            self.last_effect['drawn'] = player.draw(2, self.rng)
        elif card.ability == 'medic':
            self._place(player, card, target_row)
            self._play_medic(player, medic_target)
        elif card.ability == 'scorch_melee':
            self._place(player, card, target_row)
            self._play_scorch_melee(opponent)
        elif card.ability == 'muster':
            self._place(player, card, target_row)
            self._play_muster(player, card)
        else:
            self._place(player, card, target_row)

        self.log.append(f'{player.name}: {card.name}')
        return True

    # --- individual effects ------------------------------------------------
    def _place(self, player, card, target_row=None):
        row = target_row if target_row is not None else card.row_index
        if row is None:
            player.discard.append(card)
            return
        # An agile card may only go where it is allowed
        if card.is_unit and row not in card.allowed_rows:
            row = card.row_index
        player.rows[row].append(card)

    def _play_weather(self, player, card):
        if card.ability == 'clear':
            # Clear weather sends every active weather card to the graveyard
            for old in self.weather_cards.values():
                player.discard.append(old)
            self.weather_cards.clear()
            player.discard.append(card)
            return

        row = WEATHER_ROW[card.ability]
        previous = self.weather_cards.get(row)
        if previous is not None:
            player.discard.append(previous)
        self.weather_cards[row] = card

    def _play_horn(self, player, card, target_row):
        row = target_row if target_row is not None else MELEE
        previous = player.horns[row]
        if previous is not None:
            player.discard.append(previous)
        player.horns[row] = card

    def _play_scorch(self):
        """Scorch: destroys the strongest unit(s) on the whole board."""
        candidates = []
        for player in self.players:
            for unit, value, row in player.units(self.weather):
                if not unit.hero:
                    candidates.append((value, player, unit, row))

        if not candidates:
            return

        top = max(value for value, _, _, _ in candidates)
        burned = []
        for value, player, unit, row in candidates:
            if value == top:
                player.rows[row].remove(unit)
                player.discard.append(unit)
                burned.append(unit)
                self.log.append(f'- {unit.name} ({value})')
        self.last_effect['scorched'] = burned

    def _play_scorch_melee(self, opponent):
        """Villentretenmerth: hits the enemy melee row once it reaches 10+."""
        values = row_values(opponent.rows[MELEE], MELEE in self.weather,
                            bool(opponent.horns[MELEE]))
        if sum(v for _, v in values) < 10:
            return

        non_heroes = [(card, value) for card, value in values if not card.hero]
        if not non_heroes:
            return

        top = max(value for _, value in non_heroes)
        burned = []
        for card, value in non_heroes:
            if value == top:
                opponent.rows[MELEE].remove(card)
                opponent.discard.append(card)
                burned.append(card)
                self.log.append(f'- {card.name} ({value})')
        self.last_effect['scorched'] = burned

    def _play_medic(self, player, medic_target=None):
        """Medic: bring a unit back from the graveyard.

        medic_target allows an explicit pick, otherwise one is chosen at random.
        """
        units = self.revivable(player)
        if not units:
            return

        revived = medic_target if medic_target in units else self.rng.choice(units)
        player.discard.remove(revived)
        player.rows[revived.row_index].append(revived)
        self.last_effect['revived'] = revived
        self.log.append(f'+ {revived.name}')

        # A revived card triggers its own ability again
        if revived.ability == 'muster':
            self._play_muster(player, revived)

    def _play_muster(self, player, card):
        """Muster: pull every matching card from deck and hand.

        Matching is by Card.muster_key - normally the name, but the vampires
        and the two arachas cards share a group and muster together despite
        carrying different names.
        """
        pulled = []
        for source in (player.deck, player.hand):
            matches = [c for c in source
                       if c.musters_with(card) and c is not card]
            for other in matches:
                source.remove(other)
                # An agile card keeps its default row when pulled automatically
                player.rows[other.row_index].append(other)
                pulled.append(other)
        if pulled:
            self.last_effect['mustered'] = pulled
            self.log.append(f'+ {card.name} x{len(pulled) + 1}')

    def _play_decoy(self, player, card, decoy_target):
        """Decoy: swap one of your own units on the board for the decoy."""
        if decoy_target is None:
            return False
        for row in player.rows:
            if decoy_target in row:
                row[row.index(decoy_target)] = card
                player.hand.remove(card)
                player.hand.append(decoy_target)
                return True
        return False

    # --- rounds ------------------------------------------------------------
    def round_over(self):
        return all(p.passed for p in self.players)

    def resolve_round(self):
        """Score the round and return the winner (None on a draw)."""
        first, second = self.players
        score_first = first.total_points(self.weather)
        score_second = second.total_points(self.weather)

        if score_first > score_second:
            second.lives -= 1
            first.rounds_won += 1
            winner = first
        elif score_second > score_first:
            first.lives -= 1
            second.rounds_won += 1
            winner = second
        else:
            first.lives -= 1
            second.lives -= 1
            winner = None

        for player in self.players:
            player.clear_board()

        # Weather cards go to the graveyard of the first player
        for card in self.weather_cards.values():
            first.discard.append(card)
        self.weather_cards.clear()
        self.round += 1

        return winner

    @property
    def game_over(self):
        return any(p.lives <= 0 for p in self.players)

    def winner(self):
        if not self.game_over:
            return None
        alive = [p for p in self.players if p.lives > 0]
        return alive[0] if len(alive) == 1 else None

