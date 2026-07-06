#!/usr/bin/env python3
"""Places generator — one distinctive, hand-flavored landmark per region.

Unlike the uniform gate/wilds/crossroads templates, each region gets a unique
named landmark map with its own tileset feel, worldbuilding lore signs, a keeper
NPC (branching dialog), a small reward, and an exploration side quest. Landmarks
hang off each region's Crossroads via a free wall door.

All content is ORIGINAL. Idempotent (upsert by id / skip-if-present).
Run after generate_league.py (needs the Crossroads maps). Then run check_chain.
Usage: python3 tools/generators/generate_places.py
"""
from __future__ import annotations

import json
import os

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA = os.path.join(ROOT, "data")

# region -> landmark design (all original worldbuilding)
LANDMARKS = {
    "verdantia": {
        "name": "Verdant Glade", "bgm": "town",
        "ground": "ground", "accent": "tall_grass",
        "keeper": "Elder Root",
        "lore": [
            "Verdant Glade — where the first trainer and the first creature are said to have shared a meal.",
            "The moss here remembers footsteps. Walk gently.",
            "They say a bond made in this glade never fully breaks."],
        "keeper_lines": [
            "Elder Root: Ah, a young trainer. This glade is the oldest promise in the world.",
            "Elder Root: Long before badges and Leagues, someone knelt here and simply... trusted.",
            "Elder Root: Carry that with you. It matters more than any crest."],
    },
    "aquilon": {
        "name": "Frostwatch Lighthouse", "bgm": "ridge",
        "ground": "stone", "accent": "water",
        "keeper": "Keeper Halden",
        "lore": [
            "Frostwatch Lighthouse — its beam has guided ships since before Aquilon had a name.",
            "The light is tended not by oil, but by a creature that has never once slept.",
            "Sailors leave a single coin on the sill. Nobody remembers why; everybody still does."],
        "keeper_lines": [
            "Halden: The beam never dims, and neither does the little one who keeps it lit.",
            "Halden: Loyalty like that isn't trained. It's earned, then returned.",
            "Halden: You have the look of someone the north will remember. Mind the cold."],
    },
    "cindral": {
        "name": "Ashfall Caldera", "bgm": "ridge",
        "ground": "stone", "accent": "lava",
        "keeper": "Emberwarden Sol",
        "lore": [
            "Ashfall Caldera — the mountain's heartbeat, felt in the soles of your feet.",
            "Cinders here fall upward on the hottest nights. Old-timers call it the mountain breathing.",
            "Cindral was born from this fire. So were half its creatures."],
        "keeper_lines": [
            "Sol: Feel that? The mountain's pulse. Steady. Patient. Older than every League.",
            "Sol: Fire doesn't rage here. It endures. There's a lesson in that for a trainer.",
            "Sol: Take this, and let it remind you: heat kept, not spent, is what wins the long road."],
    },
    "solane": {
        "name": "Mirage Oasis", "bgm": "route",
        "ground": "sand", "accent": "water",
        "keeper": "Wanderer Sima",
        "lore": [
            "Mirage Oasis — half the travelers who reach it swear it wasn't here yesterday.",
            "The water is real. The second oasis you see beside it is not. Choose carefully.",
            "In Solane, thirst teaches faster than any gym."],
        "keeper_lines": [
            "Sima: You found the real water. Good — most chase the mirage until the dunes keep them.",
            "Sima: Out here, the creatures that survive aren't the strongest. They're the surest.",
            "Sima: Drink. Rest. Then walk like you know which shadow is yours."],
    },
    "umbra": {
        "name": "Duskbell Grove", "bgm": "route",
        "ground": "ground", "accent": "shadow",
        "keeper": "Nightwarden Vesper",
        "lore": [
            "Duskbell Grove — the only place where day and night are said to hold a conversation.",
            "The bells here ring once at dusk, with no hand to move them.",
            "Umbra's creatures gather to listen. So, if you're wise, will you."],
        "keeper_lines": [
            "Vesper: Stay for the dusk bell. It rings for everyone, once, whether they listen or not.",
            "Vesper: The Hollow Order came through here, you know. They didn't stay for the bell.",
            "Vesper: That's their whole tragedy, really. Take this, and stay a moment longer than they did."],
    },
    "ferrock": {
        "name": "The Old Foundry", "bgm": "town",
        "ground": "floor", "accent": "iron",
        "keeper": "Foreman Dross",
        "lore": [
            "The Old Foundry — cold now, but the creatures that worked its bellows never left.",
            "Every anvil in Ferrock was struck first here. You can hear the echo if you're still.",
            "Iron remembers every blow. So, the foundry-keepers say, does a creature."],
        "keeper_lines": [
            "Dross: This foundry built Ferrock, hammer by hammer, with creatures who chose to stay.",
            "Dross: Partnership, not ownership. The ones who forgot that always left with less.",
            "Dross: Here. Forged it myself. Strong things are simple things, kept."],
    },
    "brume": {
        "name": "The Sunken Chapel", "bgm": "route",
        "ground": "stone", "accent": "water",
        "keeper": "Fenpriest Maren",
        "lore": [
            "The Sunken Chapel — a whole town knelt here before the fen rose to keep it.",
            "The water never took the bell. It still tolls, muffled, under the reeds.",
            "In Brume, nothing is truly lost. It only goes quiet for a while."],
        "keeper_lines": [
            "Maren: The chapel drowned, but the creatures never abandoned it. Neither will I.",
            "Maren: Grief and mist look alike from a distance. Up close, both can be walked through.",
            "Maren: Bless you, traveler. Take this from the drowned altar. It wants to be useful again."],
    },
    "lumen": {
        "name": "Prism Cavern", "bgm": "ridge",
        "ground": "floor", "accent": "crystal",
        "keeper": "Lumar the Seer",
        "lore": [
            "Prism Cavern — every crystal holds a sliver of light the valley once saw.",
            "Look long enough and you'll see a memory that isn't yours. Don't look too long.",
            "Lumen's creatures are made of borrowed light. So, some say, are we all."],
        "keeper_lines": [
            "Lumar: Light has a memory here. Your reflection is a day the cavern kept for you.",
            "Lumar: I've watched a thousand trainers pass. The kind ones shine longer in the stone.",
            "Lumar: Go on. Leave a bright memory. And take this shard of one someone left before."],
    },
    "zephyra": {
        "name": "Skyreach Shrine", "bgm": "ridge",
        "ground": "stone", "accent": "cloud",
        "keeper": "Windspeaker Aquila",
        "lore": [
            "Skyreach Shrine — the highest floor a trainer can stand on and still be called grounded.",
            "Once a generation, they say, a sky-spirit alights here. Most never see it. All look up.",
            "Zephyra ends at the sky. Everything past that, you carry inside."],
        "keeper_lines": [
            "Aquila: You climbed all nine regions to reach this wind. Breathe it. You earned the height.",
            "Aquila: The old legend — a storm that wears a creature's shape — still visits this shrine.",
            "Aquila: Watch the sky when the steppe goes quiet. And take this. The wind gives to those who climb."],
    },
}

# reward item per landmark (all exist in items.json)
REWARDS = ["great_orb", "dusk_orb", "super_potion", "hyper_potion", "revive",
           "great_orb", "max_revive", "ether_shard", "master_orb"]


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(p, d):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
        f.write("\n")


def upsert(records, rec):
    for i, r in enumerate(records):
        if r.get("id") == rec["id"]:
            records[i] = rec
            return
    records.append(rec)


def landmark_map(rid, spec, reward_item):
    """An 11x9 themed room: keeper at the back, lore signs, a reward pickup."""
    g = spec["ground"]
    legend = {"#": "wall", ".": g, "D": "door", "H": "heal_pad", "~": spec["accent"]}
    # accent tiles must be walkable-or-not; map accent to a decorative walkable/blocked type
    accent_walkable = spec["accent"] in ("grass", "sand", "stone", "flower", "cloud")
    legend["~"] = spec["accent"] if accent_walkable else "wall"
    rows = [
        "###########",
        "#~~.....~~#",
        "#.........#",
        "#.........#",
        "D.........#",
        "#.........#",
        "#.........#",
        "#~~.....~~#",
        "#####D#####",
    ]
    objects = [
        {"type": "spawn", "id": "entrance", "x": 5, "y": 7},
        {"type": "spawn", "id": "from_crossroads", "x": 1, "y": 4},
        {"type": "door", "x": 5, "y": 8, "to_map": f"{rid}_crossroads", "to_spawn": "from_landmark"},
        {"type": "door", "x": 0, "y": 4, "to_map": f"{rid}_crossroads", "to_spawn": "from_landmark"},
        {"type": "npc", "x": 5, "y": 2, "npc_id": f"{rid}_keeper", "sprite": "npc_watcher",
         "dialog_id": f"lore_{rid}"},
        {"type": "sign", "x": 3, "y": 3, "text": spec["lore"][0]},
        {"type": "sign", "x": 7, "y": 3, "text": spec["lore"][1]},
        {"type": "sign", "x": 5, "y": 5, "text": spec["lore"][2]},
        {"type": "item", "x": 2, "y": 6, "item": reward_item, "flag": f"item_{rid}_landmark"},
    ]
    return {
        "$schema_version": 1, "id": f"{rid}_landmark", "display_name": spec["name"],
        "region": rid, "bgm": spec["bgm"], "tile_size": 32,
        "legend": legend, "rows": rows, "objects": objects,
    }


def lore_dialog(rid, spec, reward_item):
    """Keeper dialog: first visit gives lore + a reward and sets explored_<rid>."""
    return {
        "id": f"lore_{rid}",
        "nodes": [
            {
                "id": "revisit",
                "condition": {"kind": "flag", "flag": f"explored_{rid}"},
                "portrait": "keeper",
                "lines": [f"{spec['keeper']}: The {spec['name']} keeps its stories. Come back when you need one."],
                "next": "",
            },
            {
                "id": "first",
                "portrait": "keeper",
                "lines": spec["keeper_lines"],
                "actions": [
                    {"kind": "set_flag", "flag": f"explored_{rid}"},
                    {"kind": "give_item", "item": reward_item, "quantity": 1},
                    {"kind": "add_money", "amount": 300},
                ],
                "next": "",
            },
        ],
    }


def main():
    quests_doc = load(os.path.join(DATA, "quests", "quests.json"))
    lore_doc = {"$schema_version": 1,
                "description": "Region landmark keeper dialogs (worldbuilding + first-visit reward).",
                "dialogs": []}
    order = ["verdantia", "aquilon", "cindral", "solane", "umbra",
             "ferrock", "brume", "lumen", "zephyra"]

    for idx, rid in enumerate(order):
        spec = LANDMARKS[rid]
        reward = REWARDS[idx]
        save(os.path.join(DATA, "regions", "maps", f"{rid}_landmark.json"),
             landmark_map(rid, spec, reward))
        lore_doc["dialogs"].append(lore_dialog(rid, spec, reward))

        # exploration side quest
        upsert(quests_doc["quests"], {
            "id": f"wonder_{rid}", "display_name": f"Wonders of {rid.capitalize()}",
            "category": "side", "auto_start": False,
            "start_condition": {"kind": "flag", "flag": f"visited_{rid}"},
            "description": f"Seek out the {spec['name']} and hear what its keeper remembers.",
            "objectives": [{"id": "obj_explore", "text": f"Visit the {spec['name']} and speak with {spec['keeper']}.",
                            "condition": {"kind": "flag", "flag": f"explored_{rid}"}}],
            "rewards": [{"kind": "money", "amount": 400 + 150 * idx},
                        {"kind": "item", "item": "hyper_potion", "quantity": 1}],
            "on_complete_flag": f"wonder_{rid}_done",
        })

        # wire a Crossroads door -> landmark on a free wall tile (left col, row 1)
        cp = os.path.join(DATA, "regions", "maps", f"{rid}_crossroads.json")
        cross = load(cp)
        cross["rows"][1] = "D" + cross["rows"][1][1:]
        for obj in [
            {"type": "door", "x": 0, "y": 1, "to_map": f"{rid}_landmark", "to_spawn": "entrance"},
            {"type": "spawn", "id": "from_landmark", "x": 1, "y": 1},
        ]:
            if not any(o.get("type") == obj["type"] and o.get("x") == obj["x"] and o.get("y") == obj["y"]
                       for o in cross["objects"]):
                cross["objects"].append(obj)
        save(cp, cross)

        # register in manifest
        mp = os.path.join(DATA, "regions", f"region_{rid}.json")
        manifest = load(mp)
        if f"{rid}_landmark" not in manifest.get("maps", []):
            manifest.setdefault("maps", []).append(f"{rid}_landmark")
        save(mp, manifest)

    save(os.path.join(DATA, "dialogs", "regions_lore.json"), lore_doc)
    save(os.path.join(DATA, "quests", "quests.json"), quests_doc)
    print(f"Places: {len(order)} landmarks + lore dialogs + {len(order)} exploration quests.")


if __name__ == "__main__":
    main()
