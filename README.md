# Gwent

**Gwent** (German: *Gwint*), the card game from The Witcher 3, rebuilt as a
standalone game in Python and pygame. Four factions, every special card,
German and English.

---

# Part 1 – For Players

## Installation

You need **Python 3.10+** and pygame:

```bash
pip install pygame
pip install numpy       # optional, only for tests/test_artwork.py
```

That is all – the card images ship with the repository, so you can start
playing right away.

Only if you want to rebuild them: the images come from two ZIP archives of the
original cards. At about 224 MB each they are past GitHub's 100 MB limit for a
single file, so they are not in the repository. Drop them into `assets_src/`
and run

```bash
python tools/build_assets.py     # card images from the two ZIP archives
python tools/make_icon.py        # window icon and launcher tiles
```

This takes about a minute and writes roughly 700 images into `cards/`.

## Playing

```bash
python launcher.py
```

The launcher lets you pick a name, a faction and a language, and plays the
menu theme while you decide. You can also start the game directly:

```bash
python Gwint.py                                  # uses your stored settings
python Gwint.py --language en --faction monster  # override them
python Gwint.py --fullscreen --no-intro --no-music
python Gwint.py --help                           # all options
```

Your choices are remembered between sessions (see *Settings* below).

## What is it about?

Two players face each other with one deck each. Whoever wins **two out of
three rounds** wins the match.

Here is the twist: you get **ten cards at the start and draw almost nothing
afterwards**. Everything you burn in round one is gone later. The single most
important decision in Gwent is often to **give a round away on purpose** so
you can overwhelm your opponent in the other two.

## Flow of a round

You take turns. On your turn you have exactly two options:

- **Play a card** – it goes into its row
- **Pass** – you are out for the rest of the round

Once both players have passed the round ends. Whoever has more points on the
board wins it, and the loser loses a life (shown as a red gem). On a draw
**both** players lose one.

Afterwards the whole board is swept into the graveyard.

## Controls

| Input | Effect |
|---|---|
| **Mouse click** | Select a card; a second click on the same card plays it |
| **Arrow keys** ← → | Select a card in your hand |
| **Enter** | Play the selected card |
| **Space** | Pass the round |
| **G** | Open your graveyard |
| **F2** | Switch faction (starts a new game) |
| **F3** | Switch language (German / English) |
| **F11** | Toggle fullscreen |
| **N** | New game (once the match is over) |
| **Esc** | Cancel a selection / quit |

Whenever a card needs a target – a row for the Commander's Horn, close combat
or ranged for an agile unit, a card to revive, a unit for the decoy – the
**arrow keys step through the options** and **Enter confirms**. The current
option is outlined in gold. Everything can be done with the mouse just as well.

The window can be resized freely; the layout follows along.

## The three rows

Every unit belongs to a fixed row:

| Row | Typical cards |
|---|---|
| **Close combat** | Swordsmen, monsters |
| **Ranged** | Archers, mages |
| **Siege** | Catapults, trebuchets |

Your rows are the bottom three, your opponent's are the top three.

To the left of every row sit two small slots: one for the **weather card**
affecting that row, one for the **Commander's Horn**. Cards played there are
shown as real cards, not as text.

**Agile** units (for example Yaevinn or Toruviel) can be placed in *either*
close combat or the ranged row. When you play one, both valid rows light up
green and you pick where it goes – useful for dodging a weather card.

## Cards in hand

You get **ten cards at the start and draw nothing afterwards**. There is one
exception: the **Northern Realms** draw one extra card for every round they
win. Everything else you spend is gone for good, which is what makes passing
early such a strong move.

## Card abilities

| Ability | Effect |
|---|---|
| **Tight Bond** | Several cards of the same name boost each other. Three 4-point cards are not 12 but **36** points. |
| **Morale Boost** | Gives every *other* card in the row +1. |
| **Commander's Horn** | Doubles the row. Only one per row. |
| **Agile** | May be played into close combat or ranged – dodge a weather card by choosing the other row. |
| **Spy** | Lands on your **opponent's** side and scores for them – in exchange you draw 2 cards. The key to card advantage. |
| **Medic** | Brings a unit back from your graveyard. **You pick which one.** Heroes cannot be revived, and in round one the graveyard is still empty. |
| **Scorch** | Destroys the strongest unit on the board – including your own if it happens to be the strongest. |
| **Decoy** | Pulls one of your units off the board back into your hand. Saves spies and medics for the next round. |
| **Muster** | Immediately pulls every card of the same name out of your deck and hand onto the board. Playing one Dwarven Skirmisher brings all three. |

**Heroes** (golden frame) ignore weather and scorch – nothing touches them.

Tight Bond and Muster look similar but are not: **Bond** multiplies cards you
already played into the same row, **Muster** fetches the copies out of your
deck for free. The Northern Realms and Nilfgaard use Bond, the Scoia'tael and
the Monsters use Muster.

## Weather cards

Weather hits **both sides** at once and drops every unit in a row to 1 point:

| Card | Affected row |
|---|---|
| Biting Frost | Close combat |
| Impenetrable Fog | Ranged |
| Torrential Rain | Siege |
| **Clear Weather** | removes *all* weather effects |

## The factions

| Faction | Character |
|---|---|
| **Northern Realms** | Lots of bonds and spies, strong siege row |
| **Nilfgaard** | Spy heavy, wide ranged row |
| **Scoia'tael** | Strong single cards, many medics and bonds |
| **Monsters** | Muster chains that fill the board fast |

## Tips for getting started

1. **Spies are worth their weight in gold.** You hand your opponent a few
   points but draw two cards. Over a full match that almost always wins.
2. **Lose round one cheaply.** If your opponent commits heavily, pass early.
   You keep those cards for rounds two and three.
3. **Hold your weather cards** until your opponent has stacked a row.
4. **Count your opponent's hand** (shown in their panel). Whoever holds more
   cards at the end usually takes the last round.
5. **Only play bond cards together** – on their own they are weak.
6. **Medics are useless in round one** because the graveyard is still empty.

---

# Part 2 – Technical Documentation

## Architecture

The core idea: **the rules know nothing about pygame.** That lets the entire
game logic run headless, so over 900 checks finish in a few seconds.

```
┌─────────────────────────────────────────────┐
│ Gwint.py          window, input, AI         │  ← pygame
│ gwint_ui.py       layout, colours, images   │  ← pygame
├─────────────────────────────────────────────┤
│ gwint_game.py     game state, card effects  │  ← pure
│ gwint_rules.py    cards, scoring, decks     │  ← pure
│ gwint_i18n.py     translations              │  ← pure
│ gwint_config.py   settings, command line    │  ← pure
├─────────────────────────────────────────────┤
│ cards.json        card data                 │
└─────────────────────────────────────────────┘
```

```
Gwint/
├── Gwint.py            window, input, rendering, AI
├── gwint_ui.py         layout, colours, image cache
├── gwint_game.py       game state, card effects, round scoring
├── gwint_rules.py      card model, deck building, scoring
├── gwint_i18n.py       interface translations
├── gwint_config.py     settings and command line
├── cards.json          all card data, both languages
├── launcher.py         start window
├── run_tests.py        runs everything in tests/
├── tools/
│   ├── build_assets.py unpacks the card ZIPs
│   └── make_icon.py    icon and launcher tiles
├── tests/
│   ├── _bootstrap.py   sys.path, working directory, headless mode
│   └── test_*.py       twelve suites
├── assets_src/         the two original ZIPs (local only, ~224 MB each)
├── cards/              card images and launcher tiles (in the repository)
├── music/              menu and game themes
└── sounds/             card and round effects
```

| File | Responsibility |
|---|---|
| `gwint_rules.py` | `Card`, `load_card_pool()`, `build_deck()`, `row_values()`, `row_score()` |
| `gwint_game.py` | `Player`, `Game` – playing cards, effects, round scoring |
| `gwint_i18n.py` | `Translator` and the interface text catalogue |
| `gwint_config.py` | `Settings` – persistence and command line hand-off |
| `gwint_ui.py` | `Layout` (derives every rectangle), image cache, drawing helpers |
| `Gwint.py` | `GwintApp` – main loop, input, rendering, AI, `CardFlight`, `Intro` |
| `tools/build_assets.py` | Unpacks both ZIPs and scales every card |
| `tools/make_icon.py` | Builds `icon.png` and the sharp launcher tiles |
| `launcher.py` | Tkinter start window with the leader card picker |
| `cards.json` | All card data including both names – no values live in the code |

## Settings

There is no scratch file in the project folder any more. Two mechanisms,
cleanly separated:

**Persistence** – `gwint_config.Settings` stores a JSON file where the
operating system wants it:

| OS | Location |
|---|---|
| Windows | `%APPDATA%\Gwent\settings.json` |
| macOS | `~/Library/Application Support/Gwent/settings.json` |
| Linux | `$XDG_CONFIG_HOME/Gwent/settings.json` or `~/.config/Gwent/…` |

Writing is atomic (`.tmp` plus `os.replace`), so a crash cannot leave a broken
file behind. A missing or corrupt file silently falls back to the defaults.

**Hand-off** – the launcher does not leave a file for the game to pick up, it
passes command line arguments:

```python
subprocess.run([sys.executable, 'Gwint.py'] + settings.to_argv())
```

That is explicit, free of race conditions and works with several instances at
once. `from_command_line()` merges both sources, with the command line winning:

```python
settings = from_command_line()      # file + argv
settings.faction = 'monster'
settings.save()
```

## Turn handover

`after_move(mover)` decides who acts next and **needs to know who moved**:

```python
if mover is self.user:
    self.user_turn = self.ai.passed        # opponent, unless they passed
else:
    self.user_turn = not self.user.passed  # you, unless you passed
```

Getting this wrong stalls the game – a shared handler that always set
`user_turn = True` meant the AI never got a turn. `test_interaction.py` now
pins the handover down in both directions.

## Round end

`Game.resolve_round()` scores the board, takes a life from the loser (or from
both on a draw), sweeps everything into the graveyards and clears the weather.

**No cards are drawn.** You keep the ten you started with – that is what makes
the decision to pass early meaningful. The single exception is the Northern
Realms faction bonus: winning a round draws one extra card. It lives in
`GwintApp.finish_round()`:

```python
if not self.game_over and winner is not None:
    if winner.faction == 'north':
        winner.draw(1)
```

An earlier version handed **both** players two cards after every round, which
quietly removed the card-advantage layer from the game. `test_regression.py`
now asserts the hand size after a round end.

## Assets

A card in `cards.json`:

```json
{ "id": "095",
  "name": { "de": "Zwergen-Scharmützler", "en": "Dwarven Skirmisher" },
  "strength": 3, "row": "melee", "ability": "muster", "count": 3 }
```

| Field | Meaning |
|---|---|
| `id` | File name under `cards/<language>/small/` and `/large/` |
| `name` | Both languages. **The German name is the card's identity** – muster and tight bond compare on it, so switching language cannot break them. |
| `row` | `melee`, `ranged`, `siege`, `agile`, `special`, `weather` |
| `ability` | `bond`, `spy`, `medic`, `morale`, `horn`, `scorch`, `scorch_melee`, `decoy`, `muster`, `frost`, `fog`, `rain`, `clear` |
| `hero` | `true` → immune to weather and scorch, cannot be revived |
| `count` | How many copies sit in the deck |

Names live on the card, not in the translation catalogue. `gwint_i18n.py`
holds interface text only; `Translator.card_name(card)` forwards to
`card.display_name(language)`. Adding a card therefore means one entry in
`cards.json` and nothing else.

`row: "agile"` marks a unit that may go into close combat **or** ranged.
`Card.allowed_rows` returns every legal row, `Card.row_index` the default one.
`Game._place()` refuses a row the card is not allowed in, so a malformed call
cannot put an agile unit into the siege row.

`tests/test_carddata.py` guards this file with 658 structural checks: valid
row names, strength where it belongs, weather abilities only on weather cards,
agile only on units, every faction able to fill all three rows, bond and
muster only on cards that actually have copies, and all copies of one card
agreeing on row and ability.

New cards need **no code change** – an entry in `cards.json` is enough as long
as the ability already exists.

## Scoring

`row_values(cards, weather, horn)` returns `[(card, effective value), ...]`
and is the only place where scoring happens. The order follows the original
game:

```
1. weather  → value = 1 (heroes excluded)
2. bond     → value × number of cards with the same name
3. morale   → + number of morale cards (excluding itself)
4. horn     → value × 2
```

`row_score()` sums it up, `card_value()` picks a single value out – the latter
is what scorch needs to find the strongest target.

## Layout

`gwint_ui.Layout` derives **every** rectangle from the window size. There are
no fixed pixel positions left. `Layout.update(w, h)` runs on every
`VIDEORESIZE`.

```python
lay = Layout(1600, 900)
lay.rows[0]           # top row (opponent siege)
lay.weather_slot(0)   # weather card slot for that row
lay.horn_slot(0)      # commander's horn slot
lay.sidebar           # right hand column
lay.hand              # hand card area
```

`spread_positions(count, center_x, width, item_w)` centres cards and lets them
overlap when space runs out – the same function serves the hand and the board,
so selection frames never drift away from their card.

`test_layout.py` checks 8 resolutions from 1180×720 to 2560×1440 for overlaps,
overflow and elements outside the window.

## Animations

Cards are **animated before they land**, never after:

1. `play_selected()` puts the card into `self.flying`, so it disappears from
   the hand immediately and the hand re-flows.
2. A `CardFlight` is queued and flies for `FLIGHT_TIME` seconds.
3. `commit(callback, delay)` defers the actual rules call. When the flight
   ends, `game.play(...)` runs and the card appears on the board.

While `self.animations` or `self.deferred` hold anything, `app.busy` is `True`
and no new move is accepted. Tests call `tick_timers(dt)` in a loop to fast
forward.

`Intro` is the title sequence: cards fan in from below, the title fades in,
then everything dissolves into the board. Any key or click skips it.

## Card effects and feedback

`Game.play()` reports side effects through `Game.last_effect`:

```python
game.play(player, card, target_row=None, decoy_target=None, medic_target=None)

game.last_effect  # {'drawn': [...]}     spy: the cards drawn
                  # {'revived': card}    medic
                  # {'scorched': [...]}  scorch
                  # {'mustered': [...]}  muster
```

The UI reads this in `show_effects()` and, for example, shows the cards a spy
drew large in the centre of the screen.

Cards that need a target use `app.pending = (kind, card)`:
`'horn'` (click a row or its horn slot), `'decoy'` (click one of your units),
`'medic'` (the graveyard opens automatically). `Game.revivable(player)` returns
the legal medic targets; heroes and special cards are excluded.

Weather cards and the Commander's Horn are kept as real card objects
(`Game.weather_cards`, `Player.horns`) so the UI can draw them in their slot
instead of printing a label.

## Languages

`Translator` wraps the interface text:

```python
tr('rounds')                  # interface text
tr.card_name(card)            # forwards to card.display_name(language)
tr.faction('north')           # faction name
tr.ability('bond')            # ability name
tr.row(0)                     # row name
```

Card names are **not** in the catalogue – they sit in `cards.json` next to the
card they belong to. `Card.name` always returns the German name and serves as
the card's identity; `Card.display_name(language)` is what the interface
shows.

Card images follow along: `gwint_ui.set_language()` clears the image cache,
after which `card_image()` loads from `cards/<language>/`. If an image is
missing it falls back to German.

`test_i18n.py` fails as soon as an interface text is missing in one language
or a card lacks an English name, and it rejects German strings that use
`ae`/`oe`/`ue` instead of real umlauts.

## Verifying the data against the artwork

The card rows are **not** guesswork any more – they are read off the pictures.
`tests/test_artwork.py` does this on every run.

**How it works.** Grouping the cards by row and averaging each group into a
composite reveals where the groups differ while staying consistent inside a
group. Exactly one such spot exists, at `x=14..62, y=112..180` on the
300×450 artwork: the row symbol. No OCR, just pixel statistics.

Templates are averaged from Northern Realms cards whose rows are beyond doubt
(the archive numbers them in row order), and every card is matched against
them by correlation.

**Why the result can be trusted:**

| Evidence | Result |
|---|---|
| Template sharpness | 0.98 – 1.00 inside a row |
| Leave-one-out on 30 reference cards | 30/30 correct without themselves |
| Special and weather cards (no row symbol) | score 0.01 – 0.18, as expected |
| Agile symbol, isolated by clustering | own group, 0.92 – 0.97 |

The negative control matters most: special cards score near zero, which proves
the region really is the row symbol and not some shared decoration.

**16 rows were wrong** and got corrected, among them four cards that were not
agile at all (Toruviel, Riordain, Vrihedd Recruit, Dol Blathanna Archer) and
four that are (Barclay Els, Filavandrel, Kayran, both Harpies).

Six cards cannot be read: the neutral heroes and Eredin. Their corner is
styled differently, and `113` uses leader artwork. They are listed as known
exceptions instead of failing the test.

**Strength values could not be verified this way.** The same analysis on the
number in the corner gives 0.80 similarity within a group against 0.47
between groups – a signal, but nowhere near the 0.98 of the row symbol. Four
cards look suspicious and are worth checking by hand:

| Card | `cards.json` | Artwork suggests |
|---|---|---|
| Leshen | 2 | 10 |
| Milva | 10 | 4 |
| Shilard Fitz-Oesterlen | 7 | 3 |
| Villentretenmerth | 7 | 4 (hero framing, probably a false alarm) |

Nothing was changed on that basis.

## Tests

```bash
python run_tests.py                 # everything
python tests/test_layout.py         # a single suite
```

Every test imports `tests/_bootstrap.py` first. That puts the project root on
`sys.path`, makes it the working directory and switches pygame to headless
mode – so the suites run from the project root, from `tests/` or straight out
of an IDE.

| File | Size | Checks |
|---|---|---|
| `test_rules.py` | 63 | Scoring, weather, bond, morale, horn, agile, deck building |
| `test_game.py` | 71 | Spy, medic, decoy, scorch, muster, rounds |
| `test_config.py` | 44 | Settings round trip, atomic writes, command line merge |
| `test_i18n.py` | 201 | Both languages complete, proper umlauts, card names |
| `test_source.py` | 28 | English comments and docstrings, README markdown |
| `test_assets.py` | 13 | Every card image, leader artwork and the icon |
| `test_layout.py` | 552 | Overlaps and overflow across 8 resolutions |
| `test_interaction.py` | 58 | Turn handover, animation order, medic, agile, intro |
| `test_artwork.py` | 51 | Rows in `cards.json` match the card pictures |
| `test_carddata.py` | 660 | Structural sanity of `cards.json` |
| `test_regression.py` | 75 | Every reported bug, so none of them return |
| `test_playthrough.py` | 20 games | Full matches headless, all factions and resolutions |

`test_source.py` is the guard rail for this project's language policy: German
text may only live in `gwint_i18n.py` and `cards.json`. Comments, docstrings
and the README have to stay English. It also checks the README's markdown,
because GitHub is stricter than a local preview: doubly encoded characters,
unpaired code fences, ragged tables and an odd number of asterisks in a table
cell all render wrong there while an editor still shows something plausible.

`test_artwork.py` is the guard rail for the card data – see the section above.
It skips cleanly when numpy or the generated images are missing, so a fresh
checkout still runs.

`test_regression.py` is the safety net for bugs that were actually reported –
muster pulling its copies, no cards drawn between rounds, the Northern Realms
bonus, arrow key target selection, heroes excluded from revival.

## Assets

The finished card images are part of the repository – roughly 700 files and
about 100 MB, so a fresh checkout is playable without any build step.

The two ZIP archives they come from are *not* committed: at about 224 MB each
they exceed GitHub's 100 MB limit for a single file. Keep them in
`assets_src/` (listed in `.gitignore`) if you want to regenerate anything.
`tools/build_assets.py` reads them from there and writes:

```
cards/de/small/013.png   86×130     cards/en/small/013.png
cards/de/large/013.png  300×450     cards/en/large/013.png
```

`tools/make_icon.py` adds the window icon and the launcher tiles, all of them
next to each other under `cards/tiles/`:

```
cards/tiles/icon.png   256×256      cards/tiles/icon_64.png  64×64
cards/tiles/de/north.png  150×225   (one per faction and language)
```

The faction tiles are pre-rendered on purpose. tkinter can only scale images
by whole-number factors, which made the leader cards look blocky, so pygame's
smooth scaler does the work and the launcher merely displays the result.

`tools/build_assets.py --force` rebuilds every card; without the flag it skips
what already exists.

Naming inside the archives: `gwint_013_north_...png` (German) and
`gwint_en_013_north_...png` (English). The three digit number is the `id` from
`cards.json` and is identical in both languages.

## Multiplayer

**Not implemented.** The game is single player only: one human against the
built-in AI, on one machine. What follows is the result of an audit of how far
the current architecture would carry a multiplayer mode, so the question does
not have to be researched again.

### What the architecture already gets right

| Finding | Evidence |
|---|---|
| **A single choke point for moves** | `game.play()` is called from exactly one place (`Gwint.py`, inside `start_move().land()`). Every move would pass through one function. |
| **The rules are already server ready** | `gwint_rules.py` and `gwint_game.py` import no pygame. A server could run them unchanged – no porting, no duplicated logic. |
| **Randomness is injectable** | `Game(rng=...)` and `build_deck(rng=...)` already take a seeded generator; the tests rely on it. Deterministic replay on two machines is close to free. |
| **Tiny payloads** | One move is roughly 60 bytes (card plus up to three targets), a full player view about 120 bytes. Bandwidth is a non-issue. |
| **Headless, deterministic tests exist** | A "two clients, same seed, states must match" desync test is cheap to add on top of the current suite. |

### What would block it

| Obstacle | Detail |
|---|---|
| **`card.id` is not unique** | A 41 card deck reuses 9 ids (3x Crinfrid Reavers, 3x `Poor F***ing Infantry`, …). Over the wire "I play card 022" is ambiguous, and decoy or medic targets need to name one *specific* card. Cards would need per-instance handles. |
| **The client knows everything** | `ai.hand` and `ai.deck` live in the client. Harmless against the local AI, open cheating against a stranger. Needs server-authoritative state plus per-player filtered views. |
| **A fixed perspective** | Roughly 35 references to `self.user`, 24 to `self.ai` and 12 to `user_turn` encode "I am at the bottom, the opponent is at the top". Mechanical but wide rename to "me / them". |
| **One blocking call** | `pygame.time.delay(1500)` in `finish_round()` freezes the loop, which in a networked build would also stall receiving. Round transitions must become event driven. |
| **Animations assume local authority** | `commit(callback, delay)` lets the *client* decide when a move takes effect. With a server that decision moves away. Animations would have to become pure decoration reacting to server events instead of triggering them. This is the least obvious and most underestimated piece of work. |

### Effort estimate

| Variant | Effort | Result |
|---|---|---|
| **A – Hot seat** | 1–2 days | Two humans, one machine, hand-over screen. No networking. |
| **B – LAN / direct connection** | 10–14 days | Two machines, one hosts. Fully playable against friends. |
| **C – Internet with matchmaking** | +25–40 days | Dedicated server, accounts, ranking, cheat resistant. |

Breakdown for variant B:

| Work package | Days |
|---|---|
| Per-instance card handles | 1–1.5 |
| Perspective refactor (me / them instead of user / ai) | 1–1.5 |
| Move protocol and serialisation | 1 |
| Server loop (host runs `Game`) | 1.5–2 |
| Client: send intent, apply authoritative events | 2 |
| Remove blocking calls, event driven round changes | 0.5 |
| Lobby (address, faction, ready) | 1 |
| Disconnect, timeout, reconnect | 1–2 |
| Tests (two clients in one process, desync test) | 1–2 |

**Recommended path.** Variant B is the sweet spot – two weeks for a game that
works against friends is unusually little, and it is only possible because the
rules are separated from the presentation. Variant C is mostly infrastructure
(accounts, hosting, cheat protection, operations) rather than game.

Doing variant A first is not wasted work: hot seat forces the perspective
refactor and exposes every place that assumes "I am always at the bottom",
without any networking involved.

## Known limitations

- **No multiplayer.** Single player against the AI only – see the section
  above for what an implementation would cost.
- **Rows are verified, strengths and abilities are not.** Every row in
  `cards.json` was read off the artwork (see *Verifying the data against the
  artwork*). Strength values and abilities still rest on reconstruction; the
  four suspicious strengths listed there are worth a manual check.
- **Leader cards** are not playable. Foltest, Emhyr, Francesca and Eredin only
  serve as the launcher artwork. The monster entry `113` even points at leader
  art, which is why its row symbol is unreadable.
- **The Scoia'tael have no siege units.** That is what the artwork shows, and
  the game handles it – the row simply stays empty for them.
- Deck building rules (at least 22 units, at most 10 special cards) are not
  enforced – `build_deck()` takes every faction card plus 6 random neutrals.
- The AI only evaluates the current round and does not plan card advantage
  across several rounds. For agile cards it simply avoids a row under weather.
- Faction bonuses other than the Northern Realms draw (for example Nilfgaard
  winning draws) are not implemented.

