"""Generates the window icon and the launcher faction tiles.

tkinter can only scale images by whole-number factors, which makes the
leader cards look blocky. So the tiles are rendered here with pygame's
smooth scaler and written out at exactly the size the launcher needs.

Everything lands in cards/tiles/, next to the other generated images.

Run again after changing the assets:  python tools/make_icon.py
"""
import os

import pygame

# The script lives in tools/, everything it reads and writes sits one level up
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(BASE_DIR)

ICON_SIZE = 256
TILE_W, TILE_H = 150, 225

GOLD = (222, 178, 92)
GOLD_DIM = (150, 118, 62)
DARK = (18, 16, 14)

BACK_SOURCES = [
    os.path.join('cards', 'de', 'small', 'back.png'),
    os.path.join('cards', 'en', 'small', 'back.png'),
]

# Leader card per faction - must match FACTION_ART in launcher.py
FACTION_ART = {
    'north': '002',        # Foltest
    'nilfgaard': '036',    # Emhyr var Emreis
    'scoiatael': '072',    # Francesca Findabair
    'monster': '113',      # Eredin
}

TILE_DIR = os.path.join('cards', 'tiles')


def build_icon():
    icon = pygame.Surface((ICON_SIZE, ICON_SIZE), pygame.SRCALPHA)
    pygame.draw.rect(icon, DARK, (0, 0, ICON_SIZE, ICON_SIZE), border_radius=44)
    pygame.draw.rect(icon, GOLD_DIM, (0, 0, ICON_SIZE, ICON_SIZE), 6,
                     border_radius=44)

    source = next((p for p in BACK_SOURCES if os.path.exists(p)), None)
    if source:
        card = pygame.image.load(source).convert_alpha()
        height = ICON_SIZE - 56
        width = round(height * card.get_width() / card.get_height())
        card = pygame.transform.smoothscale(card, (width, height))

        shadow = pygame.Surface((width + 10, height + 10), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 120), shadow.get_rect(), border_radius=12)
        icon.blit(shadow, (ICON_SIZE // 2 - width // 2 - 5,
                           ICON_SIZE // 2 - height // 2 - 1))

        icon.blit(card, (ICON_SIZE // 2 - width // 2, ICON_SIZE // 2 - height // 2))
        pygame.draw.rect(icon, GOLD,
                         (ICON_SIZE // 2 - width // 2, ICON_SIZE // 2 - height // 2,
                          width, height), 3, border_radius=8)
    else:
        font = pygame.font.SysFont('Georgia,serif', 150, bold=True)
        glyph = font.render('G', True, GOLD)
        icon.blit(glyph, glyph.get_rect(center=(ICON_SIZE // 2, ICON_SIZE // 2)))

    os.makedirs(TILE_DIR, exist_ok=True)
    pygame.image.save(icon, os.path.join(TILE_DIR, 'icon.png'))
    pygame.image.save(pygame.transform.smoothscale(icon, (64, 64)),
                      os.path.join(TILE_DIR, 'icon_64.png'))
    print(f'  icon.png (256x256) and icon_64.png -> {TILE_DIR}')


def build_tiles():
    """Sharp faction tiles in every language, pre-scaled for the launcher."""
    written = 0

    for language in ('de', 'en'):
        target_dir = os.path.join(TILE_DIR, language)
        os.makedirs(target_dir, exist_ok=True)

        for code, card_id in FACTION_ART.items():
            # Prefer the requested language, fall back to the other one
            source = None
            for lang in (language, 'de', 'en'):
                path = os.path.join('cards', lang, 'large', f'{card_id}.png')
                if os.path.exists(path):
                    source = path
                    break
            if source is None:
                print(f'  {language}/{code}: source card {card_id} missing')
                continue

            card = pygame.image.load(source).convert_alpha()

            # Scale so the card covers the tile, then centre-crop the overhang.
            # That fills the tile completely without distorting the artwork.
            scale = max(TILE_W / card.get_width(), TILE_H / card.get_height())
            size = (max(1, round(card.get_width() * scale)),
                    max(1, round(card.get_height() * scale)))
            scaled = pygame.transform.smoothscale(card, size)

            tile = pygame.Surface((TILE_W, TILE_H), pygame.SRCALPHA)
            tile.blit(scaled, ((TILE_W - size[0]) // 2, (TILE_H - size[1]) // 2))

            pygame.image.save(tile, os.path.join(target_dir, f'{code}.png'))
            written += 1

    print(f'  {written} faction tiles ({TILE_W}x{TILE_H}) -> {TILE_DIR}/<language>')


def main():
    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
    pygame.init()
    pygame.display.set_mode((1, 1))

    build_icon()
    build_tiles()

    pygame.quit()


if __name__ == '__main__':
    main()

