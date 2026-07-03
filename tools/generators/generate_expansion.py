#!/usr/bin/env python3
"""Content expansion — original species lines, moves, route trainers, story arc.

Adds to the base data (idempotent upserts by id):
- ~15 new moves so every type has a usable early/mid/late kit;
- ~39 new ORIGINAL species across all nine regions (2-3 stage evolution lines,
  early-route bird/rodent archetypes, region singles, one apex rarity);
- 3 route trainers per generated region + extra trainers in Verdantia/Aquilon;
- an original antagonist arc: the Hollow Order (three agents + the Archon),
  its story quest and an extra ending.

Everything here is invented for this project. Run AFTER generate_regions.py.
Usage: python3 tools/generators/generate_expansion.py
"""
from __future__ import annotations

import json
import os

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA = os.path.join(ROOT, "data")

# ---------------------------------------------------------------- new moves

NEW_MOVES = [
    {"id": "rend", "display_name": "Rend", "type": "normal", "category": "physical",
     "power": 70, "accuracy": 95, "priority": 0, "pp": 20,
     "description": "A savage tearing strike.", "effects": [{"kind": "damage"}]},
    {"id": "blaze_wheel", "display_name": "Blaze Wheel", "type": "fire", "category": "physical",
     "power": 75, "accuracy": 95, "priority": 0, "pp": 15,
     "description": "A rolling charge sheathed in flame.",
     "effects": [{"kind": "damage"}, {"kind": "apply_status", "status": "burn", "chance": 0.1, "target": "enemy"}]},
    {"id": "inferno_ray", "display_name": "Inferno Ray", "type": "fire", "category": "special",
     "power": 95, "accuracy": 85, "priority": 0, "pp": 8,
     "description": "A concentrated beam of furnace heat.",
     "effects": [{"kind": "damage"}, {"kind": "apply_status", "status": "burn", "chance": 0.15, "target": "enemy"}]},
    {"id": "riptide", "display_name": "Riptide", "type": "water", "category": "physical",
     "power": 70, "accuracy": 100, "priority": 0, "pp": 15,
     "description": "A dragging undertow slam.", "effects": [{"kind": "damage"}]},
    {"id": "deluge", "display_name": "Deluge", "type": "water", "category": "special",
     "power": 95, "accuracy": 85, "priority": 0, "pp": 8,
     "description": "A crushing wall of water.",
     "effects": [{"kind": "damage"}, {"kind": "stat_change", "stat": "speed", "stages": -1, "chance": 0.2, "target": "enemy"}]},
    {"id": "thorn_barrage", "display_name": "Thorn Barrage", "type": "grass", "category": "physical",
     "power": 75, "accuracy": 95, "priority": 0, "pp": 15,
     "description": "A volley of hardened thorns.", "effects": [{"kind": "damage"}]},
    {"id": "bloom_burst", "display_name": "Bloom Burst", "type": "grass", "category": "special",
     "power": 90, "accuracy": 90, "priority": 0, "pp": 10,
     "description": "An explosive release of pollen and light.",
     "effects": [{"kind": "damage"}, {"kind": "apply_status", "status": "poison", "chance": 0.15, "target": "enemy"}]},
    {"id": "volt_lance", "display_name": "Volt Lance", "type": "electric", "category": "physical",
     "power": 75, "accuracy": 95, "priority": 0, "pp": 15,
     "description": "A piercing thrust of charge.",
     "effects": [{"kind": "damage"}, {"kind": "apply_status", "status": "paralyze", "chance": 0.1, "target": "enemy"}]},
    {"id": "storm_surge", "display_name": "Storm Surge", "type": "electric", "category": "special",
     "power": 95, "accuracy": 85, "priority": 0, "pp": 8,
     "description": "A cascading discharge.",
     "effects": [{"kind": "damage"}, {"kind": "apply_status", "status": "paralyze", "chance": 0.15, "target": "enemy"}]},
    {"id": "sand_grind", "display_name": "Sand Grind", "type": "earth", "category": "physical",
     "power": 60, "accuracy": 100, "priority": 0, "pp": 20,
     "description": "Abrasive grit that wears armor down.",
     "effects": [{"kind": "damage"}, {"kind": "stat_change", "stat": "defense", "stages": -1, "chance": 0.2, "target": "enemy"}]},
    {"id": "quake_stomp", "display_name": "Quake Stomp", "type": "earth", "category": "physical",
     "power": 85, "accuracy": 95, "priority": 0, "pp": 10,
     "description": "A ground-shaking stamp.", "effects": [{"kind": "damage"}]},
    {"id": "cyclone_dive", "display_name": "Cyclone Dive", "type": "wind", "category": "physical",
     "power": 80, "accuracy": 90, "priority": 0, "pp": 12,
     "description": "A spiraling aerial strike.", "effects": [{"kind": "damage"}]},
    {"id": "tempest", "display_name": "Tempest", "type": "wind", "category": "special",
     "power": 90, "accuracy": 85, "priority": 0, "pp": 8,
     "description": "A howling, battering gale.", "effects": [{"kind": "damage"}]},
    {"id": "dream_pulse", "display_name": "Dream Pulse", "type": "mystic", "category": "special",
     "power": 90, "accuracy": 90, "priority": 0, "pp": 10,
     "description": "A wave of overwhelming reverie.",
     "effects": [{"kind": "damage"}, {"kind": "stat_change", "stat": "sp_attack", "stages": -1, "chance": 0.2, "target": "enemy"}]},
    {"id": "veil_of_calm", "display_name": "Veil of Calm", "type": "mystic", "category": "status",
     "power": 0, "accuracy": 100, "priority": 0, "pp": 10,
     "description": "A soothing veil that mends wounds.", "effects": [{"kind": "heal", "fraction": 0.5}]},
]

# ------------------------------------------------------------- species lines

ROLES = {
    "swift":    [50, 58, 44, 52, 46, 78],
    "bruiser":  [58, 72, 55, 42, 48, 52],
    "guardian": [62, 52, 74, 44, 64, 34],
    "sage":     [52, 40, 48, 74, 64, 56],
    "balanced": [56, 56, 56, 56, 56, 56],
}
STAGE_MULT = [1.0, 1.38, 1.72]

TYPE_POOLS = {
    "normal":   ["tackle", "quick_jab", "rend", "focus_charge"],
    "fire":     ["ember_burst", "blaze_wheel", "flame_lash", "inferno_ray"],
    "water":    ["aqua_dart", "riptide", "tide_crash", "deluge"],
    "grass":    ["leaf_cut", "thorn_barrage", "vine_wrap", "bloom_burst"],
    "electric": ["spark_zap", "volt_lance", "static_field", "storm_surge"],
    "earth":    ["stone_toss", "sand_grind", "quake_stomp", "guard_up"],
    "wind":     ["gale_slash", "cyclone_dive", "tempest", "quick_jab"],
    "mystic":   ["mind_ray", "dream_pulse", "veil_of_calm", "focus_charge"],
}

# line: stages [(id, name, types, desc)], role, region, band_lo, evolve levels
LINES = [
    # --- Verdantia (band 2-10) ---
    {"region": "verdantia", "role": "swift", "lo": 2, "evolve": [14],
     "stages": [("chirpit", "Chirpit", ["wind"], "A restless fledgling that naps mid-hop."),
                ("galecrest", "Galecrest", ["wind"], "Its crest feathers read the wind like a map.")]},
    {"region": "verdantia", "role": "balanced", "lo": 2, "evolve": [15],
     "stages": [("nibbit", "Nibbit", ["normal"], "It gnaws fence posts to keep its teeth short."),
                ("gnawber", "Gnawber", ["normal"], "Its jaws can shear green branches in one bite.")]},
    {"region": "verdantia", "role": "sage", "lo": 3, "evolve": [12],
     "stages": [("glimbug", "Glimbug", ["grass", "mystic"], "A mossy beetle that blinks softly at dusk."),
                ("luminmoth", "Luminmoth", ["grass", "mystic"], "Meadows bloom brighter where it settles.")]},
    # --- Aquilon (band 8-18) ---
    {"region": "aquilon", "role": "guardian", "lo": 8, "evolve": [22],
     "stages": [("floekit", "Floekit", ["water", "earth"], "It naps on drift-stones in the cold surf."),
                ("floeguard", "Floeguard", ["water", "earth"], "Harbor folk trust it to watch the moorings.")]},
    {"region": "aquilon", "role": "swift", "lo": 9, "evolve": [],
     "stages": [("skerrit", "Skerrit", ["wind", "water"], "It skims wavetops chasing spray.")]},
    {"region": "aquilon", "role": "bruiser", "lo": 10, "evolve": [],
     "stages": [("brinemaw", "Brinemaw", ["water"], "Its bite marks are a fisher's tall tale.")]},
    # --- Cindral (band 14-24) ---
    {"region": "cindral", "role": "bruiser", "lo": 14, "evolve": [20, 34],
     "stages": [("flarekit", "Flarekit", ["fire"], "A cinder-tailed kit born near vents."),
                ("pyrelisk", "Pyrelisk", ["fire"], "Its scales bank heat for cold nights."),
                ("magmaraud", "Magmaraud", ["fire", "earth"], "Old lava tubes are its hunting halls.")]},
    {"region": "cindral", "role": "swift", "lo": 15, "evolve": [],
     "stages": [("sootwing", "Sootwing", ["fire", "wind"], "It rides thermals above the calderas.")]},
    # --- Solane (band 20-30) ---
    {"region": "solane", "role": "guardian", "lo": 20, "evolve": [24],
     "stages": [("cactling", "Cactling", ["grass", "earth"], "It buries itself to sip deep water."),
                ("saguarok", "Saguarok", ["grass", "earth"], "Caravans navigate by its silhouette.")]},
    {"region": "solane", "role": "sage", "lo": 21, "evolve": [],
     "stages": [("mirageel", "Mirageel", ["mystic"], "Travelers swear it was never there.")]},
    {"region": "solane", "role": "bruiser", "lo": 22, "evolve": [],
     "stages": [("scorchion", "Scorchion", ["fire", "earth"], "Its stinger cauterizes what it strikes.")]},
    # --- Umbra (band 26-36) ---
    {"region": "umbra", "role": "swift", "lo": 26, "evolve": [30],
     "stages": [("shadeling", "Shadeling", ["mystic"], "It pools in shadows like spilled ink."),
                ("umbrelynx", "Umbrelynx", ["mystic"], "Its eyes gather the last light of dusk.")]},
    {"region": "umbra", "role": "guardian", "lo": 27, "evolve": [32],
     "stages": [("sporeling", "Sporeling", ["grass"], "It naps beneath a cap of soft spores."),
                ("mycolossus", "Mycolossus", ["grass"], "A walking grove bound by fungal threads.")]},
    # --- Ferrock (band 32-42) ---
    {"region": "ferrock", "role": "bruiser", "lo": 32, "evolve": [36],
     "stages": [("ironsnout", "Ironsnout", ["earth"], "It roots for ore nuggets like truffles."),
                ("ferroboar", "Ferroboar", ["earth"], "Its tusks are prized by honest smiths.")]},
    {"region": "ferrock", "role": "swift", "lo": 33, "evolve": [],
     "stages": [("coilbolt", "Coilbolt", ["electric"], "A living spring that snaps with charge.")]},
    {"region": "ferrock", "role": "guardian", "lo": 34, "evolve": [],
     "stages": [("rustwing", "Rustwing", ["wind", "earth"], "Its oxidized feathers ring like chimes.")]},
    # --- Brume (band 38-48) ---
    {"region": "brume", "role": "guardian", "lo": 38, "evolve": [42],
     "stages": [("mireling", "Mireling", ["grass", "water"], "It surfaces only to watch the rain."),
                ("bogthorn", "Bogthorn", ["grass", "water"], "The fen reshapes itself around its roots.")]},
    {"region": "brume", "role": "swift", "lo": 39, "evolve": [],
     "stages": [("fogfin", "Fogfin", ["water", "wind"], "It swims through mist as easily as water.")]},
    {"region": "brume", "role": "sage", "lo": 40, "evolve": [],
     "stages": [("wispurr", "Wispurr", ["mystic"], "Its purr carries no sound, only calm.")]},
    # --- Lumen (band 44-54) ---
    {"region": "lumen", "role": "sage", "lo": 44, "evolve": [46],
     "stages": [("shardling", "Shardling", ["mystic", "earth"], "A splinter of the valley's oldest prism."),
                ("crystalisk", "Crystalisk", ["mystic", "earth"], "Light bends politely around it.")]},
    {"region": "lumen", "role": "swift", "lo": 45, "evolve": [],
     "stages": [("glowray", "Glowray", ["electric", "mystic"], "It glides on lines of static light.")]},
    # --- Zephyra (band 50-60) ---
    {"region": "zephyra", "role": "swift", "lo": 50, "evolve": [30, 52],
     "stages": [("nimbling", "Nimbling", ["wind"], "A puff of cloud with a stubborn streak."),
                ("cumulor", "Cumulor", ["wind"], "It herds smaller clouds across the steppe."),
                ("tempestrix", "Tempestrix", ["wind", "electric"], "Storm fronts part to let it pass.")]},
    {"region": "zephyra", "role": "sage", "lo": 52, "evolve": [],
     "stages": [("aetherion", "Aetherion", ["wind", "mystic"],
                 "The steppe's oldest legend: a sky-spirit seen once a generation."),],
     "apex": True},
]

APEX_STATS = [95, 105, 90, 125, 100, 115]


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def upsert(records, rec):
    for i, r in enumerate(records):
        if r.get("id") == rec["id"]:
            records[i] = rec
            return
    records.append(rec)


def build_learnset(types, lo, stage):
    """Level-up moves from the type pools, milestones scaled to the region band."""
    pool = []
    for j, t in enumerate(types):
        for k, mid in enumerate(TYPE_POOLS[t]):
            pool.append((k * 2 + j, mid))  # interleave dual types
    pool.sort()
    learn = [{"level": 1, "move": "tackle" if stage == 0 else pool[0][1]}]
    if stage == 0:
        learn.append({"level": 1, "move": pool[0][1]})
    step = 6
    lvl = max(2, lo + 2)
    for _, mid in pool[1:5]:
        if all(e["move"] != mid for e in learn):
            learn.append({"level": lvl, "move": mid})
            lvl += step
    return learn


def species_record(line, stage_idx):
    sid, name, types, desc = line["stages"][stage_idx]
    if line.get("apex"):
        stats = APEX_STATS
        capture, rarity = 5, "legendary"
    else:
        base = ROLES[line["role"]]
        mult = STAGE_MULT[stage_idx]
        stats = [min(160, int(v * mult)) for v in base]
        capture = [140, 70, 30][stage_idx]
        rarity = ["common", "uncommon", "rare"][stage_idx]
    evolves = []
    if stage_idx + 1 < len(line["stages"]):
        evolves = [line["stages"][stage_idx + 1][0]]
    hp, atk, dfn, spa, spd, spe = stats
    return {
        "id": sid, "display_name": name, "description": desc,
        "generation": "demo_g2", "origin_region": line["region"], "types": types,
        "base_stats": {"hp": hp, "attack": atk, "defense": dfn,
                       "sp_attack": spa, "sp_defense": spd, "speed": spe},
        "ev_yield": {"speed" if line["role"] == "swift" else "hp": 1 + stage_idx},
        "exp_curve": "medium_fast", "gender_ratio": 0.5,
        "abilities": ["swift_foot" if "wind" in types else
                      "keen_mind" if "mystic" in types else
                      "thick_hide" if "earth" in types else "blaze_heart" if "fire" in types else "tide_soul"],
        "capture_rate": capture, "rarity": rarity, "breeding_groups": ["field"],
        "learnset": build_learnset(types, line["lo"], stage_idx),
        "evolves_to": evolves, "forms": [],
    }


def trainer_moves(creature, level):
    moves = [e["move"] for e in creature["learnset"] if e["level"] <= level]
    return moves[-4:] if moves else [creature["learnset"][0]["move"]]


ROUTE_CLASSES = [
    ("rambler", "Rambler", "intermediate", "Rambler: These trails taught me everything. Your turn to learn!"),
    ("angler", "Angler", "basic", "Angler: Patience wins fights and fills nets. Got either?"),
    ("miner", "Miner", "intermediate", "Miner: I dig up more than ore out here. En garde!"),
]
ROUTE_SPOTS = [(2, 3, "down", 2), (11, 5, "up", 2), (6, 6, "right", 2)]

HOLLOW_REGIONS = ["cindral", "ferrock", "lumen"]
GENERATED = ["cindral", "solane", "umbra", "ferrock", "brume", "lumen", "zephyra"]


def band(order):
    lo = 6 * order - 4
    return lo, lo + 10


def main():
    creatures_doc = load(os.path.join(DATA, "creatures", "creatures.json"))
    moves_doc = load(os.path.join(DATA, "moves", "moves.json"))
    trainers_doc = load(os.path.join(DATA, "trainers", "trainers.json"))
    encounters_doc = load(os.path.join(DATA, "encounters", "encounters.json"))
    quests_doc = load(os.path.join(DATA, "quests", "quests.json"))
    endings_doc = load(os.path.join(DATA, "endings", "endings.json"))
    evolutions_doc = load(os.path.join(DATA, "evolutions", "evolutions.json"))

    for mv in NEW_MOVES:
        upsert(moves_doc["moves"], mv)

    by_id = {c["id"]: c for c in creatures_doc["creatures"]}
    natives_by_region = {}
    for line in LINES:
        for i in range(len(line["stages"])):
            rec = species_record(line, i)
            upsert(creatures_doc["creatures"], rec)
            by_id[rec["id"]] = rec
            natives_by_region.setdefault(line["region"], []).append(rec)
        for i, lvl in enumerate(line.get("evolve", [])):
            frm, to = line["stages"][i][0], line["stages"][i + 1][0]
            upsert(evolutions_doc["evolutions"],
                   {"id": f"evo_{frm}", "from": frm, "to": to,
                    "condition": {"kind": "level_up", "level": lvl}})

    # Encounter tables: stage-1 forms common, singles uncommon, apex ultra-rare.
    orders = {"verdantia": 1, "aquilon": 2, **{r: i + 3 for i, r in enumerate(GENERATED)}}
    for tbl in encounters_doc["tables"]:
        region = tbl.get("region", "")
        lo, _ = band(orders.get(region, 1)) if region != "verdantia" else (2, 10)
        if region == "aquilon":
            lo = 8
        existing = {e["creature"] for e in tbl["entries"]}
        for line in LINES:
            if line["region"] != region:
                continue
            sid = line["stages"][0][0]
            if sid in existing:
                continue
            if line.get("apex"):
                tbl["entries"].append({"creature": sid, "weight": 1,
                                       "level_min": lo + 5, "level_max": lo + 8, "rarity": "legendary"})
            else:
                multi = len(line["stages"]) > 1
                tbl["entries"].append({"creature": sid, "weight": 18 if multi else 10,
                                       "level_min": lo, "level_max": lo + 6,
                                       "rarity": "common" if multi else "uncommon"})

    # Route trainers in each generated region's wilds.
    for idx, rid in enumerate(GENERATED):
        lo, _ = band(idx + 3)
        locals_ = [c for c in natives_by_region.get(rid, []) if not c["evolves_to"] or c["rarity"] == "common"]
        locals_ = [c for c in locals_ if c["rarity"] != "legendary"] or [by_id["nibbit"]]
        wilds_path = os.path.join(DATA, "regions", "maps", f"{rid}_wilds.json")
        wilds = load(wilds_path)
        for t_i, (ckey, cname, ai, intro) in enumerate(ROUTE_CLASSES):
            tid = f"{rid}_{ckey}"
            picks = [locals_[t_i % len(locals_)], locals_[(t_i + 1) % len(locals_)]]
            team = [{"creature": p["id"], "level": lo + 1 + j,
                     "moves": trainer_moves(p, lo + 1 + j)} for j, p in enumerate(picks)]
            upsert(trainers_doc["trainers"], {
                "id": tid, "display_name": f"{cname} of {rid.capitalize()}",
                "sprite": f"trainer_{ckey}", "ai": ai, "boss": False,
                "reward_money": 100 + 60 * (idx + 3),
                "dialogue_intro": intro,
                "dialogue_defeat": f"{cname}: Well fought. The road is yours.",
                "dialogue_victory": f"{cname}: The road humbles everyone eventually.",
                "team": team,
            })
            x, y, facing, sight = ROUTE_SPOTS[t_i]
            obj = {"type": "trainer", "x": x, "y": y, "trainer_id": tid,
                   "sprite": f"trainer_{ckey}", "sight": sight, "facing": facing,
                   "flag": f"beat_{tid}"}
            if not any(o.get("trainer_id") == tid for o in wilds["objects"]):
                wilds["objects"].append(obj)
        # Hollow Order agent in selected regions.
        if rid in HOLLOW_REGIONS:
            tid = f"hollow_agent_{rid}"
            picks = [locals_[0], locals_[-1]]
            team = [{"creature": p["id"], "level": lo + 3 + j,
                     "moves": trainer_moves(p, lo + 3 + j)} for j, p in enumerate(picks)]
            upsert(trainers_doc["trainers"], {
                "id": tid, "display_name": "Hollow Order Agent",
                "sprite": "trainer_hollow", "ai": "advanced", "boss": False,
                "reward_money": 200 + 80 * (idx + 3),
                "dialogue_intro": "Agent: The Order hollows out what trainers hoard. Stand aside.",
                "dialogue_defeat": "Agent: The Archon will hear of you...",
                "dialogue_victory": "Agent: Hoarders always fall.",
                "team": team,
            })
            obj = {"type": "trainer", "x": 10, "y": 2, "trainer_id": tid,
                   "sprite": "trainer_hollow", "sight": 2, "facing": "down",
                   "flag": f"beat_{tid}"}
            if not any(o.get("trainer_id") == tid for o in wilds["objects"]):
                wilds["objects"].append(obj)
        save(wilds_path, wilds)

    # The Archon waits in Zephyra's wilds.
    zw_path = os.path.join(DATA, "regions", "maps", "zephyra_wilds.json")
    zw = load(zw_path)
    upsert(trainers_doc["trainers"], {
        "id": "hollow_archon", "display_name": "Hollow Archon",
        "sprite": "trainer_archon", "ai": "advanced", "boss": True,
        "boss_scaling": "limited", "reward_money": 4000,
        "dialogue_intro": "Archon: Every crest you carry fed the Order's ledger. Time to collect.",
        "dialogue_defeat": "Archon: The Order... hollowed by its own design. Fitting.",
        "dialogue_victory": "Archon: As hollow as the rest.",
        "team": [
            {"creature": "umbrelynx", "level": 54, "moves": trainer_moves(by_id["umbrelynx"], 54)},
            {"creature": "crystalisk", "level": 55, "moves": trainer_moves(by_id["crystalisk"], 55)},
            {"creature": "tempestrix", "level": 57, "moves": trainer_moves(by_id["tempestrix"], 57)},
        ],
    })
    archon_obj = {"type": "trainer", "x": 4, "y": 1, "trainer_id": "hollow_archon",
                  "sprite": "trainer_archon", "sight": 2, "facing": "down",
                  "flag": "beat_hollow_archon"}
    if not any(o.get("trainer_id") == "hollow_archon" for o in zw["objects"]):
        zw["objects"].append(archon_obj)
    save(zw_path, zw)

    # Extra trainers in Verdantia / Aquilon (hand-placed coordinates).
    manual = [
        ("verdantia_route", "meadow_rambler", "Rambler Tass", "rambler", "intermediate",
         (9, 5, "left", 3), [("nibbit", 6), ("chirpit", 7)], 150,
         "Tass: Fresh boots on the route! Let's break them in."),
        ("verdantia_forest", "forest_botanist", "Botanist Fen", "botanist", "intermediate",
         (10, 7, "left", 4), [("glimbug", 8), ("sproutkit", 9)], 200,
         "Fen: The forest shares its secrets with the persistent. Are you?"),
        ("aquilon_shore", "shore_angler", "Angler Morrow", "angler", "basic",
         (10, 5, "left", 4), [("brinemaw", 11), ("floekit", 12)], 260,
         "Morrow: The tide brought me a challenger for once!"),
        ("aquilon_ridge", "ridge_drifter", "Drifter Kael", "drifter", "intermediate",
         (3, 3, "right", 2), [("skerrit", 12), ("gustling", 13)], 300,
         "Kael: The ridge wind carries rumors of you. Let's verify them."),
    ]
    for map_id, tid, name, ckey, ai, (x, y, facing, sight), team_spec, money, intro in manual:
        team = [{"creature": cid, "level": lvl, "moves": trainer_moves(by_id[cid], lvl)}
                for cid, lvl in team_spec]
        upsert(trainers_doc["trainers"], {
            "id": tid, "display_name": name, "sprite": f"trainer_{ckey}",
            "ai": ai, "boss": False, "reward_money": money,
            "dialogue_intro": intro,
            "dialogue_defeat": f"{name.split()[0]}: Well fought.",
            "dialogue_victory": f"{name.split()[0]}: Another day, another win.",
            "team": team,
        })
        mp = os.path.join(DATA, "regions", "maps", f"{map_id}.json")
        m = load(mp)
        obj = {"type": "trainer", "x": x, "y": y, "trainer_id": tid,
               "sprite": f"trainer_{ckey}", "sight": sight, "facing": facing,
               "flag": f"beat_{tid}"}
        if not any(o.get("trainer_id") == tid for o in m["objects"]):
            m["objects"].append(obj)
        save(mp, m)

    # Story quest + ending for the Hollow Order arc.
    upsert(quests_doc["quests"], {
        "id": "main_hollow_order", "display_name": "Shadows of the Hollow Order",
        "category": "main", "auto_start": False,
        "start_condition": {"kind": "flag", "flag": "visited_cindral"},
        "description": "A shadowy order is shaking down trainers along the northern roads. Root out its agents and unmask their Archon.",
        "objectives": [
            {"id": "obj_agent1", "text": "Defeat the Hollow agent in Cindral.",
             "condition": {"kind": "flag", "flag": "beat_hollow_agent_cindral"}},
            {"id": "obj_agent2", "text": "Defeat the Hollow agent in Ferrock.",
             "condition": {"kind": "flag", "flag": "beat_hollow_agent_ferrock"}},
            {"id": "obj_agent3", "text": "Defeat the Hollow agent in Lumen.",
             "condition": {"kind": "flag", "flag": "beat_hollow_agent_lumen"}},
            {"id": "obj_archon", "text": "Defeat the Hollow Archon in the Zephyra Wilds.",
             "condition": {"kind": "flag", "flag": "beat_hollow_archon"}},
        ],
        "rewards": [{"kind": "money", "amount": 5000},
                    {"kind": "item", "item": "revive", "quantity": 3}],
        "on_complete_flag": "quest_hollow_done",
    })
    upsert(endings_doc["endings"], {
        "id": "ending_order_undone", "title": "The Hollow, Undone",
        "condition": {"kind": "all", "conditions": [
            {"kind": "flag", "flag": "quest_aquilon_done"},
            {"kind": "flag", "flag": "quest_hollow_done"},
        ]},
        "lines": [
            "With the Archon unmasked, the Hollow Order's ledgers burn in every region at once.",
            "Trainers walk the northern roads without looking over their shoulders again.",
            "Professor Maple's report gains a final chapter: the one where you gave the roads back.",
        ],
    })
    # Canonical first-match-wins order. Must stay in sync with ENDING_ORDER in
    # generate_story_placements.py (which runs later and re-enforces it).
    priority = ["ending_nine_crests", "ending_rivals_true", "ending_order_mercy",
                "ending_order_justice", "ending_order_undone", "ending_champion",
                "ending_bonds", "ending_lone_pioneer"]
    endings_doc["endings"].sort(
        key=lambda e: priority.index(e["id"]) if e["id"] in priority else 99)

    save(os.path.join(DATA, "creatures", "creatures.json"), creatures_doc)
    save(os.path.join(DATA, "moves", "moves.json"), moves_doc)
    save(os.path.join(DATA, "trainers", "trainers.json"), trainers_doc)
    save(os.path.join(DATA, "encounters", "encounters.json"), encounters_doc)
    save(os.path.join(DATA, "quests", "quests.json"), quests_doc)
    save(os.path.join(DATA, "endings", "endings.json"), endings_doc)
    save(os.path.join(DATA, "evolutions", "evolutions.json"), evolutions_doc)
    n_species = sum(len(l["stages"]) for l in LINES)
    print(f"Expansion applied: +{len(NEW_MOVES)} moves, +{n_species} species, "
          f"+{len(GENERATED) * 3 + len(HOLLOW_REGIONS) + 1 + len(manual)} trainers, Hollow Order arc.")


if __name__ == "__main__":
    main()
