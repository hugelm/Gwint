"""Gwent - the card game from The Witcher 3.

Controls are listed in README.md and in the sidebar during play.
"""
import os
import random

import pygame

from gwint_config import from_command_line
from gwint_game import Game, Player
from gwint_i18n import LANGUAGES, Translator
from gwint_rules import MELEE, RANGED, SIEGE, WEATHER_ROW, build_deck, load_card_pool
from gwint_ui import (BG_DARK, BLUE_FROST, GOLD, GOLD_DIM, GREEN, INK, PANEL,
                      PANEL_LIGHT, PARCHMENT, RED, ROW_MELEE, ROW_RANGED,
                      ROW_SIEGE, ROW_WEATHER, WHITE, Layout, badge, card_image,
                      ease_in_out, ease_out_cubic, fit_text, glow_rect, panel,
                      scaled_card, set_language, spread_positions, text,
                      vgradient)

os.chdir(os.path.dirname(os.path.abspath(__file__)))

WIDTH, HEIGHT = 1600, 900
MIN_SIZE = (1180, 720)
FPS = 60

FLIGHT_TIME = 0.42      # how long a card flies before it lands
AI_THINK_TIME = 1.4     # pause before the AI acts, so its move is readable

# Rows from top to bottom
ROW_LAYOUT = [
    ('ai', SIEGE), ('ai', RANGED), ('ai', MELEE),
    ('user', MELEE), ('user', RANGED), ('user', SIEGE),
]
ROW_COLORS = {MELEE: ROW_MELEE, RANGED: ROW_RANGED, SIEGE: ROW_SIEGE}


class CardFlight(object):
    """Animates a card from one point to another."""

    def __init__(self, card_id, start, end, duration=FLIGHT_TIME,
                 start_size=None, end_size=None):
        self.card_id = card_id
        self.start = pygame.Vector2(start)
        self.end = pygame.Vector2(end)
        self.duration = max(0.05, duration)
        self.elapsed = 0.0
        self.start_size = start_size
        self.end_size = end_size

    @property
    def done(self):
        return self.elapsed >= self.duration

    def update(self, dt):
        self.elapsed += dt

    def draw(self, surface, default_size):
        t = min(1.0, self.elapsed / self.duration)
        eased = ease_out_cubic(t)
        pos = self.start.lerp(self.end, eased)

        begin = self.start_size or default_size
        finish = self.end_size or default_size
        size = (round(begin[0] + (finish[0] - begin[0]) * eased),
                round(begin[1] + (finish[1] - begin[1]) * eased))

        # Lift the card slightly in the middle of the flight
        lift = 1.0 + 0.22 * (1 - abs(0.5 - t) * 2)
        size = (max(1, round(size[0] * lift)), max(1, round(size[1] * lift)))

        image = scaled_card(self.card_id, size)
        rect = image.get_rect(center=(round(pos.x), round(pos.y)))
        glow_rect(surface, rect, GOLD, alpha=int(130 * (1 - abs(0.5 - t) * 2)))
        surface.blit(image, rect)


class Intro(object):
    """Title sequence: cards fan in, then the board fades in."""

    FAN_IN = 1.1
    HOLD = 0.8
    FADE = 0.7

    def __init__(self, card_ids):
        self.card_ids = card_ids
        self.elapsed = 0.0

    @property
    def total(self):
        return self.FAN_IN + self.HOLD + self.FADE

    @property
    def done(self):
        return self.elapsed >= self.total

    def update(self, dt):
        self.elapsed += dt

    def skip(self):
        self.elapsed = self.total

    def draw(self, surface, layout, title, subtitle):
        w, h = layout.width, layout.height
        t = self.elapsed

        fade_out = 0.0
        if t > self.FAN_IN + self.HOLD:
            fade_out = (t - self.FAN_IN - self.HOLD) / self.FADE

        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((*BG_DARK, int(255 * (1 - fade_out))))
        surface.blit(overlay, (0, 0))
        if fade_out >= 1.0:
            return

        alpha = 1 - fade_out
        cx, cy = w // 2, h // 2 - 20
        count = len(self.card_ids)

        for i, card_id in enumerate(self.card_ids):
            delay = i * 0.08
            local = (t - delay) / self.FAN_IN
            if local <= 0:
                continue
            progress = ease_out_cubic(min(1.0, local))

            angle = (i - (count - 1) / 2) * 9
            spread_x = (i - (count - 1) / 2) * 76
            start_y = cy + 420

            x = cx + spread_x * progress
            y = start_y + (cy - start_y) * progress

            image = scaled_card(card_id, (120, 181))
            image = pygame.transform.rotozoom(image, -angle * progress, 1.0)
            image.set_alpha(int(255 * alpha))
            surface.blit(image, image.get_rect(center=(round(x), round(y))))

        if t > self.FAN_IN * 0.55:
            reveal = min(1.0, (t - self.FAN_IN * 0.55) / 0.5) * alpha
            title_font = pygame.font.SysFont('Georgia,serif', 92, bold=True)
            rendered = title_font.render(title, True, GOLD)
            rendered.set_alpha(int(255 * reveal))
            surface.blit(rendered, rendered.get_rect(center=(cx, cy - 250)))

            sub_font = pygame.font.SysFont('Georgia,serif', 24)
            sub = sub_font.render(subtitle, True, PARCHMENT)
            sub.set_alpha(int(210 * reveal))
            surface.blit(sub, sub.get_rect(center=(cx, cy + 250)))


class GwintApp(object):
    def __init__(self, player_name='Spieler', language='de', intro=True,
                 music=True, fullscreen=False):
        pygame.init()
        self.tr = Translator(language)
        set_language(self.tr.language)

        pygame.display.set_caption(self.tr('game_title'))
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        self.set_window_icon()
        self.layout = Layout(WIDTH, HEIGHT)
        self.clock = pygame.time.Clock()
        self.fullscreen = False

        self.player_name = player_name
        self.music_enabled = music
        self.pool = load_card_pool()
        self.factions = sorted(f for f in self.pool if f != 'neutral')

        self.sounds = self._load_sounds()
        if music:
            self._load_music()

        self.message = ''
        self.message_timer = 0.0
        self.ai_timer = 0.0
        self.hover_card = None
        self.pending = None        # ('horn'|'agile'|'decoy'|'medic', card)
        self.target_index = 0      # arrow key cursor while picking a target
        self.selected = 0
        self.animations = []
        self.deferred = []         # [seconds_left, callback]
        self.flying = []           # cards hidden while they are animated
        self.spy_reveal = []
        self.spy_timer = 0.0
        self.grave_view = None     # 'user' | 'ai' | None
        self.user_faction = 'north'
        self.intro = None

        self.new_game('north', intro=intro)
        if fullscreen:
            self.toggle_fullscreen()

    # --- setup -------------------------------------------------------------
    def set_window_icon(self):
        """Use the game icon, falling back to the card back from the assets."""
        for candidate in (os.path.join('cards', 'tiles', 'icon.png'),
                          os.path.join('cards', 'de', 'small', 'back.png'),
                          os.path.join('cards', 'en', 'small', 'back.png')):
            if os.path.exists(candidate):
                try:
                    icon = pygame.image.load(candidate)
                except pygame.error:
                    continue
                pygame.display.set_icon(icon)
                return
    def _load_sounds(self):
        sounds = {}
        for key, path in (('play', 'sounds/play_card.ogg'),
                          ('round', 'sounds/round_ended.ogg')):
            try:
                sound = pygame.mixer.Sound(path)
                sound.set_volume(0.25)
                sounds[key] = sound
            except pygame.error:
                sounds[key] = None
        return sounds

    def _load_music(self):
        try:
            pygame.mixer.music.load('music/soundtrack_gwint.mp3')
            pygame.mixer.music.set_volume(0.12)
            pygame.mixer.music.play(-1)
        except pygame.error:
            pass

    def play_sound(self, key):
        sound = self.sounds.get(key)
        if sound:
            sound.play()

    def new_game(self, user_faction=None, intro=False):
        self.user_faction = user_faction or self.user_faction
        ai_faction = random.choice(self.factions)

        self.user = Player(self.player_name, build_deck(self.user_faction, self.pool))
        self.ai = Player(self.tr('computer'), build_deck(ai_faction, self.pool))
        self.user.faction = self.user_faction
        self.ai.faction = ai_faction

        self.game = Game(self.user, self.ai)
        self.user.draw(10)
        self.ai.draw(10)

        self.user_turn = random.choice([True, False])
        self.selected = 0
        self.pending = None
        self.grave_view = None
        self.animations = []
        self.deferred = []
        self.flying = []
        self.spy_reveal = []
        self.ai_timer = 0.0
        self.target_index = 0
        self.set_message(self.tr('new_game_you' if self.user_turn else 'new_game_ai'))

        if intro:
            ids = [c.id for c in self.user.hand[:5]]
            self.intro = Intro(ids)

    def set_message(self, value, seconds=3.0):
        self.message = value
        self.message_timer = seconds

    @property
    def busy(self):
        """True while a card is flying or a rules call is still pending.

        No new move is accepted until this clears, so an animation can never
        be overtaken by the next card.
        """
        return bool(self.animations or self.deferred or self.flying)

    @property
    def intro_running(self):
        return self.intro is not None and not self.intro.done

    @property
    def game_over(self):
        """True as soon as one side has lost both lives.

        The rules own this fact, so it is read from the game instead of being
        mirrored in a flag here - a copy would have to be updated after every
        round and silently rot if that was ever forgotten.
        """
        return self.game.game_over

    def toggle_language(self):
        self.tr.toggle()
        set_language(self.tr.language)
        pygame.display.set_caption(self.tr('game_title'))
        self.ai.name = self.tr('computer')
        self.set_message(self.tr('game_title') + ' – ' + self.tr.language.upper())


    def commit(self, callback, delay):
        """Run callback after delay seconds - used to apply a move on landing."""
        self.deferred.append([delay, callback])

    def visible_hand(self):
        """Hand cards minus the ones currently in flight."""
        return [c for c in self.user.hand if c not in self.flying]

    def clamp_selection(self):
        hand = self.visible_hand()
        if not hand:
            self.selected = 0
        else:
            self.selected = max(0, min(self.selected, len(hand) - 1))

    def selected_card(self):
        hand = self.visible_hand()
        if not hand:
            return None
        self.clamp_selection()
        return hand[self.selected]

    def hand_rects(self):
        lay = self.layout
        hand = self.visible_hand()
        cw, ch = lay.hand_card_size()
        xs = spread_positions(len(hand), lay.hand.centerx, lay.hand.w - 20, cw)
        y = lay.hand.centery - ch // 2
        return [pygame.Rect(x, y, cw, ch) for x in xs]

    def board_card_rects(self, owner, row_index):
        lay = self.layout
        player = self.user if owner == 'user' else self.ai
        rect = lay.row_rect(ROW_LAYOUT.index((owner, row_index)))
        cards = [c for c in player.rows[row_index] if c not in self.flying]
        xs = spread_positions(len(cards), lay.cards_x + lay.cards_w // 2,
                              lay.cards_w, lay.card_w)
        y = rect.centery - lay.card_h // 2
        return [(cards[i], pygame.Rect(x, y, lay.card_w, lay.card_h))
                for i, x in enumerate(xs)]

    def row_center(self, owner, row_index):
        lay = self.layout
        rect = lay.row_rect(ROW_LAYOUT.index((owner, row_index)))
        return (lay.cards_x + lay.cards_w // 2, rect.centery)

    def grave_rects(self):
        """Cards inside the open graveyard overlay."""
        if not self.grave_view:
            return []
        player = self.user if self.grave_view == 'user' else self.ai
        cards = player.discard
        if not cards:
            return []

        lay = self.layout
        cw, ch = 74, 112
        per_row = max(1, (lay.width - 260) // (cw + 8))
        start_x = lay.width // 2 - min(len(cards), per_row) * (cw + 8) // 2
        start_y = 150

        rects = []
        for i, card in enumerate(cards):
            col, row = i % per_row, i // per_row
            rects.append((card, pygame.Rect(start_x + col * (cw + 8),
                                            start_y + row * (ch + 10), cw, ch)))
        return rects

    # --- playing a card ----------------------------------------------------
    def target_position(self, card, owner, target_row):
        """Where a card should land, depending on its type."""
        lay = self.layout
        if card.is_weather:
            if card.ability == 'clear':
                return (lay.width // 2, lay.height // 2)
            index = ROW_LAYOUT.index(('user', WEATHER_ROW[card.ability]))
            return lay.weather_slot(index).center
        if card.ability == 'horn' and card.is_special:
            row = target_row if target_row is not None else MELEE
            return lay.horn_slot(ROW_LAYOUT.index((owner, row))).center
        if card.ability == 'scorch':
            return (lay.width // 2, lay.height // 2)
        row = target_row if target_row is not None else card.row_index
        if row is None:
            return (lay.width // 2, lay.height // 2)
        return self.row_center(owner, row)

    def play_selected(self, target_row=None, decoy_target=None, medic_target=None):
        card = self.selected_card()
        if card is None or not self.user_turn or self.user.passed or self.game_over:
            return
        if self.busy or self.intro_running:
            return

        # Cards that need a target first
        if card.ability == 'horn' and card.is_special and target_row is None:
            self.pending = ('horn', card)
            self.set_message(self.tr('pick_horn_row'))
            return
        if card.is_agile and target_row is None and card.ability != 'spy':
            self.pending = ('agile', card)
            self.set_message(self.tr('pick_agile_row'))
            return
        if card.ability == 'decoy' and decoy_target is None:
            if not any(self.user.rows):
                self.set_message(self.tr('no_decoy_target'))
                return
            self.pending = ('decoy', card)
            self.set_message(self.tr('pick_decoy'))
            return
        if card.ability == 'medic' and medic_target is None:
            if self.game.revivable(self.user):
                self.pending = ('medic', card)
                self.grave_view = 'user'
                self.set_message(self.tr('pick_medic'), 8)
                return
            # Empty graveyard: play it as a plain unit and say why
            self.set_message(self.tr('empty_graveyard'))

        rects = self.hand_rects()
        hand = self.visible_hand()
        index = hand.index(card)
        from_rect = rects[index] if index < len(rects) else self.layout.hand

        self.pending = None
        self.grave_view = None

        owner = 'ai' if card.ability == 'spy' else 'user'
        self.start_move(self.user, card, owner, from_rect.center, target_row,
                        decoy_target, medic_target)

    def start_move(self, player, card, owner, start_pos, target_row=None,
                   decoy_target=None, medic_target=None):
        """Fly the card first, apply the rules when it lands."""
        lay = self.layout
        self.flying.append(card)
        self.play_sound('play')

        end = self.target_position(card, owner, target_row)
        start_size = lay.hand_card_size() if player is self.user else (lay.card_w, lay.card_h)
        self.animations.append(CardFlight(card.id, start_pos, end,
                                          start_size=start_size,
                                          end_size=(lay.card_w, lay.card_h)))

        def land():
            if card in self.flying:
                self.flying.remove(card)
            self.game.play(player, card, target_row, decoy_target, medic_target)
            self.show_effects(player)
            self.clamp_selection()
            self.after_move(player)

        self.commit(land, FLIGHT_TIME)

    def show_effects(self, player):
        """Turn game.last_effect into animations and messages."""
        effect = self.game.last_effect
        lay = self.layout
        tr = self.tr

        drawn = effect.get('drawn')
        if drawn and player is self.user:
            self.spy_reveal = list(drawn)
            self.spy_timer = 3.2

        revived = effect.get('revived')
        if revived:
            grave = lay.user_grave if player is self.user else lay.ai_grave
            owner = 'user' if player is self.user else 'ai'
            self.flying.append(revived)
            self.animations.append(CardFlight(
                revived.id, grave.center, self.row_center(owner, revived.row_index),
                duration=0.45, start_size=(40, 60),
                end_size=(lay.card_w, lay.card_h)))
            self.commit(lambda: self.flying.remove(revived)
                        if revived in self.flying else None, 0.45)
            self.set_message(f"{tr('medic_revived')}: {tr.card_name(revived)}")

        scorched = effect.get('scorched')
        if scorched:
            names = ', '.join(tr.card_name(c) for c in scorched)
            self.set_message(f"{tr('scorched')}: {names}")

        mustered = effect.get('mustered')
        if mustered:
            self.set_message(f"{tr('muster')}: {len(mustered) + 1}x")

    def after_move(self, mover):
        """Called once a move has fully landed.

        `mover` decides who goes next: after your move it is the opponent's
        turn unless they have already passed, and the other way round.
        """
        if not self.user.hand and not self.user.passed:
            self.user.passed = True
            self.set_message(self.tr('no_cards_left'))
        if not self.ai.hand and not self.ai.passed:
            self.ai.passed = True

        if self.game.round_over():
            self.finish_round()
            return

        if mover is self.user:
            self.user_turn = self.ai.passed
        else:
            self.user_turn = not self.user.passed
        self.ai_timer = 0.0

    def pass_round(self):
        if self.user.passed or self.game_over or self.busy or self.intro_running:
            return
        self.user.passed = True
        self.pending = None
        self.grave_view = None
        self.set_message(self.tr('you_passed'))
        if self.game.round_over():
            self.finish_round()
        else:
            self.user_turn = False
            self.ai_timer = 0.0

    def finish_round(self):
        user_score = self.user.total_points(self.game.weather)
        ai_score = self.ai.total_points(self.game.weather)
        winner = self.game.resolve_round()

        self.play_sound('round')
        if winner is self.user:
            key, self.user_turn = 'round_won', True
        elif winner is self.ai:
            key, self.user_turn = 'round_lost', False
        else:
            key, self.user_turn = 'round_draw', random.choice([True, False])
        self.set_message(f'{self.tr(key)}   {user_score} : {ai_score}', 4)

        self.animations = []
        self.deferred = []
        self.flying = []
        self.render()
        pygame.display.flip()
        pygame.time.delay(1500)

        # No cards are drawn between rounds - you keep the ten you started
        # with. Only the Northern Realms bonus grants one extra card for
        # winning a round.
        if not self.game_over and winner is not None:
            if winner.faction == 'north':
                drawn = winner.draw(1)
                if drawn and winner is self.user:
                    self.set_message(self.tr('north_bonus'), 3)
        self.clamp_selection()
        self.ai_timer = 0.0

    # --- AI ----------------------------------------------------------------
    def ai_move(self):
        ai, user = self.ai, self.user
        weather = self.game.weather

        if not ai.hand:
            ai.passed = True
            self.after_move(ai)
            return

        ai_score = ai.total_points(weather)
        user_score = user.total_points(weather)

        if user.passed and ai_score > user_score:
            spies = [c for c in ai.hand if c.ability == 'spy'
                     and ai_score - user_score > c.strength]
            if spies:
                self.ai_execute(spies[0])
                return
            ai.passed = True
            self.after_move(ai)
            return

        if user.passed and ai_score + sum(c.strength for c in ai.hand) < user_score:
            ai.passed = True
            self.after_move(ai)
            return

        self.ai_execute(self.ai_choose_card())

    def ai_execute(self, card):
        ai = self.ai
        weather = self.game.weather
        target_row = None
        decoy_target = None
        medic_target = None

        if card.ability == 'horn' and card.is_special:
            target_row = max(range(3), key=lambda r: ai.row_points(r, weather))
        elif card.is_agile:
            # Pick the allowed row that is not under weather and has fewer cards
            options = [r for r in card.allowed_rows if r not in weather]
            if not options:
                options = list(card.allowed_rows)
            target_row = min(options, key=lambda r: len(ai.rows[r]))
        elif card.ability == 'decoy':
            own = [c for row in ai.rows for c in row if not c.hero]
            if own:
                decoy_target = max(own, key=lambda c: c.strength)
            else:
                card = max(ai.hand, key=lambda c: c.strength)
        elif card.ability == 'medic':
            options = self.game.revivable(ai)
            if options:
                medic_target = max(options, key=lambda c: c.strength)

        owner = 'user' if card.ability == 'spy' else 'ai'
        start = self.layout.ai_panel.center
        self.start_move(ai, card, owner, start, target_row, decoy_target,
                        medic_target)

    def ai_choose_card(self):
        ai, user = self.ai, self.user
        weather = self.game.weather

        spies = [c for c in ai.hand if c.ability == 'spy']
        if spies and ai.deck:
            return min(spies, key=lambda c: c.strength)

        scorches = [c for c in ai.hand if c.ability == 'scorch']
        if scorches:
            top_enemy = max((v for c, v, _ in user.units(weather) if not c.hero),
                            default=0)
            top_own = max((v for c, v, _ in ai.units(weather) if not c.hero),
                          default=0)
            if top_enemy >= 10 and top_enemy > top_own:
                return scorches[0]

        for card in ai.hand:
            if card.is_weather and card.ability != 'clear':
                row = WEATHER_ROW[card.ability]
                if row in weather:
                    continue
                if user.row_points(row, weather) - ai.row_points(row, weather) >= 8:
                    return card

        if weather:
            clears = [c for c in ai.hand if c.ability == 'clear']
            if clears:
                hurt_ai = sum(1 for r in weather if ai.rows[r])
                hurt_user = sum(1 for r in weather if user.rows[r])
                if hurt_ai > hurt_user:
                    return clears[0]

        units = [c for c in ai.hand if c.is_unit]
        return max(units, key=lambda c: c.strength) if units else ai.hand[0]

    # --- keyboard target selection -----------------------------------------
    def target_options(self):
        """Everything the arrow keys can step through while picking a target.

        Returns a list of (label, value); the meaning of value depends on the
        kind of pending action.
        """
        if not self.pending:
            return []
        kind, card = self.pending

        if kind == 'horn':
            return [(self.tr.row(r), r) for r in range(3)]
        if kind == 'agile':
            return [(self.tr.row(r), r) for r in card.allowed_rows]
        if kind == 'medic':
            return [(self.tr.card_name(c), c) for c in self.game.revivable(self.user)]
        if kind == 'decoy':
            units = [c for row in self.user.rows for c in row if not c.hero]
            return [(self.tr.card_name(c), c) for c in units]
        return []

    def move_target_cursor(self, step):
        options = self.target_options()
        if not options:
            return
        self.target_index = (self.target_index + step) % len(options)
        label = options[self.target_index][0]
        self.set_message(f'{label}   [{self.target_index + 1}/{len(options)}]', 6)

    def confirm_target(self):
        """Play the pending card with whatever the cursor currently points at."""
        options = self.target_options()
        if not self.pending or not options:
            return
        kind, card = self.pending
        value = options[self.target_index % len(options)][1]

        hand = self.visible_hand()
        if card not in hand:
            self.pending = None
            self.grave_view = None
            return
        self.selected = hand.index(card)

        if kind in ('horn', 'agile'):
            self.play_selected(target_row=value)
        elif kind == 'medic':
            self.play_selected(medic_target=value)
        elif kind == 'decoy':
            self.play_selected(decoy_target=value)

    def current_target(self):
        """The value the cursor points at, for highlighting while drawing."""
        options = self.target_options()
        if not options:
            return None
        return options[self.target_index % len(options)][1]

    # --- input -------------------------------------------------------------
    def handle_click(self, pos):
        if self.intro_running:
            self.intro.skip()
            return
        if self.game_over or self.busy:
            return

        # Graveyard overlay open?
        if self.grave_view:
            for card, rect in self.grave_rects():
                if rect.collidepoint(pos):
                    if self.pending and self.pending[0] == 'medic':
                        if card in self.game.revivable(self.user):
                            medic = self.pending[1]
                            hand = self.visible_hand()
                            if medic in hand:
                                self.selected = hand.index(medic)
                                self.play_selected(medic_target=card)
                    return
            # A click next to the cards closes the view unless a pick is required
            if not self.pending:
                self.grave_view = None
            return

        # Open a graveyard
        if self.layout.user_grave.collidepoint(pos) and self.user.discard:
            self.grave_view = 'user'
            return
        if self.layout.ai_grave.collidepoint(pos) and self.ai.discard:
            self.grave_view = 'ai'
            return

        # A target is being picked
        if self.pending:
            kind, card = self.pending
            hand = self.visible_hand()
            if kind == 'horn':
                for index, (owner, row_index) in enumerate(ROW_LAYOUT):
                    hit = (self.layout.row_rect(index).collidepoint(pos)
                           or self.layout.horn_slot(index).collidepoint(pos))
                    if owner == 'user' and hit:
                        self.selected = hand.index(card)
                        self.play_selected(target_row=row_index)
                        return
            elif kind == 'agile':
                for index, (owner, row_index) in enumerate(ROW_LAYOUT):
                    if (owner == 'user' and row_index in card.allowed_rows
                            and self.layout.row_rect(index).collidepoint(pos)):
                        self.selected = hand.index(card)
                        self.play_selected(target_row=row_index)
                        return
            elif kind == 'decoy':
                for owner, row_index in ROW_LAYOUT:
                    if owner != 'user':
                        continue
                    for unit, rect in self.board_card_rects('user', row_index):
                        if rect.collidepoint(pos) and not unit.hero:
                            self.selected = hand.index(card)
                            self.play_selected(decoy_target=unit)
                            return
            return

        # Hand card: first click selects, second plays
        for index, rect in enumerate(self.hand_rects()):
            if rect.collidepoint(pos):
                if self.selected == index:
                    self.play_selected()
                else:
                    self.selected = index
                return

    def handle_key(self, key):
        if self.intro_running and key not in (pygame.K_ESCAPE,):
            self.intro.skip()
            return True

        if key == pygame.K_ESCAPE:
            if self.intro_running:
                self.intro.skip()
                return True
            if self.grave_view or self.pending:
                self.pending = None
                self.grave_view = None
                self.set_message(self.tr('cancelled'))
                return True
            return False

        if key == pygame.K_F11:
            self.toggle_fullscreen()
        elif key == pygame.K_F3:
            self.toggle_language()
        elif key == pygame.K_g:
            if self.pending and self.pending[0] == 'medic':
                return True
            self.grave_view = None if self.grave_view else 'user'
        elif self.game_over and key == pygame.K_n:
            self.new_game()

        # While a target is pending the arrow keys walk the options
        elif self.pending and key in (pygame.K_RIGHT, pygame.K_DOWN):
            self.move_target_cursor(1)
        elif self.pending and key in (pygame.K_LEFT, pygame.K_UP):
            self.move_target_cursor(-1)
        elif self.pending and key == pygame.K_RETURN:
            self.confirm_target()

        elif key == pygame.K_RIGHT:
            self.selected += 1
            self.clamp_selection()
        elif key == pygame.K_LEFT:
            self.selected -= 1
            self.clamp_selection()
        elif key == pygame.K_RETURN:
            self.play_selected()
        elif key == pygame.K_SPACE:
            self.pass_round()
        return True

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        self.layout.update(*self.screen.get_size())

    def handle_resize(self, size):
        width = max(MIN_SIZE[0], size[0])
        height = max(MIN_SIZE[1], size[1])
        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        self.layout.update(width, height)

    # --- drawing -----------------------------------------------------------
    def render(self):
        screen = self.screen
        lay = self.layout
        screen.fill(BG_DARK)
        vgradient(screen, (0, 0, lay.width, lay.height), (26, 23, 20), (12, 11, 10))

        self.draw_rows()
        self.draw_panels()
        self.draw_hand()
        self.draw_sidebar()
        self.draw_message()
        self.draw_spy_reveal()

        for flight in self.animations:
            flight.draw(screen, (lay.card_w, lay.card_h))

        if self.grave_view:
            self.draw_graveyard()
        if self.game_over:
            self.draw_game_over()
        if self.intro is not None and not self.intro.done:
            self.intro.draw(screen, lay, self.tr('game_title'),
                            self.tr.faction(self.user_faction))

    def draw_rows(self):
        screen, lay, tr = self.screen, self.layout, self.tr
        weather = self.game.weather

        for index, (owner, row_index) in enumerate(ROW_LAYOUT):
            player = self.user if owner == 'user' else self.ai
            rect = lay.row_rect(index)
            bad = row_index in weather

            color = ROW_WEATHER if bad else ROW_COLORS[row_index]
            panel(screen, rect, color=color, border=GOLD_DIM, width=1, radius=4)

            if self.pending and self.pending[0] == 'horn' and owner == 'user':
                cursor = self.current_target()
                width = 4 if cursor == row_index else 2
                pygame.draw.rect(screen, GOLD, rect, width, border_radius=4)
            if (self.pending and self.pending[0] == 'agile' and owner == 'user'
                    and row_index in self.pending[1].allowed_rows):
                cursor = self.current_target()
                chosen = cursor == row_index
                glow_rect(screen, rect, GOLD if chosen else GREEN,
                          alpha=90 if chosen else 60, spread=4, radius=4)
                pygame.draw.rect(screen, GOLD if chosen else GREEN, rect,
                                 4 if chosen else 3, border_radius=4)

            score = player.row_points(row_index, weather)
            badge(screen, (lay.score_x, rect.centery), score, radius=lay.badge_r,
                  fill=PARCHMENT if score else PANEL_LIGHT,
                  fg=INK if score else GOLD_DIM, size=max(14, lay.badge_r))

            self.draw_weather_slot(index, row_index)
            self.draw_horn_slot(index, owner, row_index, player)

            for card, card_rect in self.board_card_rects(owner, row_index):
                screen.blit(scaled_card(card.id, (card_rect.w, card_rect.h)), card_rect)
                if card.hero:
                    pygame.draw.rect(screen, GOLD, card_rect, 2, border_radius=3)
                if (self.pending and self.pending[0] == 'decoy'
                        and owner == 'user' and not card.hero):
                    chosen = self.current_target() is card
                    pygame.draw.rect(screen, GOLD if chosen else GREEN,
                                     card_rect, 4 if chosen else 3,
                                     border_radius=3)

    def draw_weather_slot(self, index, row_index):
        """Shows the actual weather card lying next to the affected row."""
        screen, lay, tr = self.screen, self.layout, self.tr
        slot = lay.weather_slot(index)
        card = self.game.weather_cards.get(row_index)

        if card is not None and card not in self.flying:
            screen.blit(scaled_card(card.id, (slot.w, slot.h)), slot)
            pygame.draw.rect(screen, BLUE_FROST, slot, 2, border_radius=3)
        else:
            panel(screen, slot, color=(30, 34, 42), border=(60, 66, 76),
                  width=1, radius=3)
            names = {MELEE: tr('frost'), RANGED: tr('fog'), SIEGE: tr('rain')}
            text(screen, names[row_index][:1], slot.center, size=14,
                 color=(78, 88, 100), center=True)

    def draw_horn_slot(self, index, owner, row_index, player):
        """Shows the Commander's Horn card in the row it boosts."""
        screen, lay, tr = self.screen, self.layout, self.tr
        slot = lay.horn_slot(index)
        card = player.horns[row_index]

        highlight = (self.pending and self.pending[0] == 'horn' and owner == 'user')

        if card is not None and card not in self.flying:
            screen.blit(scaled_card(card.id, (slot.w, slot.h)), slot)
            pygame.draw.rect(screen, GOLD, slot, 2, border_radius=3)
        else:
            panel(screen, slot, color=(44, 38, 30) if not highlight else (72, 60, 38),
                  border=GOLD if highlight else (70, 62, 52), width=1, radius=3)
            text(screen, tr('horn_slot')[:1], slot.center, size=14,
                 color=GOLD if highlight else (100, 90, 76), center=True)

    def draw_panels(self):
        screen, lay, tr = self.screen, self.layout, self.tr
        weather = self.game.weather
        mouse = pygame.mouse.get_pos()

        for owner in ('ai', 'user'):
            player = self.ai if owner == 'ai' else self.user
            rect = lay.ai_panel if owner == 'ai' else lay.user_panel
            grave = lay.ai_grave if owner == 'ai' else lay.user_grave

            active = (owner == 'user') == self.user_turn and not self.game_over
            panel(screen, rect, border=GOLD if active else GOLD_DIM,
                  width=3 if active else 2)

            inner = rect.w - 24
            text(screen, fit_text(player.name, 19, inner - 60, True),
                 (rect.x + 12, rect.y + 8), size=19, color=GOLD, bold=True)
            text(screen, fit_text(tr.faction(player.faction), 13, inner),
                 (rect.x + 12, rect.y + 32), size=13, color=(150, 138, 120))
            text(screen, f"{tr('cards')}: {len(player.hand)}",
                 (rect.x + 12, rect.y + 52), size=15)
            text(screen, f"{tr('deck')}: {len(player.deck)}",
                 (rect.x + 12, rect.y + 72), size=14, color=(150, 138, 120))

            for i in range(2):
                center = (rect.right - 22 - i * 24, rect.y + 20)
                pygame.draw.circle(screen, RED if i < player.lives else (70, 62, 54),
                                   center, 8)
                pygame.draw.circle(screen, GOLD_DIM, center, 8, 2)

            total = player.total_points(weather)
            badge(screen, (rect.right - 34, rect.bottom - 30), total, radius=24,
                  fill=GOLD if total else PANEL_LIGHT,
                  fg=INK if total else GOLD_DIM, size=24)

            if player.passed:
                text(screen, tr('passed'), (rect.x + 12, rect.bottom - 24),
                     size=14, color=RED, bold=True)

            # Graveyard button
            hot = grave.collidepoint(mouse) and player.discard
            wanted = (self.pending and self.pending[0] == 'medic' and owner == 'user')
            panel(screen, grave, color=PANEL_LIGHT if hot else PANEL,
                  border=GREEN if wanted else (GOLD if hot else GOLD_DIM))
            text(screen, f"{tr('graveyard')}: {len(player.discard)}",
                 grave.center, size=14,
                 color=PARCHMENT if player.discard else (110, 98, 84), center=True)

    def draw_hand(self):
        screen = self.screen
        hand = self.visible_hand()
        self.clamp_selection()

        for index, rect in enumerate(self.hand_rects()):
            card = hand[index]
            screen.blit(scaled_card(card.id, (rect.w, rect.h)), rect)
            if card.hero:
                pygame.draw.rect(screen, GOLD, rect, 2, border_radius=3)
            if index == self.selected and not self.game_over:
                pygame.draw.rect(screen, GOLD, rect.inflate(8, 8), 3, border_radius=5)

    def draw_sidebar(self):
        screen, lay, tr = self.screen, self.layout, self.tr
        bar = lay.sidebar
        card = self.hover_card or self.selected_card()

        y = bar.y
        preview_h = min(390, int(bar.h * 0.46))
        preview = pygame.Rect(bar.x, y, bar.w, preview_h)
        panel(screen, preview)
        if card:
            img_h = preview_h - 84
            img_w = int(img_h * 2 / 3)
            screen.blit(scaled_card(card.id, (img_w, img_h), large=True),
                        (preview.centerx - img_w // 2, preview.y + 10))

            text(screen, fit_text(tr.card_name(card), 16, bar.w - 20, True),
                 (preview.centerx, preview.bottom - 62), size=16, color=GOLD,
                 bold=True, center=True)
            for i, line in enumerate(self.card_description(card)):
                text(screen, fit_text(line, 13, bar.w - 20),
                     (preview.centerx, preview.bottom - 40 + i * 18), size=13,
                     center=True)

        y = preview.bottom + 8
        wx = pygame.Rect(bar.x, y, bar.w, 64)
        panel(screen, wx)
        text(screen, tr('weather'), (wx.x + 10, wx.y + 6), size=14, color=GOLD,
             bold=True)
        if self.game.weather:
            names = {MELEE: tr('frost'), RANGED: tr('fog'), SIEGE: tr('rain')}
            active = ', '.join(names[r] for r in sorted(self.game.weather))
            text(screen, fit_text(active, 16, bar.w - 20), (wx.x + 10, wx.y + 28),
                 size=16, color=BLUE_FROST, bold=True)
        else:
            text(screen, tr('clear_sky'), (wx.x + 10, wx.y + 28), size=16,
                 color=(120, 130, 120))

        y = wx.bottom + 8
        score = pygame.Rect(bar.x, y, bar.w, 74)
        panel(screen, score)
        text(screen, f"{tr('rounds')}  ({tr('round_label')} {self.game.round})",
             (score.centerx, score.y + 8), size=13, color=GOLD, bold=True,
             center=True)
        text(screen, f'{self.user.rounds_won} : {self.ai.rounds_won}',
             (score.centerx, score.y + 44), size=30, bold=True, center=True)

        y = score.bottom + 8
        help_h = 106
        log = pygame.Rect(bar.x, y, bar.w, max(60, bar.bottom - y - help_h - 8))
        panel(screen, log)
        text(screen, tr('history'), (log.x + 10, log.y + 6), size=14, color=GOLD,
             bold=True)
        visible = max(1, (log.h - 28) // 18)
        for i, entry in enumerate(self.game.log[-visible:]):
            text(screen, fit_text(entry, 12, bar.w - 20),
                 (log.x + 10, log.y + 26 + i * 18), size=12, color=(170, 158, 140))

        helper = pygame.Rect(bar.x, bar.bottom - help_h, bar.w, help_h)
        panel(screen, helper)
        text(screen, tr('controls'), (helper.x + 10, helper.y + 6), size=13,
             color=GOLD, bold=True)
        for i, key in enumerate(('ctrl_play', 'ctrl_select', 'ctrl_pass', 'ctrl_misc')):
            text(screen, fit_text(tr(key), 12, bar.w - 20),
                 (helper.x + 10, helper.y + 26 + i * 19), size=12,
                 color=(160, 150, 134))

    def card_description(self, card):
        tr = self.tr
        lines = []
        if card.is_unit:
            kind = tr('hero') if card.hero else tr('unit')
            where = tr('agile_rows') if card.is_agile else tr.row(card.row_index)
            lines.append(f'{kind} – {where} – {card.strength}')
        else:
            lines.append(tr('special_card'))
        if card.is_agile:
            lines.append(tr('agile'))
        if card.ability:
            lines.append(tr.ability(card.ability))
        return lines

    def draw_message(self):
        if not self.message or self.message_timer <= 0:
            return
        rect = self.layout.message
        panel(self.screen, rect, color=(48, 40, 30), border=GOLD)
        text(self.screen, fit_text(self.message, 17, rect.w - 20, True),
             rect.center, size=17, color=GOLD, bold=True, center=True)

    def draw_spy_reveal(self):
        """Shows the cards a spy just drew, large and centred."""
        if not self.spy_reveal or self.spy_timer <= 0:
            return

        lay = self.layout
        cw, ch = 96, 145
        total = len(self.spy_reveal) * (cw + 12) - 12
        box = pygame.Rect(0, 0, total + 32, ch + 56)
        box.center = (lay.width // 2, lay.height // 2 - 40)

        fade = min(1.0, self.spy_timer)
        overlay = pygame.Surface(box.size, pygame.SRCALPHA)
        overlay.fill((24, 20, 16, int(235 * fade)))
        self.screen.blit(overlay, box)
        pygame.draw.rect(self.screen, GOLD, box, 2, border_radius=6)

        text(self.screen, self.tr('spy_drew'), (box.centerx, box.y + 16), size=16,
             color=GOLD, bold=True, center=True)
        for i, card in enumerate(self.spy_reveal):
            x = box.x + 16 + i * (cw + 12)
            self.screen.blit(scaled_card(card.id, (cw, ch)), (x, box.y + 36))

    def draw_graveyard(self):
        screen, lay, tr = self.screen, self.layout, self.tr
        player = self.user if self.grave_view == 'user' else self.ai

        overlay = pygame.Surface((lay.width, lay.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 205))
        screen.blit(overlay, (0, 0))

        text(screen, f"{tr('graveyard')} – {player.name}", (lay.width // 2, 60),
             size=32, color=GOLD, bold=True, center=True)

        picking = self.pending and self.pending[0] == 'medic'
        if picking:
            text(screen, tr('pick_medic'), (lay.width // 2, 100), size=18,
                 color=GREEN, bold=True, center=True)
            text(screen, tr('arrow_hint'), (lay.width // 2, 126), size=14,
                 color=(150, 140, 124), center=True)
        else:
            text(screen, '[Esc] / [G]', (lay.width // 2, 104), size=16,
                 color=(150, 140, 124), center=True)

        revivable = self.game.revivable(player) if self.grave_view == 'user' else []
        mouse = pygame.mouse.get_pos()
        cursor = self.current_target() if picking else None

        for card, rect in self.grave_rects():
            selectable = picking and card in revivable
            focused = selectable and (rect.collidepoint(mouse) or card is cursor)
            if focused:
                glow_rect(screen, rect, GOLD, alpha=150)
            screen.blit(scaled_card(card.id, (rect.w, rect.h)), rect)
            if selectable:
                pygame.draw.rect(screen, GOLD if focused else GREEN, rect,
                                 4 if focused else 3, border_radius=4)
            elif card.hero:
                # Heroes cannot be revived - mark them so it is obvious why
                pygame.draw.rect(screen, GOLD_DIM, rect, 2, border_radius=4)
                if picking:
                    shade = pygame.Surface(rect.size, pygame.SRCALPHA)
                    shade.fill((0, 0, 0, 150))
                    screen.blit(shade, rect)
                    text(screen, tr('hero'), rect.center, size=12,
                         color=GOLD_DIM, center=True)
            elif picking:
                shade = pygame.Surface(rect.size, pygame.SRCALPHA)
                shade.fill((0, 0, 0, 150))
                screen.blit(shade, rect)

        if picking and not revivable:
            text(screen, tr('no_revive_target'), (lay.width // 2, lay.height - 70),
                 size=17, color=RED, bold=True, center=True)

        if not player.discard:
            text(screen, '–', (lay.width // 2, lay.height // 2), size=40,
                 color=(120, 110, 96), center=True)

    def draw_game_over(self):
        lay = self.layout
        overlay = pygame.Surface((lay.width, lay.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        winner = self.game.winner()
        if winner is self.user:
            title, color = self.tr('you_win'), GREEN
        elif winner is self.ai:
            title, color = self.tr('you_lose'), RED
        else:
            title, color = self.tr('draw'), PARCHMENT

        text(self.screen, title, (lay.width // 2, lay.height // 2 - 40), size=68,
             color=color, bold=True, center=True)
        text(self.screen, self.tr('restart_hint'),
             (lay.width // 2, lay.height // 2 + 40), size=22, center=True)

    # --- main loop ---------------------------------------------------------
    def update_hover(self, pos):
        self.hover_card = None
        if self.grave_view:
            for card, rect in self.grave_rects():
                if rect.collidepoint(pos):
                    self.hover_card = card
                    return
            return

        hand = self.visible_hand()
        for index, rect in enumerate(self.hand_rects()):
            if rect.collidepoint(pos):
                self.hover_card = hand[index]
                return

        for index, (owner, row_index) in enumerate(ROW_LAYOUT):
            weather_card = self.game.weather_cards.get(row_index)
            if weather_card and self.layout.weather_slot(index).collidepoint(pos):
                self.hover_card = weather_card
                return
            player = self.user if owner == 'user' else self.ai
            horn = player.horns[row_index]
            if horn and self.layout.horn_slot(index).collidepoint(pos):
                self.hover_card = horn
                return
            for card, rect in self.board_card_rects(owner, row_index):
                if rect.collidepoint(pos):
                    self.hover_card = card
                    return

    def tick_timers(self, dt):
        self.message_timer = max(0.0, self.message_timer - dt)
        self.spy_timer = max(0.0, self.spy_timer - dt)
        if self.spy_timer <= 0:
            self.spy_reveal = []

        if self.intro is not None:
            self.intro.update(dt)

        for flight in self.animations:
            flight.update(dt)
        self.animations = [f for f in self.animations if not f.done]

        # Deferred moves are applied once their animation has landed
        ready = []
        for entry in self.deferred:
            entry[0] -= dt
            if entry[0] <= 0:
                ready.append(entry)
        for entry in ready:
            if entry in self.deferred:
                self.deferred.remove(entry)
            entry[1]()

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            self.tick_timers(dt)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.handle_resize(event.size)
                elif event.type == pygame.KEYDOWN:
                    if not self.handle_key(event.key):
                        running = False
                elif event.type == pygame.MOUSEMOTION:
                    self.update_hover(event.pos)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_click(event.pos)

            if (not self.game_over and not self.user_turn and not self.busy
                    and not self.intro_running):
                if self.ai.passed:
                    self.user_turn = True
                else:
                    self.ai_timer += dt
                    if self.ai_timer >= AI_THINK_TIME:
                        self.ai_timer = 0.0
                        self.ai_move()

            self.render()
            pygame.display.flip()

        pygame.quit()


def main(argv=None):
    settings = from_command_line(argv)

    app = GwintApp(settings.name, settings.language, intro=False,
                   music=settings.music, fullscreen=settings.fullscreen)
    faction = (settings.faction if settings.faction in app.factions
               else app.factions[0])
    app.new_game(faction, intro=settings.intro)
    app.run()

    # Remember what the player last used
    settings.faction = app.user_faction
    settings.language = app.tr.language
    settings.save()


if __name__ == '__main__':
    main()

