"""Plays full games headless - catches crashes and endless loops."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bootstrap  # noqa: F401,E402  - sets sys.path, cwd and headless mode

import random

import pygame  # noqa: E402

import Gwint  # noqa: E402

RESOLUTIONS = [(1180, 720), (1600, 900), (1920, 1080)]

def settle(app, limit=60):
    """Finish every running animation so the next move can start."""
    steps = 0
    while app.busy and steps < limit:
        app.tick_timers(0.1)
        steps += 1

def user_move(app):
    """A random but legal move for the human side."""
    hand = app.visible_hand()
    if not hand or random.random() < 0.06:
        app.pass_round()
        return

    app.selected = random.randrange(len(hand))
    card = app.selected_card()

    if card.ability == 'horn' and card.is_special:
        app.play_selected(target_row=random.randrange(3))
    elif card.ability == 'decoy':
        own = [c for row in app.user.rows for c in row if not c.hero]
        if own:
            app.play_selected(decoy_target=random.choice(own))
        else:
            app.pass_round()
    elif card.ability == 'medic':
        options = app.game.revivable(app.user)
        app.play_selected(medic_target=random.choice(options) if options else None)
    else:
        app.play_selected()

    # A medic may now be waiting for a graveyard pick
    if app.pending and app.pending[0] == 'medic':
        options = app.game.revivable(app.user)
        medic = app.pending[1]
        visible = app.visible_hand()
        if options and medic in visible:
            app.selected = visible.index(medic)
            app.play_selected(medic_target=random.choice(options))
        else:
            app.pending = None
            app.grave_view = None

def simulate(seed, faction, size):
    random.seed(seed)
    app = Gwint.GwintApp('Tester', random.choice(['de', 'en']), intro=False)
    app.layout.update(*size)
    app.new_game(faction)

    steps = 0
    while not app.game_over and steps < 2000:
        steps += 1
        settle(app)

        if app.user_turn and not app.user.passed:
            user_move(app)
        elif not app.ai.passed:
            app.ai_move()
        else:
            app.user_turn = True
            if app.user.passed:
                break

        settle(app)
        app.render()

    # Draw the special views once as well
    app.grave_view = 'user'
    app.render()
    app.grave_view = None
    app.spy_reveal = app.user.hand[:2]
    app.spy_timer = 1.0
    app.render()

    return app, steps

def main():
    pygame.init()
    factions = ['north', 'nilfgaard', 'scoiatael', 'monster']
    played = 0

    for faction in factions:
        for seed in range(5):
            size = RESOLUTIONS[seed % len(RESOLUTIONS)]
            app, steps = simulate(seed, faction, size)
            winner = app.game.winner()
            name = winner.name if winner else 'draw'
            assert app.game_over, f'{faction}/{seed}: game did not end ({steps})'
            assert steps < 2000, f'{faction}/{seed}: endless loop'
            played += 1
            print(f'{faction:10s} seed {seed} {size[0]}x{size[1]}: {steps:4d} steps, '
                  f'opponent {app.ai.faction:10s} winner: {name}')

    pygame.quit()
    print(f'\n{played} games across all factions and resolutions '
          f'completed without a crash.')

if __name__ == '__main__':
    main()

