"""Checks the translations for completeness and proper German spelling."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bootstrap  # noqa: F401,E402  - sets sys.path, cwd and headless mode

import re

from gwint_i18n import LANGUAGES, TEXT, Translator  # noqa: E402
from gwint_rules import load_card_pool  # noqa: E402

checks = []

def check(label, ok, detail=''):
    checks.append(bool(ok))
    print(f'{"OK  " if ok else "FAIL"} {label}{" - " + detail if detail else ""}')

# 1. Every entry has to cover all languages
for key, entry in TEXT.items():
    missing = [lang for lang in LANGUAGES if lang not in entry or not entry[lang]]
    check(f'text "{key}" complete', not missing, ','.join(missing))

# 2. German strings must use real umlauts, never ae/oe/ue transcriptions.
#    Words where the letter pair is genuine (or a proper noun) are allowed.
ALLOWED = {
    # genuine German spellings
    'zuerst', 'Steuerung', 'neue', 'neues', 'Neue', 'auerdem', 'Feuer',
    'teuer', 'heute', 'Leute', 'Freude', 'Auswahl', 'Bauer',
    # proper nouns from the Witcher universe
    'Scoia', 'tael', "Scoia'tael", 'aep', 'aen', 'Coehoorn', 'Kaedwen',
    'Kaedwen-Belagerungsexperte', 'Nausicaa', 'Saesenthessis', 'Faoiltiarna',
    'Yaevinn', 'Caerme', 'Oesterlen', 'Shilard', 'Fitz-Oesterlen',
    'Vreemde', 'Sweers', 'Emean', 'Easnillien', 'Matsen', 'Renuald',
    'Ceallach', 'Cahir', 'Ciaran', 'Ida', 'Menno', 'Havekar', 'Mahakam',
    'Blathanna', 'Toruviel', 'Riordain', 'Isengrim', 'Filavandrel',
    'Barclay', 'Els', 'Milva', 'Iorweth', 'Eithne', 'Draug', 'Kayran',
}
TRANSCRIPTION = re.compile(r'(?<![aeiouäöü])(ae|oe|ue)(?![iu])', re.IGNORECASE)

def transcription_hits(value):
    hits = []
    for word in re.findall(r"[A-Za-zÄÖÜäöüß'-]+", value):
        if word in ALLOWED or any(part in ALLOWED for part in word.split('-')):
            continue
        if TRANSCRIPTION.search(word):
            hits.append(word)
    return hits

for key, entry in TEXT.items():
    hits = transcription_hits(entry.get('de', ''))
    check(f'german "{key}" uses real umlauts', not hits, ', '.join(hits))

# 3. Every card carries a name in both languages
pool = load_card_pool()
cards = [c for cards in pool.values() for c in cards]
names = sorted({c.name for c in cards})

missing_en = sorted({c.name for c in cards
                     if not c.names.get('en') or c.names['en'] == c.name})
# A handful of names are identical in both languages, that is legitimate
IDENTICAL_OK = {'Vernon Roche', 'Ves', 'Thaler', 'Yaevinn', 'Milva', 'Detmold',
                'Draug', 'Kayran', 'Gargoyle', 'Wyvern', 'Regis', 'Vesemir',
                'Eredin', 'Imlerith', 'Toruviel', 'Riordain', 'Vreemde',
                'Sweers', 'Albrich', 'Cynthia', 'Vanhemar', 'Puttkammer',
                'Morteisen', 'Rainfarn', 'Eithne', 'Nekker', 'Endriaga',
                'Ballista', 'Villentretenmerth', 'Triss Merigold', 'Keira Metz',
                'Philippa Eilhart', 'Sabrina Glevissig', 'Assire var Anahid',
                'Fringilla Vigo', 'Menno Coehoorn', 'Stefan Skellen',
                'Shilard Fitz-Oesterlen', 'Tibor Eggebracht', 'Morvran Voorhis',
                'Vattier de Rideaux', 'Isengrim Faoiltiarna', 'Saesenthessis',
                'Dennis Cranmer', 'Barclay Els', 'Ciaran aep Easnillien',
                'Ida Emean aep Sivney', 'Sheala de Tancarville',
                'Renuald aep Matsen', 'Cahir aep Ceallach', 'Zoltan Chivay',
                'Yarpen Zigrin', 'Sigismund Dijkstra', 'Nausicaa-Kavalleriebrigade'}
unexpected = [n for n in missing_en if n not in IDENTICAL_OK]
check('every card has an english name', not unexpected, ', '.join(unexpected[:6]))

# 4. German card names must not contain transcriptions either
bad_names = [n for n in names if transcription_hits(n)]
check('german card names use real umlauts', not bad_names, ', '.join(bad_names[:6]))

# 5. Every ability in the pool needs a label
abilities = sorted({c.ability for cards in pool.values() for c in cards if c.ability})
for ability in abilities:
    check(f'ability "{ability}" translated', f'ab_{ability}' in TEXT)

# 6. Every faction needs a name and a description
for faction in pool:
    if faction == 'neutral':
        continue
    check(f'faction "{faction}" translated', f'fac_{faction}' in TEXT)
    check(f'faction "{faction}" described', f'desc_{faction}' in TEXT)

# 7. The translator behaves sensibly in both languages
for lang in LANGUAGES:
    tr = Translator(lang)
    check(f'{lang}: title present', bool(tr('game_title')))
    check(f'{lang}: unknown key falls back', tr('does_not_exist') == 'does_not_exist')
    check(f'{lang}: row names', bool(tr.row(0)) and bool(tr.row(2)))
    check(f'{lang}: faction description', bool(tr.faction_description('north')))

# 8. Switching works
tr = Translator('de')
check('switch de -> en', tr.toggle() == 'en')
check('switch en -> de', tr.toggle() == 'de')

# 9. Card names really differ between languages
tr_de, tr_en = Translator('de'), Translator('en')
sample = [c for cards in pool.values() for c in cards if c.name == 'Klirrende Kälte']
if sample:
    card = sample[0]
    check('card name translated', tr_en.card_name(card) == 'Biting Frost',
          tr_en.card_name(card))
    check('german name kept', tr_de.card_name(card) == 'Klirrende Kälte')

print()
if all(checks):
    print(f'All {len(checks)} i18n checks passed.')
else:
    print(f'{checks.count(False)} of {len(checks)} i18n checks FAILED.')
    raise SystemExit(1)

