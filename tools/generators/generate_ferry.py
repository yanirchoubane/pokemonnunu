#!/usr/bin/env python3
"""Ferry network — free travel between every region you have already visited.

Fulfils the original spec point "travel freely between unlocked regions": a
Harbormaster NPC stands in every region and offers passage to any region whose
`visited_<region>` flag is set (dialog choices are condition-gated; the engine
filters them at runtime). Return trips stay free; unvisited regions simply do
not appear, so sequential progression through the story ports is untouched.

All content original. Idempotent. Part of run_all.py (after story placements).
Usage: python3 tools/generators/generate_ferry.py
"""
from __future__ import annotations

import json
import os

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA = os.path.join(ROOT, "data")

# region -> (destination map, spawn, harbor map, npc tile)
NETWORK = {
    "verdantia": ("verdantia_town", "default", "verdantia_town", (12, 10)),
    "aquilon": ("aquilon_shore", "default", "aquilon_shore", (8, 6)),
    "cindral": ("cindral_gate", "port", "cindral_gate", (10, 4)),
    "solane": ("solane_gate", "port", "solane_gate", (10, 4)),
    "umbra": ("umbra_gate", "port", "umbra_gate", (10, 4)),
    "ferrock": ("ferrock_gate", "port", "ferrock_gate", (10, 4)),
    "brume": ("brume_gate", "port", "brume_gate", (10, 4)),
    "lumen": ("lumen_gate", "port", "lumen_gate", (10, 4)),
    "zephyra": ("zephyra_gate", "port", "zephyra_gate", (10, 4)),
}


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(p, d):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
        f.write("\n")


def main():
    # One shared dialog: each destination is a condition-gated choice.
    choices = []
    for rid, (dest_map, dest_spawn, _hm, _tile) in NETWORK.items():
        choices.append({
            "text": f"Sail to {rid.capitalize()}.",
            "condition": {"kind": "region_visited", "region": rid},
            "actions": [{"kind": "warp", "map": dest_map, "spawn": dest_spawn}],
            "next": "",
        })
    choices.append({"text": "Stay ashore.", "actions": [], "next": ""})
    dialog_doc = {
        "$schema_version": 1,
        "description": "Shared Harbormaster dialog: free travel between visited regions.",
        "dialogs": [{
            "id": "ferry_network",
            "nodes": [{
                "id": "start",
                "portrait": "harbormaster",
                "lines": [
                    "Harbormaster: The ferry answers to no League and no Order — only to the tide and the fare you've already paid in footsteps.",
                    "Harbormaster: I sail to any gate you've stood on. Where to?",
                ],
                "prompt": "Where to?",
                "choices": choices,
            }],
        }],
    }
    save(os.path.join(DATA, "dialogs", "ferry.json"), dialog_doc)

    placed = 0
    for rid, (_dm, _ds, harbor_map, (x, y)) in NETWORK.items():
        mp = os.path.join(DATA, "regions", "maps", f"{harbor_map}.json")
        m = load(mp)
        if not any(o.get("npc_id") == f"harbormaster_{rid}" for o in m["objects"]):
            m["objects"].append({"type": "npc", "x": x, "y": y,
                                 "npc_id": f"harbormaster_{rid}",
                                 "sprite": "npc_sailor", "dialog_id": "ferry_network"})
            save(mp, m)
            placed += 1
    print(f"Ferry network: shared travel dialog + {placed} Harbormasters placed "
          f"(9 total when idempotent).")


if __name__ == "__main__":
    main()
