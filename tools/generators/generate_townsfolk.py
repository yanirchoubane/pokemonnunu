#!/usr/bin/env python3
"""Townsfolk generator — mature, branching NPC conversations across every region.

Populates each region's Crossroads, gate town and landmark with weathered,
morally-textured inhabitants: indebted farmers, war-tired trainers, ex-Order
sympathizers, grieving keepers, pragmatic fixers. The register is adult and
serious (debt, loss, compromise, disillusion) — not childish — while staying
tasteful. All content original. Idempotent: prunes its own NPCs (npc_id prefix
"folk_") and overwrites data/dialogs/townsfolk.json before regenerating.

Run after generate_league.py + generate_places.py. Then run check_chain.
Usage: python3 tools/generators/generate_townsfolk.py
"""
from __future__ import annotations

import json
import os

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA = os.path.join(ROOT, "data")

# region -> (landmark, display, theme noun, the region's quiet trouble)
REGION = {
    "verdantia": ("Verdant Glade", "Verdantia", "meadows",
                  "The soil's thinner every year, and the young leave for the League and don't write."),
    "aquilon": ("Frostwatch Lighthouse", "Aquilon", "cold coast",
                "Three boats didn't come back this winter. The sea keeps its own ledger."),
    "cindral": ("Ashfall Caldera", "Cindral", "volcanic slopes",
                "The mountain gives work and takes lungs. Everyone here coughs by fifty."),
    "solane": ("Mirage Oasis", "Solane", "dunes",
               "Water's currency out here. The Order understood that better than we'd like."),
    "umbra": ("Duskbell Grove", "Umbra", "twilight woods",
              "People come to Umbra to disappear. Some of them wanted to."),
    "ferrock": ("The Old Foundry", "Ferrock", "iron hills",
                "The foundry closed and took the town's spine with it. We forge memories now."),
    "brume": ("The Sunken Chapel", "Brume", "fens",
              "Half of Brume is underwater and the other half is grieving it."),
    "lumen": ("Prism Cavern", "Lumen", "crystal vale",
              "The light shows you old days. Some folk go in and forget to come out."),
    "zephyra": ("Skyreach Shrine", "Zephyra", "sky steppes",
                "Up here you can see the whole road you walked. Most people can't stand to look."),
}

# Shared mature archetypes. {land}/{region}/{theme}/{trouble} are substituted.
# entry: (role, name, [lines], optional [ (choice_text, action_kind|None, key, value, reply) ])
ARCHES = [
    ("veteran", "Retired Elite {N}", [
        "I held an Elite seat once. Four hundred challengers, and I remember the faces of the ones who beat me.",
        "You don't retire from this. You just stop getting up when they knock you down. {trouble}"]),
    ("debtor", "Farmhand {N}", [
        "The Order 'lent' my family a season's grain and called back triple. Gray coats always do.",
        "I'm free of them now. Cost me the farm, but a debt paid in dirt is still paid."]),
    ("sympathizer", "Quiet {N}", [
        "I almost took the gray coat, you know. When you've lost enough, 'take before it's taken' sounds like wisdom.",
        "The defector talked me out of it. Verel. Ask for them at the northern gate if you haven't met yet."],
     [("Why didn't you join?", None, None, 0,
       "Quiet {N}: Because hollow's a one-way road. You don't come back with more. You come back with less."),
      ("Weakness, then.", "adjust_relationship", "quiet", -1,
       "Quiet {N}: ...Say that after you've buried something. Then we'll talk.")]),
    ("fixer", "Broker {N}", [
        "Orbs, salves, information — I move all three. In {region}, knowing a thing is worth more than owning it.",
        "Word is you're unpicking the Order's cell, region by region. That's worth a discount. And a warning."]),
    ("mourner", "Widow {N}", [
        "My partner trained the same team for twenty years. When they passed, the creatures wouldn't eat for a week.",
        "That's the part the Leagues don't put on the badges. Bonds cut both ways. {trouble}"]),
    ("cynic", "Old {N}", [
        "Nine crests, they'll tell you. As if a wall of medals ever fed anyone.",
        "Chase it if you must. Just don't mistake the applause for a life."],
     [("It's more than applause to me.", "adjust_relationship", "old", 1,
       "Old {N}: ...Good. Hold onto the more. It's the only part that lasts."),
      ("Spare me the sermon.", None, None, 0,
       "Old {N}: Suit yourself. The road's a patient teacher.")]),
    ("watch", "Roadwarden {N}", [
        "I patrol between the gyms. Since the Order moved north, the wilds have teeth after dark.",
        "If you're headed for the Lieutenant in Umbra — go rested. Mourn doesn't fight angry. He fights tired, and wins."]),
    ("scholar", "Field-scholar {N}", [
        "Two thousand species catalogued and the {theme} of {region} still hand me a new one every month.",
        "Ambition's fine. But the ones who last learn to be curious instead. It ages better."]),
]

REGION_SPECIFIC = {
    "cindral": ("emberwidow", "Furnace-widow Ost", [
        "Furnace-widow Ost: My husband fed the {land}'s fire for thirty years. It fed on him right back.",
        "Furnace-widow Ost: The Order came the week after the funeral. Vultures know a thin season."]),
    "umbra": ("greytongue", "Grey Marda", [
        "Marda: Mourn drank at my table once, before the coat. Gentle man. Lost a child, then a purpose.",
        "Marda: When you beat him — and you will — be quick about the mercy. He's suffered the slow kind enough."]),
    "zephyra": ("summitkeep", "Summit-warden Iren", [
        "Iren: Everyone who reaches this wind has left something behind to get here. What's yours?",
        "Iren: The Archon left everything behind. That's the difference between you and them. So far."]),
}

# placement: (map_suffix, [tiles]) per location kind
CROSS_TILES = [(4, 2), (11, 2), (4, 6), (11, 6), (6, 2), (9, 6)]
GATE_TILES = [(4, 4), (9, 5)]        # generated *_gate maps (12x7); (2,4) holds the gate sign
LAND_TILES = [(8, 3), (2, 5)]        # landmark maps (11x9)
GENERATED = ["cindral", "solane", "umbra", "ferrock", "brume", "lumen", "zephyra"]
SPRITE = {"veteran": "npc_watcher", "debtor": "npc_villager", "sympathizer": "npc_villager",
          "fixer": "npc_clerk", "mourner": "npc_villager", "cynic": "npc_villager",
          "watch": "npc_watcher", "scholar": "npc_villager", "emberwidow": "npc_villager",
          "greytongue": "npc_watcher", "summitkeep": "npc_watcher"}


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(p, d):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
        f.write("\n")


def sub(text, rid, n):
    land, region, theme, trouble = REGION[rid]
    return (text.replace("{land}", land).replace("{region}", region)
                .replace("{theme}", theme).replace("{trouble}", trouble).replace("{N}", n))


def build_dialog(did, rid, entry, n):
    role, name, lines = entry[0], sub(entry[1], rid, n), [sub(l, rid, n) for l in entry[2]]
    node = {"id": "start", "portrait": role, "lines": lines}
    nodes = [node]
    if len(entry) > 3 and entry[3]:
        choices = []
        for i, (text, kind, key, val, reply) in enumerate(entry[3]):
            actions = []
            if kind == "adjust_relationship":
                actions.append({"kind": "adjust_relationship", "npc": key, "delta": int(val)})
            elif kind == "set_var":
                actions.append({"kind": "set_var", "var": key, "value": val})
            rid_node = f"reply_{i}"
            nodes.append({"id": rid_node, "entry": False, "portrait": role,
                          "lines": [sub(reply, rid, n)], "next": ""})
            choices.append({"text": sub(text, rid, n), "actions": actions, "next": rid_node})
        node["choices"] = choices
    else:
        node["next"] = ""
    return {"id": did, "nodes": nodes}


def prune_folk(m):
    def is_folk(o):
        nid = str(o.get("npc_id", ""))
        return o.get("type") == "npc" and ("folk_" in nid)
    m["objects"] = [o for o in m["objects"] if not is_folk(o)]


def place(m, tiles, entries, rid, doc, kind):
    n = 0
    for (x, y), entry in zip(tiles, entries):
        idx = f"{kind}{n}"
        did = f"town_{rid}_{idx}"
        doc["dialogs"].append(build_dialog(did, rid, entry, str(n + 1)))
        m["objects"].append({"type": "npc", "x": x, "y": y,
                             "npc_id": f"folk_{rid}_{idx}",
                             "sprite": SPRITE.get(entry[0], "npc_villager"), "dialog_id": did})
        n += 1


def main():
    doc = {"$schema_version": 1,
           "description": "Mature townsfolk conversations across Crossroads, gates and landmarks.",
           "dialogs": []}
    order = list(REGION.keys())
    total = 0
    for r_i, rid in enumerate(order):
        # rotate the shared archetypes so regions don't all read identically
        picks = [ARCHES[(r_i + k) % len(ARCHES)] for k in range(len(CROSS_TILES))]
        # Crossroads mature NPCs
        cp = os.path.join(DATA, "regions", "maps", f"{rid}_crossroads.json")
        cross = load(cp); prune_folk(cross)
        place(cross, CROSS_TILES, picks, rid, doc, "x")
        save(cp, cross); total += len(CROSS_TILES)
        # Gate town (generated regions only): 2 more
        if rid in GENERATED:
            gp = os.path.join(DATA, "regions", "maps", f"{rid}_gate.json")
            gate = load(gp); prune_folk(gate)
            gpicks = [ARCHES[(r_i + 4 + k) % len(ARCHES)] for k in range(2)]
            place(gate, GATE_TILES, gpicks, rid, doc, "g")
            save(gp, gate); total += len(GATE_TILES)
        # Landmark: a region-specific voice if we wrote one, else an archetype
        lp = os.path.join(DATA, "regions", "maps", f"{rid}_landmark.json")
        land = load(lp); prune_folk(land)
        lentries = []
        if rid in REGION_SPECIFIC:
            lentries.append(REGION_SPECIFIC[rid])
        lentries.append(ARCHES[(r_i + 6) % len(ARCHES)])
        place(land, LAND_TILES[:len(lentries)], lentries, rid, doc, "l")
        save(lp, land); total += len(lentries)

    save(os.path.join(DATA, "dialogs", "townsfolk.json"), doc)
    print(f"Townsfolk: {len(doc['dialogs'])} mature NPC dialogs, {total} NPCs across "
          f"Crossroads / gates / landmarks.")


if __name__ == "__main__":
    main()
