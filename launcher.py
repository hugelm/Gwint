"""Launcher: pick name, faction and language before starting a game.

The faction picker shows each faction's leader card so you can see what you
are choosing instead of reading a drop-down list. Settings are stored through
gwint_config and handed to the game as command line arguments.
"""
import os
import subprocess
import sys
import tkinter
from tkinter import font as tkfont

from gwint_config import Settings
from gwint_i18n import LANGUAGES, Translator
from gwint_rules import load_card_pool

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BG = '#16130f'
PANEL = '#241f18'
PANEL_HOT = '#332b20'
FG = '#e2d4b4'
MUTED = '#9c8f79'
ACCENT = '#deb25c'
ACCENT_DIM = '#8a6f3c'
DANGER = '#b23a2e'

# Leader card of each faction, used as the tile artwork
FACTION_ART = {
    'north': '002',        # Foltest
    'nilfgaard': '036',    # Emhyr var Emreis
    'scoiatael': '072',    # Francesca Findabair
    'monster': '113',      # Eredin
}

# Tiles keep the 2:3 card ratio, every tile is exactly this size
TILE_W, TILE_H = 150, 225
TILE_PAD = 10
LABEL_H = 34

FACTION_ORDER = ['north', 'nilfgaard', 'scoiatael', 'monster']


def available_factions():
    try:
        pool = load_card_pool()
        found = {f for f in pool if f != 'neutral'}
    except (OSError, ValueError, KeyError):
        return ['north']

    ordered = [f for f in FACTION_ORDER if f in found]
    ordered += sorted(found - set(ordered))
    return ordered or ['north']


def assets_ready(language):
    return os.path.isdir(os.path.join(BASE_DIR, 'cards', language, 'small'))


class Launcher(object):
    def __init__(self):
        self.settings = Settings.load()
        self.tr = Translator(self.settings.language)
        self.factions = available_factions()
        self.selected = (self.settings.faction if self.settings.faction in self.factions
                         else self.factions[0])
        self.images = {}
        self.tiles = {}
        self.music_started = False

        self.root = tkinter.Tk()
        self.root.configure(bg=BG)
        self.root.resizable(False, False)
        self._set_icon()

        self.title_font = tkfont.Font(family='Georgia', size=36, weight='bold')
        self.label_font = tkfont.Font(family='Georgia', size=12)
        self.name_font = tkfont.Font(family='Georgia', size=15)
        self.tile_font = tkfont.Font(family='Georgia', size=11, weight='bold')
        self.small_font = tkfont.Font(family='Georgia', size=9)
        self.button_font = tkfont.Font(family='Georgia', size=16, weight='bold')

        self._build()
        self.refresh()
        self._start_music()

    # --- setup -------------------------------------------------------------
    def _set_icon(self):
        for name in ('icon_64.png', 'icon.png'):
            path = os.path.join(BASE_DIR, 'cards', 'tiles', name)
            if not os.path.exists(path):
                continue
            try:
                self.icon = tkinter.PhotoImage(file=path)
                self.root.iconphoto(True, self.icon)
                return
            except tkinter.TclError:
                continue

    def _start_music(self):
        """Play the menu theme, if pygame and the file are available."""
        path = os.path.join(BASE_DIR, 'music', 'start_soundtrack.mp3')
        if not os.path.exists(path):
            return
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(0.2)
            pygame.mixer.music.play(-1)
            self.music_started = True
        except Exception:
            # Audio is a nicety, never let it break the launcher
            self.music_started = False

    def _stop_music(self):
        if not self.music_started:
            return
        try:
            import pygame
            pygame.mixer.music.fadeout(400)
        except Exception:
            pass

    def _build(self):
        root = self.root

        self.title = tkinter.Label(root, font=self.title_font, bg=BG, fg=ACCENT)
        self.title.pack(pady=(20, 2))

        self.subtitle = tkinter.Label(root, font=self.label_font, bg=BG, fg=MUTED)
        self.subtitle.pack(pady=(0, 16))

        name_row = tkinter.Frame(root, bg=BG)
        name_row.pack(pady=(0, 16))
        self.label_name = tkinter.Label(name_row, font=self.label_font, bg=BG, fg=FG)
        self.label_name.pack(side=tkinter.LEFT, padx=(0, 10))
        self.entry_name = tkinter.Entry(name_row, font=self.name_font, width=22,
                                        justify=tkinter.CENTER, bg=PANEL, fg=FG,
                                        insertbackground=ACCENT,
                                        relief=tkinter.FLAT,
                                        highlightthickness=1,
                                        highlightbackground=ACCENT_DIM,
                                        highlightcolor=ACCENT)
        self.entry_name.pack(side=tkinter.LEFT, ipady=6)
        self.entry_name.insert(0, self.settings.name)
        self.entry_name.bind('<Return>', lambda event: self.start())

        self.tile_row = tkinter.Frame(root, bg=BG)
        self.tile_row.pack(pady=(0, 14), padx=24)
        for code in self.factions:
            tile = self._build_tile(self.tile_row, code)
            tile['frame'].pack(side=tkinter.LEFT, padx=8)
            self.tiles[code] = tile

        lang_row = tkinter.Frame(root, bg=BG)
        lang_row.pack(pady=(0, 12))
        self.label_lang = tkinter.Label(lang_row, font=self.label_font, bg=BG, fg=FG)
        self.label_lang.pack(side=tkinter.LEFT, padx=(0, 10))

        self.lang_var = tkinter.StringVar(value=self.settings.language)
        self.lang_buttons = {}
        for code in LANGUAGES:
            btn = tkinter.Label(lang_row, text=code.upper(), font=self.label_font,
                                bg=PANEL, fg=FG, width=5, pady=4, cursor='hand2')
            btn.pack(side=tkinter.LEFT, padx=3)
            btn.bind('<Button-1>', lambda e, c=code: self.set_language(c))
            self.lang_buttons[code] = btn

        self.button_start = tkinter.Label(root, font=self.button_font, bg=ACCENT_DIM,
                                          fg=BG, pady=11, padx=48, cursor='hand2')
        self.button_start.pack(pady=(4, 10))
        self.button_start.bind('<Button-1>', lambda e: self.start())
        self.button_start.bind('<Enter>',
                               lambda e: self.button_start.config(bg=ACCENT))
        self.button_start.bind('<Leave>',
                               lambda e: self.button_start.config(bg=ACCENT_DIM))

        self.warning = tkinter.Label(root, font=self.small_font, bg=BG, fg=DANGER,
                                     wraplength=640)
        self.warning.pack(pady=(0, 14))

    def _build_tile(self, parent, code):
        """One clickable faction tile. Every tile has exactly the same size."""
        frame = tkinter.Frame(parent, bg=PANEL, highlightthickness=2,
                              highlightbackground=PANEL, cursor='hand2',
                              width=TILE_W + 2 * TILE_PAD,
                              height=TILE_H + LABEL_H + 2 * TILE_PAD)
        # Fixed geometry, so a long faction name cannot stretch the tile
        frame.pack_propagate(False)

        canvas = tkinter.Canvas(frame, width=TILE_W, height=TILE_H, bg=PANEL,
                                highlightthickness=0, bd=0)
        canvas.pack(pady=(TILE_PAD, 4))

        image = self._load_art(code)
        if image is not None:
            canvas.create_image(TILE_W // 2, TILE_H // 2, image=image)
        else:
            canvas.create_text(TILE_W // 2, TILE_H // 2, text='?', fill=MUTED,
                               font=self.title_font)

        label = tkinter.Label(frame, font=self.tile_font, bg=PANEL, fg=FG,
                              wraplength=TILE_W + 8, justify=tkinter.CENTER)
        label.pack(fill=tkinter.X, expand=True)

        for widget in (frame, canvas, label):
            widget.bind('<Button-1>', lambda e, c=code: self.select(c))
            widget.bind('<Enter>', lambda e, c=code: self.hover(c, True))
            widget.bind('<Leave>', lambda e, c=code: self.hover(c, False))

        return {'frame': frame, 'canvas': canvas, 'label': label}

    def _load_art(self, code):
        """Load the pre-rendered faction tile for the active language.

        make_icon.py writes these at exactly TILE_W x TILE_H using pygame's
        smooth scaler. tkinter can only scale by whole-number factors, which
        looked blocky, so it just displays the finished image here.
        """
        key = (code, self.tr.language)
        for language in (self.tr.language, 'de', 'en'):
            path = os.path.join(BASE_DIR, 'cards', 'tiles', language,
                                f'{code}.png')
            if not os.path.exists(path):
                continue
            try:
                image = tkinter.PhotoImage(file=path)
                self.images[key] = image      # keep a reference alive
                return image
            except tkinter.TclError:
                continue

        # Fall back to the raw card if the tiles were never generated
        card_id = FACTION_ART.get(code)
        if not card_id:
            return None
        for language in (self.tr.language, 'de', 'en'):
            raw_path = os.path.join(BASE_DIR, 'cards', language, 'large',
                                    f'{card_id}.png')
            if not os.path.exists(raw_path):
                continue
            try:
                raw = tkinter.PhotoImage(file=raw_path)
            except tkinter.TclError:
                continue
            shrink = max(1, round(raw.width() / TILE_W))
            image = raw.subsample(shrink, shrink)
            self.images[key] = image
            return image
        return None


    # --- behaviour ---------------------------------------------------------
    def select(self, code):
        self.selected = code
        self.refresh_tiles()

    def hover(self, code, entering):
        tile = self.tiles.get(code)
        if not tile or code == self.selected:
            return
        color = PANEL_HOT if entering else PANEL
        border = ACCENT_DIM if entering else PANEL
        tile['frame'].config(bg=color, highlightbackground=border)
        tile['canvas'].config(bg=color)
        tile['label'].config(bg=color)

    def set_language(self, code):
        self.lang_var.set(code)
        self.tr.language = code
        self.refresh()

    def refresh_tiles(self):
        for code, tile in self.tiles.items():
            chosen = code == self.selected
            bg = PANEL_HOT if chosen else PANEL
            tile['frame'].config(bg=bg,
                                 highlightbackground=ACCENT if chosen else PANEL)
            tile['canvas'].config(bg=bg)
            tile['label'].config(bg=bg, fg=ACCENT if chosen else FG,
                                 text=self.tr.faction(code))

            # The artwork carries the card name, so it follows the language
            image = self._load_art(code)
            tile['canvas'].delete('all')
            if image is not None:
                tile['canvas'].create_image(TILE_W // 2, TILE_H // 2, image=image)
            else:
                tile['canvas'].create_text(TILE_W // 2, TILE_H // 2, text='?',
                                           fill=MUTED, font=self.title_font)

    def refresh(self):
        tr = self.tr
        self.root.title(tr('game_title'))
        self.title.config(text=tr('game_title'))
        self.subtitle.config(text=tr('launcher_choose'))
        self.label_name.config(text=tr('launcher_name'))
        self.label_lang.config(text=tr('launcher_lang'))
        self.button_start.config(text=tr('launcher_start'))

        for code, btn in self.lang_buttons.items():
            chosen = code == self.lang_var.get()
            btn.config(bg=ACCENT_DIM if chosen else PANEL,
                       fg=BG if chosen else FG)

        self.refresh_tiles()
        self.warning.config(
            text='' if assets_ready(tr.language) else tr('assets_missing'))

    def current_settings(self):
        self.settings.name = self.entry_name.get().strip() or self.tr('player')
        self.settings.faction = self.selected
        self.settings.language = self.lang_var.get()
        return self.settings

    def start(self):
        if not assets_ready(self.tr.language):
            return

        settings = self.current_settings()
        settings.save()

        self._stop_music()
        self.root.destroy()

        subprocess.run([sys.executable, os.path.join(BASE_DIR, 'Gwint.py')]
                       + settings.to_argv(), cwd=BASE_DIR)

    def run(self):
        self.root.update_idletasks()
        width = self.root.winfo_reqwidth()
        height = self.root.winfo_reqheight()
        x = (self.root.winfo_screenwidth() - width) // 2
        y = max(0, (self.root.winfo_screenheight() - height) // 3)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        # Cursor at the end, nothing selected: typing adds to the name instead
        # of replacing it, which is friendlier when the name is already right
        self.entry_name.focus_set()
        self.entry_name.icursor(tkinter.END)
        self.root.mainloop()


if __name__ == '__main__':
    Launcher().run()

