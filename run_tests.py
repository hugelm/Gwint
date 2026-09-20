"""Runs every test suite:  python run_tests.py"""
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_DIR = os.path.join(BASE_DIR, 'tests')

# Fast, pure-logic suites first so a broken rule shows up immediately
ORDER = [
    'test_rules.py',
    'test_game.py',
    'test_config.py',
    'test_i18n.py',
    'test_source.py',
    'test_assets.py',
    'test_layout.py',
    'test_interaction.py',
    'test_playthrough.py',
]


def discover():
    found = sorted(f for f in os.listdir(TEST_DIR)
                   if f.startswith('test_') and f.endswith('.py'))
    ordered = [f for f in ORDER if f in found]
    return ordered + [f for f in found if f not in ordered]


def main():
    failed = []
    tests = discover()

    for name in tests:
        print(f'\n=== {name} ' + '=' * max(0, 56 - len(name)))
        result = subprocess.run([sys.executable, '-u', os.path.join(TEST_DIR, name)],
                                cwd=BASE_DIR)
        if result.returncode != 0:
            failed.append(name)

    print('\n' + '=' * 62)
    if failed:
        print('FAILED: ' + ', '.join(failed))
        return 1
    print(f'All {len(tests)} test files passed.')
    return 0


if __name__ == '__main__':
    sys.exit(main())

