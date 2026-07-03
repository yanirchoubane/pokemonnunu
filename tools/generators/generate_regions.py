#!/usr/bin/env python3
"""Region generator — scaffolds complete, connected demo regions from specs.

Generates for each region spec: a manifest, three maps (gate town with heal/shop,
wilds with encounters and a scout trainer, summit hall with a boss champion),
an encounter table, two trainers, native creatures and a main quest — then wires
the inter-region port chain (previous hall -> gate -> wilds -> hall -> next gate).

All generated content is ORIGINAL (invented names, stats and dialogue). The tool
is idempotent: records are upserted by id, so re-running refreshes the output.
Users can add their own specs to REGIONS (or copy this file into their own tool)
to scaffold more regions, including packs under user_content/.

Usage: python3 tools/generators/generate_regions.py
"""
from __future__ import annotations

import json
import os

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA = os.path.join(ROOT, "data")

# ---------------------------------------------------------------------------
# Region specs (order 3..9). Levels scale with order; species are region natives.
# ---------------------------------------------------------------------------

REGIONS = [
    {
        "id": "cindral", "name": "Cindral", "order": 3, "theme": "volcanic slopes",
        "natives": [
            {"id": "cindermole", "name": "Cindermole", "types": ["fire", "earth"],
             "desc": "A burrower whose tunnels glow faintly at night.",
             "stats": [60, 66, 62, 55, 52, 48], "moves": ["scratch", "ember_burst", "stone_toss", "focus_charge"]},
            {"id": "ashvole", "name": "Ashvole", "types": ["earth"],
             "desc": "It bathes in warm ash to harden its pelt.",
             "stats": [55, 58, 70, 42, 55, 45], "moves": ["tackle", "stone_toss", "guard_up"]},
        ],
        "pool": ["emberpup", "pebblet"],
    },
    {
        "id": "solane", "name": "Solane", "order": 4, "theme": "sun-baked dunes",
        "natives": [
            {"id": "duneling", "name": "Duneling", "types": ["earth"],
             "desc": "It surfs the dunes on its flat, sand-polished belly.",
             "stats": [62, 64, 66, 50, 58, 55], "moves": ["tackle", "stone_toss", "quick_jab", "guard_up"]},
            {"id": "sunwisp", "name": "Sunwisp", "types": ["fire", "mystic"],
             "desc": "A mote of noon light that hums when storms approach.",
             "stats": [52, 45, 50, 78, 66, 68], "moves": ["ember_burst", "mind_ray", "focus_charge"]},
        ],
        "pool": ["zapmouse", "gustling"],
    },
    {
        "id": "umbra", "name": "Umbra", "order": 5, "theme": "twilight woods",
        "natives": [
            {"id": "gloomoth", "name": "Gloomoth", "types": ["mystic", "wind"],
             "desc": "Its wingbeats scatter sleep-inducing dust.",
             "stats": [58, 50, 54, 76, 70, 72], "moves": ["mind_ray", "gale_slash", "static_field"]},
            {"id": "thornrat", "name": "Thornrat", "types": ["grass"],
             "desc": "It naps inside bramble knots no predator dares enter.",
             "stats": [64, 70, 60, 48, 55, 66], "moves": ["scratch", "leaf_cut", "vine_wrap", "quick_jab"]},
        ],
        "pool": ["sproutkit", "psywisp"],
    },
    {
        "id": "ferrock", "name": "Ferrock", "order": 6, "theme": "iron hills",
        "natives": [
            {"id": "boltram", "name": "Boltram", "types": ["electric", "earth"],
             "desc": "Its horns arc with charge gathered from ore veins.",
             "stats": [70, 76, 68, 60, 58, 62], "moves": ["tackle", "spark_zap", "stone_toss", "focus_charge"]},
            {"id": "slagbeetle", "name": "Slagbeetle", "types": ["fire", "earth"],
             "desc": "It chews smelter slag and spits sparks.",
             "stats": [66, 68, 80, 55, 62, 40], "moves": ["tackle", "ember_burst", "stone_toss", "guard_up"]},
        ],
        "pool": ["pebblet", "zapmouse"],
    },
    {
        "id": "brume", "name": "Brume", "order": 7, "theme": "misty fens",
        "natives": [
            {"id": "fenling", "name": "Fenling", "types": ["water", "grass"],
             "desc": "It plants reeds along the banks it patrols.",
             "stats": [72, 60, 66, 70, 74, 58], "moves": ["aqua_dart", "leaf_cut", "vine_wrap", "guard_up"]},
            {"id": "murkfin", "name": "Murkfin", "types": ["water"],
             "desc": "Only its dorsal fin breaks the fog-laden water.",
             "stats": [68, 74, 62, 64, 60, 70], "moves": ["aqua_dart", "tide_crash", "quick_jab"]},
        ],
        "pool": ["aquafin", "mistcalf"],
    },
    {
        "id": "lumen", "name": "Lumen", "order": 8, "theme": "crystal vale",
        "natives": [
            {"id": "glimshard", "name": "Glimshard", "types": ["mystic"],
             "desc": "A living prism that stores the valley's stray light.",
             "stats": [60, 48, 64, 88, 78, 66], "moves": ["mind_ray", "static_field", "focus_charge", "guard_up"]},
            {"id": "prismole", "name": "Prismole", "types": ["earth", "mystic"],
             "desc": "Its claws cut crystal as easily as soil.",
             "stats": [74, 78, 76, 62, 66, 52], "moves": ["scratch", "stone_toss", "mind_ray", "guard_up"]},
        ],
        "pool": ["psywisp", "pebblet"],
    },
    {
        "id": "zephyra", "name": "Zephyra", "order": 9, "theme": "sky steppes",
        "natives": [
            {"id": "galehare", "name": "Galehare", "types": ["wind"],
             "desc": "It outruns the storm fronts it loves to race.",
             "stats": [70, 78, 62, 60, 62, 96], "moves": ["quick_jab", "gale_slash", "focus_charge"]},
            {"id": "stormkite", "name": "Stormkite", "types": ["wind", "electric"],
             "desc": "It rides thunderheads, trailing ribbons of charge.",
             "stats": [72, 66, 64, 84, 70, 88], "moves": ["gale_slash", "spark_zap", "static_field", "mind_ray"]},
        ],
        "pool": ["gustling", "mistelk"],
    },
]

SHOP_STOCK = ["capture_orb", "great_orb", "dusk_orb", "potion", "super_potion",
              "hyper_potion", "max_potion", "antidote", "burn_salve", "spark_charm",
              "revive", "max_revive"]


def band(order: int) -> tuple[int, int]:
    """Recommended level band for a region order (3 -> 14-24 ... 9 -> 50-60)."""
    lo = 6 * order - 4
    return lo, lo + 10


def load(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def upsert(records: list, rec: dict) -> None:
    for i, r in enumerate(records):
        if r.get("id") == rec["id"]:
            records[i] = rec
            return
    records.append(rec)


def creature_record(spec: dict, region_id: str, order: int) -> dict:
    hp, atk, dfn, spa, spd, spe = spec["stats"]
    learnset = [{"level": 1, "move": spec["moves"][0]}]
    lo, _ = band(order)
    for j, mid in enumerate(spec["moves"][1:], start=1):
        learnset.append({"level": max(1, lo - 8 + j * 6), "move": mid})
    return {
        "id": spec["id"], "display_name": spec["name"], "description": spec["desc"],
        "generation": "demo_g1", "origin_region": region_id, "types": spec["types"],
        "base_stats": {"hp": hp, "attack": atk, "defense": dfn,
                       "sp_attack": spa, "sp_defense": spd, "speed": spe},
        "ev_yield": {"hp": 1}, "exp_curve": "medium_fast", "gender_ratio": 0.5,
        "abilities": ["thick_hide" if "earth" in spec["types"] else
                      "swift_foot" if "wind" in spec["types"] else
                      "keen_mind" if "mystic" in spec["types"] else "thick_hide"],
        "capture_rate": 90, "rarity": "common", "breeding_groups": ["field"],
        "learnset": learnset, "evolves_to": [], "forms": [],
    }


def trainer_moves(creature: dict, level: int) -> list:
    moves = [e["move"] for e in creature["learnset"] if e["level"] <= level]
    return moves[-4:] if moves else [creature["learnset"][0]["move"]]


def gate_map(r: dict, prev_map: str, prev_spawn: str) -> dict:
    rid = r["id"]
    return {
        "$schema_version": 1, "id": f"{rid}_gate", "display_name": f"{r['name']} Gate",
        "region": rid, "bgm": "town", "tile_size": 32,
        "legend": {"#": "wall", ".": "ground", "D": "door", "H": "heal_pad"},
        "rows": [
            "############",
            "#..........#",
            "#..H.......#",
            "D..........D",
            "#..........#",
            "#..........#",
            "############",
        ],
        "objects": [
            {"type": "spawn", "id": "port", "x": 1, "y": 3},
            {"type": "spawn", "id": "from_wilds", "x": 10, "y": 3},
            {"type": "spawn", "id": "default", "x": 5, "y": 4},
            {"type": "door", "x": 0, "y": 3, "to_map": prev_map, "to_spawn": prev_spawn},
            {"type": "door", "x": 11, "y": 3, "to_map": f"{rid}_wilds", "to_spawn": "from_gate"},
            {"type": "heal", "x": 3, "y": 2, "sets_respawn": True, "respawn_spawn": "default"},
            {"type": "shop", "x": 8, "y": 2, "npc_id": f"{rid}_clerk", "sprite": "npc_clerk",
             "stock": SHOP_STOCK,
             "dialogue": [f"Clerk: Welcome to {r['name']}! Gear up for the {r['theme']}."]},
            {"type": "npc", "x": 6, "y": 2, "npc_id": f"{rid}_greeter", "sprite": "npc_villager",
             "dialogue": [f"Greeter: {r['name']} lies ahead — {r['theme']} as far as the eye can see.",
                          "The Summit Hall only opens to those the wilds have tested."]},
            {"type": "sign", "x": 2, "y": 4,
             "text": f"{r['name']} Gate — west: the port home. East: the wilds."},
        ],
    }


def wilds_map(r: dict) -> dict:
    rid = r["id"]
    lo, _ = band(r["order"])
    return {
        "$schema_version": 1, "id": f"{rid}_wilds", "display_name": f"{r['name']} Wilds",
        "region": rid, "bgm": "route", "tile_size": 32,
        "legend": {"#": "wall", ".": "ground", "~": "tall_grass", "P": "path", "D": "door"},
        "rows": [
            "##############",
            "#~~~....~~~..#",
            "#~~~....~~~..#",
            "#............#",
            "D....PPPP....D",
            "#............#",
            "#..~~~...~~~.#",
            "#..~~~...~~~.#",
            "##############",
        ],
        "objects": [
            {"type": "spawn", "id": "from_gate", "x": 1, "y": 4},
            {"type": "spawn", "id": "from_hall", "x": 12, "y": 4},
            {"type": "door", "x": 0, "y": 4, "to_map": f"{rid}_gate", "to_spawn": "from_wilds"},
            {"type": "door", "x": 13, "y": 4, "to_map": f"{rid}_hall", "to_spawn": "entrance",
             "requires_flag": f"beat_{rid}_scout",
             "locked_text": "The hall road opens once the wilds' scout acknowledges you."},
            {"type": "encounter_zone", "table": f"{rid}_encounters"},
            {"type": "trainer", "x": 7, "y": 3, "trainer_id": f"{rid}_scout",
             "sprite": "trainer_scout", "sight": 2, "facing": "down",
             "flag": f"beat_{rid}_scout"},
            {"type": "item", "x": 11, "y": 1, "item": "super_potion", "flag": f"item_{rid}_wilds_1"},
            {"type": "sign", "x": 4, "y": 3,
             "text": f"{r['name']} Wilds — locals report creatures around Lv {lo}."},
        ],
    }


def hall_map(r: dict, next_map: str) -> dict:
    rid = r["id"]
    rows = [
        "####D####" if next_map else "#########",
        "#.......#",
        "#.......#",
        "#.......#",
        "#.......#",
        "#.......#",
        "####D####",
    ]
    objects = [
        {"type": "spawn", "id": "entrance", "x": 4, "y": 5},
        {"type": "spawn", "id": "from_next", "x": 4, "y": 1},
        {"type": "door", "x": 4, "y": 6, "to_map": f"{rid}_wilds", "to_spawn": "from_hall"},
        {"type": "trainer", "x": 4, "y": 2, "trainer_id": f"{rid}_champion",
         "sprite": "trainer_champion", "sight": 2, "facing": "down",
         "flag": f"beat_{rid}_champion"},
        {"type": "sign", "x": 2, "y": 1,
         "text": f"{r['name']} Summit Hall — the {r['name']} Crest awaits."},
    ]
    if next_map:
        objects.append({"type": "door", "x": 4, "y": 0, "to_map": next_map, "to_spawn": "port",
                        "requires_flag": f"beat_{rid}_champion",
                        "locked_text": "The northern port opens to crest-bearers only."})
    else:
        objects.append({"type": "sign", "x": 6, "y": 1,
                        "text": "The charted world ends here... for now."})
    return {
        "$schema_version": 1, "id": f"{rid}_hall", "display_name": f"{r['name']} Summit Hall",
        "region": rid, "bgm": "town", "tile_size": 32,
        "legend": {"#": "wall", ".": "floor", "D": "door"},
        "rows": rows, "objects": objects,
    }


def main() -> None:
    creatures_doc = load(os.path.join(DATA, "creatures", "creatures.json"))
    trainers_doc = load(os.path.join(DATA, "trainers", "trainers.json"))
    encounters_doc = load(os.path.join(DATA, "encounters", "encounters.json"))
    quests_doc = load(os.path.join(DATA, "quests", "quests.json"))
    endings_doc = load(os.path.join(DATA, "endings", "endings.json"))
    creatures_by_id = {c["id"]: c for c in creatures_doc["creatures"]}

    prev_map, prev_spawn = "aquilon_shore", "from_north"
    for idx, r in enumerate(REGIONS):
        rid, lo, hi = r["id"], *band(r["order"])
        nxt = REGIONS[idx + 1] if idx + 1 < len(REGIONS) else None

        # Natives
        for spec in r["natives"]:
            rec = creature_record(spec, rid, r["order"])
            upsert(creatures_doc["creatures"], rec)
            creatures_by_id[rec["id"]] = rec

        # Encounter table: natives common, pool species filling out the band
        entries = [
            {"creature": r["natives"][0]["id"], "weight": 30, "level_min": lo, "level_max": lo + 6, "rarity": "common"},
            {"creature": r["natives"][1]["id"], "weight": 30, "level_min": lo, "level_max": lo + 6, "rarity": "common"},
            {"creature": r["pool"][0], "weight": 25, "level_min": lo, "level_max": lo + 5, "rarity": "common"},
            {"creature": r["pool"][1], "weight": 15, "level_min": lo + 2, "level_max": lo + 7, "rarity": "uncommon"},
        ]
        upsert(encounters_doc["tables"], {"id": f"{rid}_encounters", "region": rid, "entries": entries})

        # Trainers: scout (2 members) + boss champion (3 members, badge)
        s_lvls, c_lvls = [lo + 1, lo + 2], [lo + 5, lo + 6, lo + 8]
        scout_team = [
            {"creature": r["natives"][0]["id"], "level": s_lvls[0],
             "moves": trainer_moves(creatures_by_id[r["natives"][0]["id"]], s_lvls[0])},
            {"creature": r["pool"][0], "level": s_lvls[1],
             "moves": trainer_moves(creatures_by_id[r["pool"][0]], s_lvls[1])},
        ]
        champ_team = [
            {"creature": r["pool"][1], "level": c_lvls[0],
             "moves": trainer_moves(creatures_by_id[r["pool"][1]], c_lvls[0])},
            {"creature": r["natives"][0]["id"], "level": c_lvls[1],
             "moves": trainer_moves(creatures_by_id[r["natives"][0]["id"]], c_lvls[1])},
            {"creature": r["natives"][1]["id"], "level": c_lvls[2],
             "moves": trainer_moves(creatures_by_id[r["natives"][1]["id"]], c_lvls[2])},
        ]
        upsert(trainers_doc["trainers"], {
            "id": f"{rid}_scout", "display_name": f"Scout of {r['name']}",
            "sprite": "trainer_scout", "ai": "intermediate", "boss": False,
            "reward_money": 150 + 100 * r["order"],
            "dialogue_intro": f"Scout: The {r['theme']} test every traveler. Show me your mettle.",
            "dialogue_defeat": "Scout: The hall road is yours.",
            "dialogue_victory": "Scout: The wilds win today.",
            "team": scout_team,
        })
        upsert(trainers_doc["trainers"], {
            "id": f"{rid}_champion", "display_name": f"Champion of {r['name']}",
            "sprite": "trainer_champion", "ai": "advanced", "boss": True,
            "boss_scaling": "limited", "reward_money": 500 + 250 * r["order"],
            "reward_badge": f"{rid}_crest",
            "dialogue_intro": f"Champion: {r['name']} crowns only the worthy. Begin.",
            "dialogue_defeat": f"Champion: The {r['name']} Crest is yours. Travel on.",
            "dialogue_victory": "Champion: The summit is patient. Return stronger.",
            "team": champ_team,
        })

        # Quest
        rewards = [{"kind": "money", "amount": 400 + 200 * r["order"]},
                   {"kind": "item", "item": "great_orb", "quantity": 3}]
        if nxt:
            rewards.append({"kind": "unlock_region", "region": nxt["id"]})
        upsert(quests_doc["quests"], {
            "id": f"main_{rid}", "display_name": f"The {r['name']} Crest",
            "category": "main", "auto_start": False,
            "start_condition": {"kind": "flag", "flag": f"visited_{rid}"},
            "description": f"Cross the {r['theme']} of {r['name']} and claim its crest.",
            "objectives": [
                {"id": "obj_scout", "text": f"Defeat the Scout in the {r['name']} Wilds.",
                 "condition": {"kind": "flag", "flag": f"beat_{rid}_scout"}},
                {"id": "obj_champion", "text": f"Defeat the Champion of {r['name']}.",
                 "condition": {"kind": "flag", "flag": f"beat_{rid}_champion"}},
            ],
            "rewards": rewards,
            "on_complete_flag": f"quest_{rid}_done",
        })

        # Maps + manifest
        next_gate = f"{nxt['id']}_gate" if nxt else ""
        save(os.path.join(DATA, "regions", "maps", f"{rid}_gate.json"), gate_map(r, prev_map, prev_spawn))
        save(os.path.join(DATA, "regions", "maps", f"{rid}_wilds.json"), wilds_map(r))
        save(os.path.join(DATA, "regions", "maps", f"{rid}_hall.json"), hall_map(r, next_gate))
        save(os.path.join(DATA, "regions", f"region_{rid}.json"), {
            "$schema_version": 1, "id": rid, "display_name": r["name"], "order": r["order"],
            "starting_map": f"{rid}_gate",
            "recommended_level_min": lo, "recommended_level_max": hi,
            "badge_count": 1, "league_id": f"{rid}_league",
            "next_regions": [nxt["id"]] if nxt else [],
            "maps": [f"{rid}_gate", f"{rid}_wilds", f"{rid}_hall"],
            "regional_rules": {"level_scaling": "soft", "encounter_table": f"{rid}_encounters",
                               "allow_previous_team": True, "obedience_cap_level": hi + 10},
        })
        prev_map, prev_spawn = f"{rid}_hall", "from_next"

    # Grand ending: all nine crests (checked first — array order is priority)
    crest_flags = ["beat_gym_verdantia", "beat_aquilon_champion"] + \
        [f"beat_{r['id']}_champion" for r in REGIONS]
    grand = {
        "id": "ending_nine_crests", "title": "Legend of the Nine Crests",
        "condition": {"kind": "all",
                      "conditions": [{"kind": "flag", "flag": f} for f in crest_flags]},
        "lines": [
            "Nine regions. Nine crests. One unbroken road from Verdantia's meadows to Zephyra's storms.",
            "Professor Maple's final report needs no title but your name.",
            "Wherever new coastlines rise, the legend of the Nine Crests will arrive first.",
        ],
    }
    existing = [e for e in endings_doc["endings"] if e["id"] != grand["id"]]
    endings_doc["endings"] = [grand] + existing

    # Wire Aquilon into the chain
    aq = load(os.path.join(DATA, "regions", "region_aquilon.json"))
    aq["next_regions"] = ["cindral"]
    save(os.path.join(DATA, "regions", "region_aquilon.json"), aq)
    shore = load(os.path.join(DATA, "regions", "maps", "aquilon_shore.json"))
    shore["legend"]["D"] = "door"
    shore["rows"][0] = "WWWWWWWDWWWWWWW"
    for obj in [{"type": "spawn", "id": "from_north", "x": 7, "y": 1},
                {"type": "door", "x": 7, "y": 0, "to_map": "cindral_gate", "to_spawn": "port",
                 "requires_flag": "beat_aquilon_champion",
                 "locked_text": "The northern ferry serves crest-bearers only. Defeat Champion Isolde first."}]:
        if not any(o.get("type") == obj["type"] and o.get("x") == obj["x"] and o.get("y") == obj["y"]
                   for o in shore["objects"]):
            shore["objects"].append(obj)
    save(os.path.join(DATA, "regions", "maps", "aquilon_shore.json"), shore)

    # Aquilon league quest also unlocks Cindral
    for q in quests_doc["quests"]:
        if q["id"] == "main_aquilon_league":
            if not any(rw.get("kind") == "unlock_region" for rw in q["rewards"]):
                q["rewards"].append({"kind": "unlock_region", "region": "cindral"})

    save(os.path.join(DATA, "creatures", "creatures.json"), creatures_doc)
    save(os.path.join(DATA, "trainers", "trainers.json"), trainers_doc)
    save(os.path.join(DATA, "encounters", "encounters.json"), encounters_doc)
    save(os.path.join(DATA, "quests", "quests.json"), quests_doc)
    save(os.path.join(DATA, "endings", "endings.json"), endings_doc)
    print(f"Generated {len(REGIONS)} regions: " + ", ".join(r["id"] for r in REGIONS))


if __name__ == "__main__":
    main()
