"""Extracts the original cards from the ZIP archives and scales them
to the sizes the game uses.

Source:
    assets_src/*.zip           the two original archives

Result:
    cards/de/small/<id>.png    86x130  (hand / board)
    cards/de/large/<id>.png   300x450  (detail view)
    cards/en/small/<id>.png   same for English
    cards/en/large/<id>.png

Usage:  python tools/build_assets.py [--force]
"""
import os
import re
import sys
import zipfile

import pygame

# The script lives in tools/, everything it reads and writes sits one level up
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(BASE_DIR)

SMALL_SIZE = (86, 130)
LARGE_SIZE = (300, 450)

# Where the untouched archives are kept (too large for the repository)
SOURCE_DIR = 'assets_src'

# Per language: the ZIP file and a regex yielding the card number.
#   DE: gwint_013_north_blaue_streifen.png
#   EN: gwint_en_013_north_blue_stripes.png
SOURCES = {
    'de': {
        'zip': 'gwint_205_karten_ohne_ueberdruck_2015_06_22_DE.zip',
        'pattern': re.compile(r'^gwint_(\d{3})_[a-z]+_'),
        'back': re.compile(r'^gwint_000_a_back_?\.png$'),
    },
    'en': {
        'zip': 'gwent_205_cards_without_bleeding_2015_06_21_EN.zip',
        'pattern': re.compile(r'^gwint_en_(\d{3})_[a-z]+_'),
        # The English archive names the file 'gwint_en_000_a_back_.png'
        'back': re.compile(r'^gwint_en_000_a_back_?\.png$'),
    },
}

SKIP_MARKERS = ('alternative', '_alt', 'rules')


def build_language(code, config, force=False):
    zip_name = os.path.join(SOURCE_DIR, config['zip'])
    if not os.path.exists(zip_name):
        print(f'  {code}: ZIP missing, skipped ({zip_name})')
        return 0

    small_dir = os.path.join('cards', code, 'small')
    large_dir = os.path.join('cards', code, 'large')
    os.makedirs(small_dir, exist_ok=True)
    os.makedirs(large_dir, exist_ok=True)

    written = 0
    with zipfile.ZipFile(zip_name) as archive:
        for name in sorted(archive.namelist()):
            base = os.path.basename(name)

            if any(marker in base for marker in SKIP_MARKERS):
                continue
            match = config['pattern'].match(base)
            if not match:
                continue

            card_id = match.group(1)
            small_path = os.path.join(small_dir, f'{card_id}.png')
            large_path = os.path.join(large_dir, f'{card_id}.png')

            # First file per number wins (several artworks share one id)
            if not force and os.path.exists(small_path) and os.path.exists(large_path):
                continue

            with archive.open(name) as handle:
                surface = pygame.image.load(handle, base).convert_alpha()

            pygame.image.save(pygame.transform.smoothscale(surface, SMALL_SIZE), small_path)
            pygame.image.save(pygame.transform.smoothscale(surface, LARGE_SIZE), large_path)
            written += 1

        # Card back
        found_back = False
        for name in archive.namelist():
            if config['back'].match(os.path.basename(name)):
                with archive.open(name) as handle:
                    back = pygame.image.load(handle, 'back.png').convert_alpha()
                pygame.image.save(pygame.transform.smoothscale(back, SMALL_SIZE),
                                  os.path.join(small_dir, 'back.png'))
                found_back = True
                break
        if not found_back:
            print(f'  {code}: warning - no card back found')

    print(f'  {code}: {written} cards -> {small_dir}, {large_dir}')
    return written


def main():
    force = '--force' in sys.argv

    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
    pygame.init()
    pygame.display.set_mode((1, 1))

    total = 0
    for code, config in SOURCES.items():
        total += build_language(code, config, force)

    pygame.quit()
    print(f'Done: {total} card images written.')


if __name__ == '__main__':
    main()

