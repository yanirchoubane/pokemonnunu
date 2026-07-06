#!/usr/bin/env python3
"""Signpost generator — directional + lore signs across the world.

Adds a directory signpost to every Crossroads (which gym lies which way, where the
League and landmark are), a milepost at each generated gate, and a weathered
warning sign in each wilds. Adult, grounded register. Idempotent: prunes signs it
previously added (marked with "gen": "sign") before re-adding.

Run after generate_league.py + generate_places.py. Then run check_chain.
Usage: python3 tools/generators/generate_signs.py
"""
from __future__ import annotations

import glob
import json
import os

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA = os.path.join(ROOT, "data")
TYPES = ["normal", "fire", "water", "grass", "electric", "earth", "wind", "mystic"]
GENERATED = ["cindral", "solane", "umbra", "ferrock", "brume", "lumen", "zephyra"]

TYPE_TITLES = {"normal": "Plainskeeper", "fire": "Ember Sage", "water": "Tidecaller",
               "grass": "Grovewarden", "electric": "Stormsmith", "earth": "Cairnbreaker",
               "wind": "Skydancer", "mystic": "Dreambinder"}

WILDS_WARN = {
    "cindral": "NOTICE: Vents open without warning past this marker. Since the gray coats came, travel armed and travel light.",
    "solane": "NOTICE: Water two days south. The Order priced the wells before we ran them off — pay nothing to a gray coat.",
    "umbra": "NOTICE: The grove keeps a Lieutenant now. Those with debts to the Order should turn back here.",
    "ferrock": "NOTICE: Foundry ruins ahead, structurally unsound. Two Order agents were last seen working these hills.",
    "brume": "NOTICE: The fen rises fast after rain. If the bell under the reeds tolls, you have already stayed too long.",
    "lumen": "NOTICE: Do not linger at the crystals. The last Order agent hides in the deep galleries. Bring light and leave.",
    "zephyra": "NOTICE: Beyond this marker, the Archon walks the steppe. What you decide up there, the whole sky will carry.",
}


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(p, d):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
        f.write("\n")


def prune_signs(m):
    m["objects"] = [o for o in m["objects"] if not (o.get("type") == "sign" and o.get("gen") == "sign")]


def add_sign(m, x, y, text):
    m["objects"].append({"type": "sign", "x": x, "y": y, "text": text, "gen": "sign"})


def main():
    maps = {}
    for f in glob.glob(os.path.join(DATA, "regions", "maps", "*.json")):
        m = load(f)
        maps[m["id"]] = (f, m)
    added = 0

    for rid in ["verdantia", "aquilon"] + GENERATED:
        # Crossroads directory sign (top gyms N, bottom gyms S, League E, landmark W)
        cid = f"{rid}_crossroads"
        if cid in maps:
            fp, m = maps[cid]
            prune_signs(m)
            top = ", ".join(f"{TYPE_TITLES[t]} ({t})" for t in TYPES[:4])
            bot = ", ".join(f"{TYPE_TITLES[t]} ({t})" for t in TYPES[4:])
            add_sign(m, 6, 5,
                     "CROSSROADS DIRECTORY. North halls: %s. South halls: %s. "
                     "East: the League — sealed until all eight badges are earned. West: the old road, and the landmark."
                     % (top, bot))
            add_sign(m, 8, 5,
                     "Eight leaders, one crest apiece. Beat them in any order. "
                     "The four Elites past the League gate do not wait in any order — they wait in a line.")
            save(fp, m); added += 2
        # Wilds warning (generated regions)
        wid = f"{rid}_wilds"
        if wid in maps and rid in WILDS_WARN:
            fp, m = maps[wid]
            prune_signs(m)
            add_sign(m, 4, 3, WILDS_WARN[rid])
            save(fp, m); added += 1
        # Gate milepost (generated regions)
        gid = f"{rid}_gate"
        if gid in maps:
            fp, m = maps[gid]
            prune_signs(m)
            add_sign(m, 5, 5,
                     "%s GATE. West: the port home — no toll, no questions. East: the wilds, then the Crossroads. "
                     "Rest while it's free to." % rid.capitalize())
            save(fp, m); added += 1

    print(f"Signs: added {added} directional/lore signposts across the world.")


if __name__ == "__main__":
    main()
