"""Drawing layer for Gwent: layout, colours, images and widgets."""
import math
import os

import pygame

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- colour palette ---------------------------------------------------------
GOLD = (222, 178, 92)
GOLD_DIM = (150, 118, 62)
PARCHMENT = (226, 212, 180)
INK = (28, 24, 20)
BG_DARK = (18, 16, 14)
PANEL = (38, 33, 28)
PANEL_LIGHT = (52, 45, 38)
ROW_MELEE = (74, 46, 36)
ROW_RANGED = (52, 58, 42)
ROW_SIEGE = (42, 46, 62)
ROW_WEATHER = (46, 62, 82)
RED = (178, 58, 46)
GREEN = (96, 150, 88)
BLUE_FROST = (128, 176, 214)
WHITE = (240, 236, 228)

CARD_W, CARD_H = 86, 130

_font_cache = {}
_image_cache = {}
_language = 'de'


def set_language(code):
    """Switch the image language and drop the cache."""
    global _language
    if code != _language:
        _language = code
        _image_cache.clear()


def get_language():
    return _language


def font(size, bold=False):
    key = (size, bold)
    if key not in _font_cache:
        _font_cache[key] = pygame.font.SysFont(
            'Georgia,Palatino Linotype,serif', size, bold=bold)
    return _font_cache[key]


def card_image(card_id, large=False):
    """Load a card image in the active language (cached)."""
    key = (card_id, large, _language)
    if key in _image_cache:
        return _image_cache[key]

    folder = 'large' if large else 'small'
    path = os.path.join(BASE_DIR, 'cards', _language, folder, f'{card_id}.png')
    if not os.path.exists(path):
        # Fall back to German, then to a placeholder
        path = os.path.join(BASE_DIR, 'cards', 'de', folder, f'{card_id}.png')

    if os.path.exists(path):
        image = pygame.image.load(path).convert_alpha()
    else:
        size = (300, 450) if large else (CARD_W, CARD_H)
        image = pygame.Surface(size, pygame.SRCALPHA)
        image.fill(PANEL_LIGHT)
        pygame.draw.rect(image, GOLD_DIM, image.get_rect(), 2)

    _image_cache[key] = image
    return image


def scaled_card(card_id, size, large=False):
    """Card image at an arbitrary size, also cached."""
    size = (max(1, int(size[0])), max(1, int(size[1])))
    key = ('scaled', card_id, size, _language, large)
    if key not in _image_cache:
        _image_cache[key] = pygame.transform.smoothscale(
            card_image(card_id, large), size)
    return _image_cache[key]


def text(surface, value, pos, size=20, color=PARCHMENT, bold=False,
         center=False, right=False, shadow=True):
    rendered = font(size, bold).render(str(value), True, color)
    rect = rendered.get_rect()
    if center:
        rect.center = pos
    elif right:
        rect.midright = pos
    else:
        rect.topleft = pos

    if shadow:
        surface.blit(font(size, bold).render(str(value), True, (0, 0, 0)),
                     (rect.x + 1, rect.y + 1))
    surface.blit(rendered, rect)
    return rect


def fit_text(value, size, max_width, bold=False):
    """Shorten a string with an ellipsis until it fits."""
    value = str(value)
    rendered = font(size, bold)
    if rendered.size(value)[0] <= max_width:
        return value
    while value and rendered.size(value + '...')[0] > max_width:
        value = value[:-1]
    return value + '...'


def panel(surface, rect, color=PANEL, border=GOLD_DIM, width=2, radius=6):
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    if width:
        pygame.draw.rect(surface, border, rect, width, border_radius=radius)


def badge(surface, center, value, radius=20, fill=PARCHMENT, fg=INK, size=22):
    pygame.draw.circle(surface, (0, 0, 0), (center[0] + 2, center[1] + 2), radius)
    pygame.draw.circle(surface, fill, center, radius)
    pygame.draw.circle(surface, GOLD_DIM, center, radius, 2)
    text(surface, value, center, size=size, color=fg, bold=True, center=True,
         shadow=False)


def vgradient(surface, rect, top_color, bottom_color):
    x, y, w, h = rect
    for i in range(h):
        ratio = i / max(h - 1, 1)
        color = [round(top_color[c] + (bottom_color[c] - top_color[c]) * ratio)
                 for c in range(3)]
        pygame.draw.line(surface, color, (x, y + i), (x + w - 1, y + i))


def glow_rect(surface, rect, color, alpha=120, spread=8, radius=6):
    """Soft glow behind a rectangle, used for highlights."""
    glow = pygame.Surface((rect.w + spread * 2, rect.h + spread * 2), pygame.SRCALPHA)
    pygame.draw.rect(glow, (*color, alpha), glow.get_rect(), border_radius=radius)
    surface.blit(glow, (rect.x - spread, rect.y - spread))


def spread_positions(count, center_x, width, item_w, gap=4):
    """Spread items around a centre; they overlap when space runs out."""
    if count <= 0:
        return []

    step = item_w + gap
    if count * step - gap > width:
        step = max(16, (width - item_w) // max(count - 1, 1))

    total = step * (count - 1) + item_w
    start = center_x - total // 2
    return [start + i * step for i in range(count)]


# Kept for backwards compatibility with the tests
spread = spread_positions


def ease_out_cubic(t):
    return 1 - (1 - t) ** 3


def ease_in_out(t):
    return 0.5 - 0.5 * math.cos(math.pi * min(max(t, 0.0), 1.0))


class Layout(object):
    """Derives every rectangle from the window size - nothing is hardcoded."""

    def __init__(self, width, height):
        self.update(width, height)

    def update(self, width, height):
        self.width = width
        self.height = height
        margin = 12

        # Right hand sidebar
        self.sidebar_w = max(252, min(320, int(width * 0.21)))
        self.sidebar = pygame.Rect(width - self.sidebar_w - margin, margin,
                                   self.sidebar_w, height - 2 * margin)

        # Left hand info column
        self.info_w = max(186, min(240, int(width * 0.15)))
        self.info_x = margin

        # Board sits between the columns, leaving space for the score badges
        board_left = self.info_x + self.info_w + margin + 34
        board_right = self.sidebar.left - margin
        board_w = board_right - board_left

        # Heights: 6 rows + message strip + hand
        self.hand_h = 134
        self.message_h = 32
        available = height - 2 * margin - self.hand_h - self.message_h - 10
        self.row_gap = 4
        self.row_h = max(66, (available - 5 * self.row_gap) // 6)

        self.card_h = self.row_h - 8
        self.card_w = max(38, int(self.card_h * CARD_W / CARD_H))

        top = margin
        self.rows = [pygame.Rect(board_left, top + i * (self.row_h + self.row_gap),
                                 board_w, self.row_h) for i in range(6)]

        board_bottom = self.rows[-1].bottom
        self.message = pygame.Rect(board_left + 40, board_bottom + 6,
                                   board_w - 80, self.message_h)
        self.hand = pygame.Rect(board_left, self.message.bottom + 6,
                                board_w, self.hand_h)

        # Score badge left of every row, weather and horn slots inside
        self.badge_r = min(19, self.row_h // 3)
        self.score_x = board_left - self.badge_r - 8

        # Two small card slots at the left edge of each row
        self.slot_w = max(30, int((self.row_h - 14) * CARD_W / CARD_H))
        self.slot_h = self.row_h - 14
        self.weather_slot_x = board_left + 6
        self.horn_slot_x = self.weather_slot_x + self.slot_w + 4

        self.cards_x = self.horn_slot_x + self.slot_w + 10
        self.cards_w = board_right - self.cards_x - 10

        # Player panels top left / bottom left
        panel_h = 122
        self.ai_panel = pygame.Rect(self.info_x, margin, self.info_w, panel_h)
        self.user_panel = pygame.Rect(self.info_x, height - margin - panel_h,
                                      self.info_w, panel_h)
        self.ai_grave = pygame.Rect(self.info_x, self.ai_panel.bottom + 8,
                                    self.info_w, 32)
        self.user_grave = pygame.Rect(self.info_x, self.user_panel.top - 40,
                                      self.info_w, 32)

    def row_rect(self, index):
        return self.rows[index]

    def weather_slot(self, index):
        rect = self.rows[index]
        return pygame.Rect(self.weather_slot_x, rect.y + 7, self.slot_w, self.slot_h)

    def horn_slot(self, index):
        rect = self.rows[index]
        return pygame.Rect(self.horn_slot_x, rect.y + 7, self.slot_w, self.slot_h)

    def hand_card_size(self):
        h = min(CARD_H, self.hand_h - 8)
        return max(38, int(h * CARD_W / CARD_H)), h

