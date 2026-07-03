#!/usr/bin/env python3
"""Canonical generator pipeline — runs every content generator in the ONE valid
order, then all verifiers. Use this instead of running generators by hand:
several of them rewrite files that earlier ones created (e.g. generate_league
replaces the summit halls that generate_regions writes; rewrite_trainer_voices
renames champions that generate_league creates), so order matters.

Usage: python3 tools/generators/run_all.py [--skip-verify]
"""
from __future__ import annotations

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))

PIPELINE = [
    # (script, why it must run at this point)
    ("tools/generators/generate_regions.py", "base region scaffolds (gates/wilds/summit halls)"),
    ("tools/generators/generate_expansion.py", "species/moves/route trainers/Hollow agents"),
    ("tools/generators/generate_league.py", "REPLACES summit halls with League corridors; gyms; elites; champions"),
    ("tools/generators/generate_bulk.py", "mass dex + Battle Courts (self-pruning)"),
    ("tools/generators/generate_extras.py", "items/abilities/moves/side quests"),
    ("tools/generators/generate_places.py", "landmarks + lore keepers + wonder quests"),
    ("tools/generators/generate_story_placements.py", "pins the story cast (Corin, Verel, Mourn, Archon) onto rewritten maps"),
    ("tools/generators/generate_rival_battles.py", "Corin fights (needs expansion species)"),
    ("tools/generators/generate_townsfolk.py", "mature townsfolk (prunes + re-places its NPCs)"),
    ("tools/generators/rewrite_trainer_voices.py", "MUST BE LAST trainer pass: names champions, voices bosses, syncs quest texts"),
    ("tools/generators/generate_signs.py", "signposts (prunes + re-places its signs)"),
]
VERIFY = [
    "tools/validators/validate_data.py",
    "tools/validators/check_chain.py",
    "tools/world_summary.py",
    "tests/test_reference.py",
]


def run(script: str) -> None:
    r = subprocess.run([sys.executable, os.path.join(ROOT, script)], cwd=ROOT)
    if r.returncode != 0:
        print(f"\n✗ {script} failed (exit {r.returncode}) — pipeline stopped.")
        sys.exit(r.returncode)


def main() -> None:
    for script, why in PIPELINE:
        print(f"\n=== {script}  ({why})")
        run(script)
    if "--skip-verify" not in sys.argv:
        for script in VERIFY:
            print(f"\n=== verify: {script}")
            run(script)
    print("\n✓ Pipeline complete: all generators applied in canonical order, all verifiers green.")


if __name__ == "__main__":
    main()
