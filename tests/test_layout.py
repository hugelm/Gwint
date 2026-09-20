"""Checks the layout for overlaps and overflow across many resolutions."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bootstrap  # noqa: F401,E402  - sets sys.path, cwd and headless mode

import pygame  # noqa: E402

from gwint_ui import Layout, spread_positions  # noqa: E402

RESOLUTIONS = [
    (1180, 720), (1280, 720), (1366, 768), (1440, 900),
    (1600, 900), (1680, 1050), (1920, 1080), (2560, 1440),
]

checks = []

def check(label, ok, detail=''):
    checks.append(bool(ok))
    print(f'{"OK  " if ok else "FAIL"} {label}{" - " + detail if detail else ""}')

def main():
    pygame.init()
    pygame.display.set_mode((1, 1))

    for width, height in RESOLUTIONS:
        lay = Layout(width, height)
        tag = f'{width}x{height}'
        screen = pygame.Rect(0, 0, width, height)

        # 1. Rows must not run into the sidebar or the info column
        for i, row in enumerate(lay.rows):
            check(f'{tag}: row {i} clear of the sidebar',
                  not row.colliderect(lay.sidebar))
            check(f'{tag}: row {i} clear of the info column',
                  row.left >= lay.info_x + lay.info_w)
            check(f'{tag}: row {i} inside the window', screen.contains(row))

        # 2. Panels must not overlap each other
        check(f'{tag}: AI panel vs AI graveyard',
              not lay.ai_panel.colliderect(lay.ai_grave))
        check(f'{tag}: player panel vs player graveyard',
              not lay.user_panel.colliderect(lay.user_grave))
        check(f'{tag}: the two graveyard buttons',
              not lay.ai_grave.colliderect(lay.user_grave))
        check(f'{tag}: the two player panels',
              not lay.ai_panel.colliderect(lay.user_panel))

        # 3. Everything has to stay inside the window
        for name, rect in (('sidebar', lay.sidebar), ('hand', lay.hand),
                           ('message', lay.message), ('ai_panel', lay.ai_panel),
                           ('user_panel', lay.user_panel),
                           ('ai_grave', lay.ai_grave),
                           ('user_grave', lay.user_grave)):
            check(f'{tag}: {name} inside the window', screen.contains(rect),
                  f'{tuple(rect)}')

        # 4. Vertical stacking
        check(f'{tag}: rows above the message strip',
              lay.rows[-1].bottom <= lay.message.top)
        check(f'{tag}: message strip above the hand',
              lay.message.bottom <= lay.hand.top)
        check(f'{tag}: hand clear of the player panel',
              not lay.hand.colliderect(lay.user_panel))

        # 5. Score badge must not reach into the info column
        check(f'{tag}: score badge right of the info column',
              lay.score_x - lay.badge_r >= lay.info_x + lay.info_w)

        # 6. Card area has to fit inside the row
        check(f'{tag}: card area inside the row',
              lay.cards_x + lay.cards_w <= lay.rows[0].right)
        check(f'{tag}: cards fit the row height', lay.card_h <= lay.row_h)

        # 7. Many cards must not spill out of the row
        for count in (1, 5, 10, 16, 22):
            xs = spread_positions(count, lay.cards_x + lay.cards_w // 2,
                                  lay.cards_w, lay.card_w)
            if xs:
                check(f'{tag}: {count} cards inside the area',
                      xs[0] >= lay.cards_x - 1
                      and xs[-1] + lay.card_w <= lay.cards_x + lay.cards_w + 1)

        # 8. Hand cards must not spill out either
        cw, ch = lay.hand_card_size()
        for count in (1, 10, 14, 20):
            xs = spread_positions(count, lay.hand.centerx, lay.hand.w - 20, cw)
            if xs:
                check(f'{tag}: {count} hand cards inside the area',
                      xs[0] >= lay.hand.left - 1
                      and xs[-1] + cw <= lay.hand.right + 1)
        check(f'{tag}: hand card fits the height', ch <= lay.hand.h)

        # 9. Weather and horn slots sit inside their row and never overlap
        for i in range(6):
            w = lay.weather_slot(i)
            h = lay.horn_slot(i)
            check(f'{tag}: weather slot {i} inside the row', lay.rows[i].contains(w))
            check(f'{tag}: horn slot {i} inside the row', lay.rows[i].contains(h))
            check(f'{tag}: slots {i} do not overlap', not w.colliderect(h))
            check(f'{tag}: slots {i} left of the cards', h.right <= lay.cards_x)

    pygame.quit()

    print()
    if all(checks):
        print(f'All {len(checks)} layout checks passed '
              f'({len(RESOLUTIONS)} resolutions).')
    else:
        print(f'{checks.count(False)} of {len(checks)} layout checks FAILED.')
        raise SystemExit(1)

if __name__ == '__main__':
    main()

