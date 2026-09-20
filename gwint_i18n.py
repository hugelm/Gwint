"""Language handling: German / English."""

LANGUAGES = ('de', 'en')

TEXT = {
    # --- general ---
    'game_title':      {'de': 'Gwint',                  'en': 'Gwent'},
    'player':          {'de': 'Spieler',                'en': 'Player'},
    'computer':        {'de': 'Computer',               'en': 'Computer'},
    'faction':         {'de': 'Fraktion',               'en': 'Faction'},
    'cards':           {'de': 'Karten',                 'en': 'Cards'},
    'discard':         {'de': 'Ablage',                 'en': 'Discard'},
    'deck':            {'de': 'Stapel',                 'en': 'Deck'},
    'passed':          {'de': 'GEPASST',                'en': 'PASSED'},
    'rounds':          {'de': 'Runden',                 'en': 'Rounds'},
    'history':         {'de': 'Verlauf',                'en': 'History'},
    'weather':         {'de': 'Wetter',                 'en': 'Weather'},
    'clear_sky':       {'de': 'klar',                   'en': 'clear'},
    'round_label':     {'de': 'Runde',                  'en': 'Round'},

    # --- rows ---
    'melee':           {'de': 'Nahkampf',               'en': 'Close Combat'},
    'ranged':          {'de': 'Fernkampf',              'en': 'Ranged'},
    'siege':           {'de': 'Belagerung',             'en': 'Siege'},
    'horn_slot':       {'de': 'Horn',                   'en': 'Horn'},

    # --- weather ---
    'frost':           {'de': 'Frost',                  'en': 'Frost'},
    'fog':             {'de': 'Nebel',                  'en': 'Fog'},
    'rain':            {'de': 'Regen',                  'en': 'Rain'},

    # --- messages ---
    'new_game_you':    {'de': 'Neue Partie – du beginnst',
                        'en': 'New game – you start'},
    'new_game_ai':     {'de': 'Neue Partie – Computer beginnt',
                        'en': 'New game – computer starts'},
    'you_passed':      {'de': 'Du hast gepasst',        'en': 'You passed'},
    'no_cards_left':   {'de': 'Keine Karten mehr – du passt',
                        'en': 'No cards left – you pass'},
    'round_won':       {'de': 'Runde gewonnen',         'en': 'Round won'},
    'round_lost':      {'de': 'Runde verloren',         'en': 'Round lost'},
    'round_draw':      {'de': 'Unentschieden',          'en': 'Draw'},
    'pick_horn_row':   {'de': 'Reihe für das Horn anklicken',
                        'en': 'Click a row for the horn'},
    'pick_agile_row':  {'de': 'Nahkampf oder Fernkampf anklicken',
                        'en': 'Click close combat or ranged'},
    'pick_decoy':      {'de': 'Eigene Einheit für die Finte anklicken',
                        'en': 'Click one of your units for the decoy'},
    'pick_medic':      {'de': 'Karte zum Wiederbeleben wählen',
                        'en': 'Choose a card to revive'},
    'no_decoy_target': {'de': 'Keine eigene Einheit für die Finte',
                        'en': 'No unit of yours for the decoy'},
    'empty_graveyard': {'de': 'Friedhof ist leer – Heiler wirkt erst ab Runde 2',
                        'en': 'Graveyard is empty – medic works from round 2'},
    'no_revive_target': {'de': 'Nichts zum Wiederbeleben – Helden zählen nicht',
                         'en': 'Nothing to revive – heroes do not count'},
    'north_bonus':     {'de': 'Nördliche Königreiche: eine Karte nachgezogen',
                        'en': 'Northern Realms: one extra card drawn'},
    'arrow_hint':      {'de': 'Pfeiltasten wählen, Eingabe bestätigt',
                        'en': 'Arrow keys to choose, Enter to confirm'},
    'cancelled':       {'de': 'Abgebrochen',            'en': 'Cancelled'},
    'spy_drew':        {'de': 'Spion – nachgezogen',    'en': 'Spy – cards drawn'},
    'muster':          {'de': 'Abruf',                  'en': 'Muster'},
    'medic_revived':   {'de': 'Wiederbelebt',           'en': 'Revived'},
    'scorched':        {'de': 'Verbrannt',              'en': 'Scorched'},
    'not_your_turn':   {'de': 'Der Computer ist am Zug',
                        'en': 'The computer is thinking'},

    # --- end of game ---
    'you_win':         {'de': 'GEWONNEN',               'en': 'YOU WIN'},
    'you_lose':        {'de': 'VERLOREN',               'en': 'YOU LOSE'},
    'draw':            {'de': 'UNENTSCHIEDEN',          'en': 'DRAW'},
    'restart_hint':    {'de': '[N] neues Spiel     [Esc] beenden',
                        'en': '[N] new game     [Esc] quit'},

    # --- card types ---
    'unit':            {'de': 'Einheit',                'en': 'Unit'},
    'hero':            {'de': 'Held',                   'en': 'Hero'},
    'agile':           {'de': 'Wendig',                 'en': 'Agile'},
    'agile_rows':      {'de': 'Nahkampf oder Fernkampf',
                        'en': 'Close combat or ranged'},
    'special_card':    {'de': 'Spezialkarte',           'en': 'Special card'},
    'graveyard':       {'de': 'Friedhof',               'en': 'Graveyard'},

    # --- abilities ---
    'ab_bond':         {'de': 'Bindung',                'en': 'Tight Bond'},
    'ab_spy':          {'de': 'Spion',                  'en': 'Spy'},
    'ab_medic':        {'de': 'Heiler',                 'en': 'Medic'},
    'ab_morale':       {'de': 'Moralbonus',             'en': 'Morale Boost'},
    'ab_horn':         {'de': 'Hornist',                'en': "Commander's Horn"},
    'ab_scorch':       {'de': 'Verbrennen',             'en': 'Scorch'},
    'ab_scorch_melee': {'de': 'Verbrennen (Nahkampf)',  'en': 'Scorch (close combat)'},
    'ab_decoy':        {'de': 'Finte',                  'en': 'Decoy'},
    'ab_muster':       {'de': 'Abruf',                  'en': 'Muster'},
    'ab_frost':        {'de': 'Frost – Nahkampf',       'en': 'Frost – close combat'},
    'ab_fog':          {'de': 'Nebel – Fernkampf',      'en': 'Fog – ranged'},
    'ab_rain':         {'de': 'Regen – Belagerung',     'en': 'Rain – siege'},
    'ab_clear':        {'de': 'Gutes Wetter',           'en': 'Clear Weather'},

    # --- factions ---
    'fac_north':       {'de': 'Nördliche Königreiche',  'en': 'Northern Realms'},
    'fac_nilfgaard':   {'de': 'Nilfgaard',              'en': 'Nilfgaard'},
    'fac_scoiatael':   {'de': "Scoia'tael",             'en': "Scoia'tael"},
    'fac_monster':     {'de': 'Monster',                'en': 'Monsters'},

    # --- faction descriptions (launcher) ---
    'desc_north':      {'de': 'Viele Bindungen und Spione, starke Belagerung',
                        'en': 'Many bonds and spies, strong siege row'},
    'desc_nilfgaard':  {'de': 'Spionagelastig, breite Fernkampfreihe',
                        'en': 'Spy heavy, wide ranged row'},
    'desc_scoiatael':  {'de': 'Starke Einzelkarten, viele Heiler',
                        'en': 'Strong single cards, many medics'},
    'desc_monster':    {'de': 'Abruf-Ketten füllen das Feld im Nu',
                        'en': 'Muster chains fill the board fast'},

    # --- controls ---
    'controls':        {'de': 'Steuerung',              'en': 'Controls'},
    'ctrl_play':       {'de': 'Klick / Eingabe – ausspielen',
                        'en': 'Click / Enter – play card'},
    'ctrl_select':     {'de': 'Pfeiltasten – Karte wählen',
                        'en': 'Arrow keys – select card'},
    'ctrl_pass':       {'de': 'Leertaste – passen',     'en': 'Space – pass round'},
    'ctrl_misc':       {'de': 'G Friedhof, F3 Sprache, F11 Vollbild',
                        'en': 'G graveyard, F3 language, F11 fullscreen'},

    # --- launcher ---
    'launcher_name':   {'de': 'Spielername',            'en': 'Player name'},
    'launcher_start':  {'de': 'Spiel starten',          'en': 'Start game'},
    'launcher_lang':   {'de': 'Sprache',                'en': 'Language'},
    'launcher_choose': {'de': 'Wähle deine Fraktion',   'en': 'Choose your faction'},
    'assets_missing':  {'de': 'Kartenbilder fehlen – bitte zuerst tools/build_assets.py ausführen',
                        'en': 'Card images missing – please run tools/build_assets.py first'},
}

class Translator(object):
    def __init__(self, language='de'):
        self.language = language if language in LANGUAGES else 'de'

    def toggle(self):
        index = (LANGUAGES.index(self.language) + 1) % len(LANGUAGES)
        self.language = LANGUAGES[index]
        return self.language

    def __call__(self, key, default=None):
        entry = TEXT.get(key)
        if entry is None:
            return default if default is not None else key
        return entry.get(self.language, entry.get('de', key))

    def card_name(self, card):
        """Card name in the active language, taken from the card itself."""
        return card.display_name(self.language)

    def faction(self, code):
        return self(f'fac_{code}', code)

    def faction_description(self, code):
        return self(f'desc_{code}', '')

    def ability(self, ability):
        return self(f'ab_{ability}', ability) if ability else ''

    def row(self, index):
        return self(('melee', 'ranged', 'siege')[index])

