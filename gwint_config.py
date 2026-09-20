"""Settings handling.

Replaces the old game_data.txt hand-off. Two mechanisms, clearly separated:

* **Persistence** - a JSON file in the location the operating system intends
  for application settings (``%APPDATA%`` on Windows, ``$XDG_CONFIG_HOME`` or
  ``~/.config`` on Linux, ``~/Library/Application Support`` on macOS).
  Nothing is written into the project folder any more.

* **Hand-off** - the launcher starts the game with command line arguments.
  That is explicit, race free and works even when two instances run at once.

Command line arguments always win over the stored file.
"""
import argparse
import json
import os
import sys

APP_NAME = 'Gwent'
FILE_NAME = 'settings.json'

DEFAULTS = {
    'name': 'Geralt',
    'faction': 'north',
    'language': 'de',
    'fullscreen': False,
    'music': True,
    'intro': True,
}

VALID_LANGUAGES = ('de', 'en')

# Names that used to be the default. A stored value matching one of these was
# never chosen by the player, so it is replaced by the current default.
LEGACY_DEFAULT_NAMES = ('Spieler', 'Player', '')


def config_dir():
    """Directory the current OS designates for application settings."""
    if sys.platform.startswith('win'):
        base = os.environ.get('APPDATA') or os.path.expanduser('~')
    elif sys.platform == 'darwin':
        base = os.path.expanduser('~/Library/Application Support')
    else:
        base = os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config')
    return os.path.join(base, APP_NAME)


def config_path():
    return os.path.join(config_dir(), FILE_NAME)


class Settings(object):
    """Typed access to the stored settings."""

    def __init__(self, **values):
        merged = dict(DEFAULTS)
        merged.update({k: v for k, v in values.items() if v is not None})
        self.name = str(merged['name'])
        self.faction = str(merged['faction'])
        self.language = (merged['language'] if merged['language'] in VALID_LANGUAGES
                         else DEFAULTS['language'])
        self.fullscreen = bool(merged['fullscreen'])
        self.music = bool(merged['music'])
        self.intro = bool(merged['intro'])

    def as_dict(self):
        return {
            'name': self.name,
            'faction': self.faction,
            'language': self.language,
            'fullscreen': self.fullscreen,
            'music': self.music,
            'intro': self.intro,
        }

    # --- persistence -------------------------------------------------------
    @classmethod
    def load(cls, path=None):
        """Read the settings file. Missing or broken files fall back to defaults."""
        path = path or config_path()
        try:
            with open(path, encoding='utf-8') as handle:
                stored = json.load(handle)
            if not isinstance(stored, dict):
                stored = {}
        except (OSError, ValueError):
            stored = {}

        values = {k: stored.get(k) for k in DEFAULTS}

        # Carry an old default name over to the current one
        if isinstance(values.get('name'), str):
            if values['name'].strip() in LEGACY_DEFAULT_NAMES:
                values['name'] = None

        return cls(**values)

    def save(self, path=None):
        """Write the settings atomically so a crash cannot corrupt the file."""
        path = path or config_path()
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            temp = path + '.tmp'
            with open(temp, 'w', encoding='utf-8') as handle:
                json.dump(self.as_dict(), handle, indent=2, ensure_ascii=False)
            os.replace(temp, path)
            return True
        except OSError:
            return False

    # --- command line ------------------------------------------------------
    def to_argv(self):
        """Arguments the launcher passes on to the game."""
        argv = ['--name', self.name,
                '--faction', self.faction,
                '--language', self.language]
        if self.fullscreen:
            argv.append('--fullscreen')
        if not self.music:
            argv.append('--no-music')
        if not self.intro:
            argv.append('--no-intro')
        return argv

    def __repr__(self):
        return f'<Settings {self.as_dict()}>'


def build_parser():
    parser = argparse.ArgumentParser(
        prog='Gwint.py', description='Gwent - the card game from The Witcher 3')
    parser.add_argument('--name', help='player name')
    parser.add_argument('--faction', help='starting faction')
    parser.add_argument('--language', choices=VALID_LANGUAGES, help='interface language')
    parser.add_argument('--fullscreen', action='store_true', default=None,
                        help='start in fullscreen')
    parser.add_argument('--no-music', dest='music', action='store_false',
                        default=None, help='start without music')
    parser.add_argument('--no-intro', dest='intro', action='store_false',
                        default=None, help='skip the title sequence')
    return parser


def from_command_line(argv=None):
    """Stored settings, overridden by whatever was passed on the command line."""
    args = build_parser().parse_args(argv)
    settings = Settings.load()

    for key in ('name', 'faction', 'language', 'fullscreen', 'music', 'intro'):
        value = getattr(args, key, None)
        if value is not None:
            setattr(settings, key, value)

    # Re-validate, the command line could carry nonsense
    return Settings(**settings.as_dict())

