"""
scripts/manage_seed.py
----------------------
Cross-platform helper script to load and save pre-populated databases and index.
"""

import os
import shutil
import sys

SEED_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "tests", "dummy_data")
)
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FILES = ["users.db", "corpus.db", "corpus.index"]


def load_seed():
    print("Loading pre-populated seed databases and index...")
    for f in FILES:
        src = os.path.join(SEED_DIR, f)
        dest = os.path.join(ROOT_DIR, f)
        if os.path.exists(src):
            if os.path.exists(dest):
                try:
                    os.remove(dest)
                except Exception as err:
                    print(f"Warning: Could not remove existing file {dest} ({err})")
            shutil.copy2(src, dest)
            print(f"Loaded {f} into active environment.")
        else:
            print(f"Warning: Seed file {src} not found.")
    print("Seed data successfully loaded!")


def save_seed():
    print("Saving current database state as seed data...")
    if not os.path.exists(SEED_DIR):
        os.makedirs(SEED_DIR, exist_ok=True)
    for f in FILES:
        src = os.path.join(ROOT_DIR, f)
        dest = os.path.join(SEED_DIR, f)
        if os.path.exists(src):
            if os.path.exists(dest):
                try:
                    os.remove(dest)
                except Exception as err:
                    print(f"Warning: Could not remove existing file {dest} ({err})")
            shutil.copy2(src, dest)
            print(f"Saved {f} to tests/dummy_data/.")
        else:
            print(f"Warning: Active file {src} not found.")
    print("Seed data successfully saved!")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("load", "save"):
        print("Usage: python scripts/manage_seed.py [load|save]")
        sys.exit(1)
    if sys.argv[1] == "load":
        load_seed()
    else:
        save_seed()
