#!/usr/bin/env python3
"""League generator — full gym circuit, Elite Four and Champion for every region.

For EACH of the nine regions this adds (idempotent, all ORIGINAL content):
- a Crossroads city map with EIGHT gyms — one per elemental type, so every type
  is represented in every region — each with a themed leader and its own badge;
- a "gym circuit" quest whose completion (all 8 badges) opens the League;
- a League Hall: a choke-point corridor where the FOUR Elite trainers must be
  beaten in sequence before the region Champion (5-creature team);
- enough native species that every type has an evolution line in every region
  (the dex generator below guarantees type coverage; raise EXTRA_LINES to grow
  the dex further toward very large counts).

Run AFTER generate_regions.py and generate_expansion.py.
Usage: python3 tools/generators/generate_league.py
"""
from __future__ import annotations

import json
import os

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA = os.path.join(ROOT, "data")

TYPES = ["normal", "fire", "water", "grass", "electric", "earth", "wind", "mystic"]

# Region id -> (order, band_lo). Bands drive wild levels, gym/elite/champion levels.
REGION_ORDERS = {
    "verdantia": (1, 2), "aquilon": (2, 8), "cindral": (3, 14), "solane": (4, 20),
    "umbra": (5, 26), "ferrock": (6, 32), "brume": (7, 38), "lumen": (8, 44),
    "zephyra": (9, 50),
}
CHAIN_NEXT = {"cindral": "solane", "solane": "umbra", "umbra": "ferrock",
              "ferrock": "brume", "brume": "lumen", "lumen": "zephyra"}
GENERATED = ["cindral", "solane", "umbra", "ferrock", "brume", "lumen", "zephyra"]

# Extra non-type-anchored dual lines per region (raise to grow the dex a lot).
EXTRA_LINES = 4

# ------------------------------------------------------------- name material

ROOTS = {
    "normal":   ["fawn", "bristle", "tuft", "burrow", "meadow", "loper", "whisk", "dapple", "vale", "harrow", "clover", "russet"],
    "fire":     ["cinder", "pyre", "scorch", "brand", "kiln", "ashen", "torch", "smolder", "furn", "charr", "blazen", "hearth"],
    "water":    ["brine", "ripple", "cove", "torrent", "pearl", "lagoon", "spume", "current", "delta", "shoal", "drift", "mist"],
    "grass":    ["bramble", "fern", "moss", "petal", "sap", "verdure", "thistle", "willow", "sprig", "canopy", "loam", "seed"],
    "electric": ["volt", "arc", "spark", "ion", "surge", "flux", "coil", "jolt", "ampere", "static", "fulgor", "dynamo"],
    "earth":    ["boulder", "shale", "clay", "granite", "dune", "quarry", "tremor", "basalt", "ridge", "cairn", "silt", "marl"],
    "wind":     ["zephyr", "squall", "breeze", "cirrus", "gust", "aero", "strato", "billow", "vane", "soar", "kestrel", "draft"],
    "mystic":   ["opal", "rune", "trance", "aura", "omen", "seer", "myst", "arcane", "glyph", "solace", "vision", "eidol"],
}
SUFFIXES = [["ling", "it", "et", "ie", "kin", "let"],
            ["claw", "fang", "mane", "wing", "horn", "tail"],
            ["lord", "wyrm", "titan", "monarch", "warden", "sage"]]

LEADER_NAMES = ["Mira", "Torv", "Ashka", "Bren", "Sylla", "Odan", "Vesse", "Karn",
                "Ilya", "Roan", "Petra", "Sorrel", "Yara", "Colm", "Nyssa", "Garrick"]
ELITE_NAMES = ["Halvard", "Imara", "Cassiel", "Rooke", "Solenne", "Vantor", "Ondine",
               "Merrick", "Thessa", "Ludo", "Averil", "Coriane"]
TYPE_TITLES = {"normal": "Plainskeeper", "fire": "Ember Sage", "water": "Tidecaller",
               "grass": "Grovewarden", "electric": "Stormsmith", "earth": "Cairnbreaker",
               "wind": "Skydancer", "mystic": "Dreambinder"}

ROLE_BY_TYPE = {"normal": "balanced", "fire": "bruiser", "water": "guardian",
                "grass": "balanced", "electric": "swift", "earth": "guardian",
                "wind": "swift", "mystic": "sage"}
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
DUAL_COMBOS = [("fire", "wind"), ("water", "earth"), ("grass", "mystic"), ("electric", "normal")]


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
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
    pool = []
    for j, t in enumerate(types):
        for k, mid in enumerate(TYPE_POOLS[t]):
            pool.append((k * 2 + j, mid))
    pool.sort()
    learn = [{"level": 1, "move": "tackle" if stage == 0 else pool[0][1]}]
    if stage == 0:
        learn.append({"level": 1, "move": pool[0][1]})
    lvl = max(2, lo + 2)
    for _, mid in pool[1:5]:
        if all(e["move"] != mid for e in learn):
            learn.append({"level": lvl, "move": mid})
            lvl += 6
    return learn


class Dex:
    """Region×type species lines with guaranteed coverage and unique names."""

    def __init__(self, creatures_doc, evolutions_doc):
        self.creatures = creatures_doc["creatures"]
        self.evolutions = evolutions_doc["evolutions"]
        self.used = {c["id"] for c in self.creatures}
        self.lines = {}  # (region, type) -> [species ids by stage]

    def _name(self, tkey, region_order, offset, stage):
        roots = ROOTS[tkey]
        for attempt in range(len(roots)):
            root = roots[(region_order * 3 + offset + attempt) % len(roots)]
            suffix = SUFFIXES[stage][(region_order + offset + attempt) % len(SUFFIXES[stage])]
            sid = root + suffix
            if sid not in self.used:
                self.used.add(sid)
                return sid
        sid = f"{roots[0]}{region_order}{offset}{stage}"
        self.used.add(sid)
        return sid

    def make_line(self, region, types, n_stages, lo, order, offset):
        role = ROLE_BY_TYPE[types[0]]
        growth = 1.0 + 0.02 * (order - 1)
        ids = []
        for s in range(n_stages):
            sid = self._name(types[0], order, offset, s)
            base = ROLES[role]
            stats = [min(160, int(v * STAGE_MULT[s] * growth)) for v in base]
            hp, atk, dfn, spa, spd, spe = stats
            ids.append(sid)
            upsert(self.creatures, {
                "id": sid, "display_name": sid.capitalize(),
                "description": f"A {types[0]}-attuned native of the {region.capitalize()} region.",
                "generation": "demo_g3", "origin_region": region, "types": list(types),
                "base_stats": {"hp": hp, "attack": atk, "defense": dfn,
                               "sp_attack": spa, "sp_defense": spd, "speed": spe},
                "ev_yield": {"speed" if role == "swift" else "hp": 1 + s},
                "exp_curve": "medium_fast", "gender_ratio": 0.5,
                "abilities": ["swift_foot" if "wind" in types else
                              "keen_mind" if "mystic" in types else
                              "thick_hide" if "earth" in types else
                              "blaze_heart" if "fire" in types else "tide_soul"],
                "capture_rate": [140, 70, 30][s], "rarity": ["common", "uncommon", "rare"][s],
                "breeding_groups": ["field"], "learnset": build_learnset(list(types), lo, s),
                "evolves_to": [], "forms": [],
            })
        # Wire evolutions
        evolve_levels = []
        for s in range(n_stages - 1):
            lvl = min(58, lo + 6 + s * 12)
            evolve_levels.append(lvl)
            for c in self.creatures:
                if c["id"] == ids[s]:
                    c["evolves_to"] = [ids[s + 1]]
            upsert(self.evolutions, {"id": f"evo_{ids[s]}", "from": ids[s], "to": ids[s + 1],
                                     "condition": {"kind": "level_up", "level": lvl}})
        return {"ids": ids, "evolve": evolve_levels}

    def form_for_level(self, line, level):
        idx = sum(1 for e in line["evolve"] if e <= level)
        return line["ids"][min(idx, len(line["ids"]) - 1)]


def crossroads_map(rid, region_name, wilds_map, wilds_spawn):
    doors_top = [(2, TYPES[0]), (5, TYPES[1]), (8, TYPES[2]), (11, TYPES[3])]
    doors_bot = [(2, TYPES[4]), (5, TYPES[5]), (8, TYPES[6]), (11, TYPES[7])]
    objects = [
        {"type": "spawn", "id": "from_wilds", "x": 1, "y": 3},
        {"type": "spawn", "id": "from_league", "x": 14, "y": 5},
        {"type": "spawn", "id": "default", "x": 7, "y": 5},
        {"type": "door", "x": 0, "y": 3, "to_map": wilds_map, "to_spawn": wilds_spawn},
        {"type": "door", "x": 15, "y": 5, "to_map": f"{rid}_league" if rid in ("verdantia", "aquilon") else f"{rid}_hall",
         "to_spawn": "entrance", "requires_flag": f"league_open_{rid}",
         "locked_text": "The League gates open only to holders of all eight %s badges." % region_name},
        {"type": "heal", "x": 7, "y": 4, "sets_respawn": True, "respawn_spawn": "default"},
        {"type": "sign", "x": 6, "y": 5, "text": f"{region_name} Crossroads — eight gyms, one League."},
    ]
    for x, t in doors_top:
        objects.append({"type": "door", "x": x, "y": 0, "to_map": f"{rid}_gym_{t}", "to_spawn": "entrance"})
        objects.append({"type": "spawn", "id": f"from_{t}_gym", "x": x, "y": 1})
    for x, t in doors_bot:
        objects.append({"type": "door", "x": x, "y": 8, "to_map": f"{rid}_gym_{t}", "to_spawn": "entrance"})
        objects.append({"type": "spawn", "id": f"from_{t}_gym", "x": x, "y": 7})
    return {
        "$schema_version": 1, "id": f"{rid}_crossroads", "display_name": f"{region_name} Crossroads",
        "region": rid, "bgm": "town", "tile_size": 32,
        "legend": {"#": "wall", ".": "ground", "D": "door", "H": "heal_pad"},
        "rows": [
            "##D##D##D##D####",
            "#..............#",
            "#..............#",
            "D..............#",
            "#......H.......#",
            "#..............D",
            "#..............#",
            "#..............#",
            "##D##D##D##D####",
        ],
        "objects": objects,
    }


def gym_map(rid, region_name, t, back_spawn):
    return {
        "$schema_version": 1, "id": f"{rid}_gym_{t}", "display_name": f"{region_name} {t.capitalize()} Gym",
        "region": rid, "bgm": "town", "tile_size": 32,
        "legend": {"#": "wall", ".": "floor", "D": "door"},
        "rows": ["#######", "#.....#", "#.....#", "#.....#", "#.....#", "#.....#", "###D###"],
        "objects": [
            {"type": "spawn", "id": "entrance", "x": 3, "y": 5},
            {"type": "door", "x": 3, "y": 6, "to_map": f"{rid}_crossroads", "to_spawn": back_spawn},
            {"type": "trainer", "x": 3, "y": 2, "trainer_id": f"{rid}_gym_{t}",
             "sprite": "trainer_gym", "sight": 2, "facing": "down", "flag": f"beat_{rid}_gym_{t}"},
            {"type": "sign", "x": 1, "y": 1, "text": f"{TYPE_TITLES[t]}'s gym — {t} techniques honored here."},
        ],
    }


def league_map(rid, region_name, map_id, next_gate):
    rows = [
        "####D####" if next_gate else "#########",
        "#.......#",
        "#.......#",
        "#.......#",
        "####.####",
        "#.......#",
        "####.####",
        "#.......#",
        "####.####",
        "#.......#",
        "####.####",
        "#.......#",
        "#...H...#",
        "#.......#",
        "####D####",
    ]
    objects = [
        {"type": "spawn", "id": "entrance", "x": 4, "y": 13},
        {"type": "spawn", "id": "from_next", "x": 4, "y": 1},
        {"type": "door", "x": 4, "y": 14, "to_map": f"{rid}_crossroads", "to_spawn": "from_league"},
        {"type": "heal", "x": 4, "y": 12, "sets_respawn": True, "respawn_spawn": "entrance"},
        {"type": "sign", "x": 2, "y": 11, "text": f"{region_name} League — four Elites guard the Champion."},
    ]
    for i, y in enumerate([10, 8, 6, 4]):
        objects.append({"type": "trainer", "x": 4, "y": y, "trainer_id": f"{rid}_elite_{i + 1}",
                        "sprite": "trainer_elite", "sight": 1, "facing": "down",
                        "flag": f"beat_{rid}_elite_{i + 1}"})
    champ_id = {"verdantia": "verdantia_sovereign", "aquilon": "aquilon_marshal"}.get(rid, f"{rid}_champion")
    objects.append({"type": "trainer", "x": 4, "y": 2, "trainer_id": champ_id,
                    "sprite": "trainer_champion", "sight": 2, "facing": "down",
                    "flag": f"beat_{champ_id}"})
    if next_gate:
        objects.append({"type": "door", "x": 4, "y": 0, "to_map": next_gate, "to_spawn": "port",
                        "requires_flag": f"beat_{champ_id}",
                        "locked_text": "The northern port opens to crest-bearers only."})
    else:
        objects.append({"type": "sign", "x": 6, "y": 1, "text": "The charted world ends here... for now."})
    return {
        "$schema_version": 1, "id": map_id, "display_name": f"{region_name} League",
        "region": rid, "bgm": "town", "tile_size": 32,
        "legend": {"#": "wall", ".": "floor", "D": "door", "H": "heal_pad"},
        "rows": rows, "objects": objects,
    }


def main():
    creatures_doc = load(os.path.join(DATA, "creatures", "creatures.json"))
    evolutions_doc = load(os.path.join(DATA, "evolutions", "evolutions.json"))
    trainers_doc = load(os.path.join(DATA, "trainers", "trainers.json"))
    encounters_doc = load(os.path.join(DATA, "encounters", "encounters.json"))
    quests_doc = load(os.path.join(DATA, "quests", "quests.json"))

    dex = Dex(creatures_doc, evolutions_doc)

    for rid, (order, lo) in REGION_ORDERS.items():
        region_name = rid.capitalize()
        # --- species: one line per type per region + extra dual-type flavor lines
        for t_i, t in enumerate(TYPES):
            n_stages = 3 if t_i in (order % 8, (order + 3) % 8) else 2
            dex.lines[(rid, t)] = dex.make_line(rid, (t,), n_stages, lo, order, t_i)
        for x_i, combo in enumerate(DUAL_COMBOS[:EXTRA_LINES]):
            dex.make_line(rid, combo, 2, lo, order, 8 + x_i)

        # --- encounter table: add every stage-1 type native (keeps all types wild)
        tbl = next((t for t in encounters_doc["tables"] if t.get("region") == rid), None)
        if tbl is not None:
            existing = {e["creature"] for e in tbl["entries"]}
            for t in TYPES:
                sid = dex.lines[(rid, t)]["ids"][0]
                if sid not in existing:
                    tbl["entries"].append({"creature": sid, "weight": 8,
                                           "level_min": lo, "level_max": lo + 6, "rarity": "common"})

        # --- 8 gym leaders (one per type)
        for g_i, t in enumerate(TYPES):
            lvl = lo + 1 + g_i
            line = dex.lines[(rid, t)]
            team = []
            for j in range(3):
                mlvl = max(2, lvl - 2 + j)
                sid = dex.form_for_level(line, mlvl)
                spec = next(c for c in creatures_doc["creatures"] if c["id"] == sid)
                moves = [e["move"] for e in spec["learnset"] if e["level"] <= mlvl][-4:]
                team.append({"creature": sid, "level": mlvl, "moves": moves or [spec["learnset"][0]["move"]]})
            leader = LEADER_NAMES[(order * 5 + g_i) % len(LEADER_NAMES)]
            upsert(trainers_doc["trainers"], {
                "id": f"{rid}_gym_{t}", "display_name": f"{TYPE_TITLES[t]} {leader}",
                "sprite": "trainer_gym", "ai": "advanced", "boss": True, "boss_scaling": "limited",
                "reward_money": 300 + 120 * order + 40 * g_i,
                "reward_badge": f"{rid}_{t}_badge",
                "dialogue_intro": f"{leader}: {TYPE_TITLES[t]}s test every challenger with pure {t} craft. Begin!",
                "dialogue_defeat": f"{leader}: Masterfully done. The {t} badge of {region_name} is yours.",
                "dialogue_victory": f"{leader}: Study the {t} arts and return.",
                "team": team,
            })

        # --- 4 Elites + Champion (5-creature team)
        for e_i in range(4):
            lvl = lo + 9 + e_i
            e_types = [TYPES[(order + e_i * 2 + k) % 8] for k in range(4)]
            team = []
            for k, t in enumerate(e_types):
                line = dex.lines[(rid, t)]
                mlvl = max(2, lvl - 1 + (k % 2))
                sid = dex.form_for_level(line, mlvl)
                spec = next(c for c in creatures_doc["creatures"] if c["id"] == sid)
                moves = [e["move"] for e in spec["learnset"] if e["level"] <= mlvl][-4:]
                team.append({"creature": sid, "level": mlvl, "moves": moves or [spec["learnset"][0]["move"]]})
            ename = ELITE_NAMES[(order * 3 + e_i) % len(ELITE_NAMES)]
            upsert(trainers_doc["trainers"], {
                "id": f"{rid}_elite_{e_i + 1}", "display_name": f"Elite {ename}",
                "sprite": "trainer_elite", "ai": "advanced", "boss": True, "boss_scaling": "limited",
                "reward_money": 800 + 200 * order + 100 * e_i,
                "dialogue_intro": f"{ename}: The Elite Four of {region_name} yield to no one unproven.",
                "dialogue_defeat": f"{ename}: Proven. Pass.",
                "dialogue_victory": f"{ename}: The corridor ends here for you.",
                "team": team,
            })
        champ_id = {"verdantia": "verdantia_sovereign", "aquilon": "aquilon_marshal"}.get(rid, f"{rid}_champion")
        champ_name = {"verdantia": "Sovereign Laurel", "aquilon": "Marshal Eirwen"}.get(
            rid, f"Champion of {region_name}")
        c_types = [TYPES[(order + k * 3) % 8] for k in range(5)]
        team = []
        for k, t in enumerate(c_types):
            line = dex.lines[(rid, t)]
            mlvl = lo + 12 + (k % 3)
            sid = dex.form_for_level(line, mlvl)
            spec = next(c for c in creatures_doc["creatures"] if c["id"] == sid)
            moves = [e["move"] for e in spec["learnset"] if e["level"] <= mlvl][-4:]
            team.append({"creature": sid, "level": mlvl, "moves": moves or [spec["learnset"][0]["move"]]})
        upsert(trainers_doc["trainers"], {
            "id": champ_id, "display_name": champ_name,
            "sprite": "trainer_champion", "ai": "advanced", "boss": True, "boss_scaling": "limited",
            "reward_money": 1500 + 400 * order,
            "reward_badge": f"{rid}_crest",
            "dialogue_intro": f"{champ_name}: Eight badges brought you here. Show me their weight.",
            "dialogue_defeat": f"{champ_name}: {region_name} bows to a new Champion.",
            "dialogue_victory": f"{champ_name}: Come back when the badges feel heavier.",
            "team": team,
        })

        # --- circuit quest: all 8 badges open the League
        upsert(quests_doc["quests"], {
            "id": f"circuit_{rid}", "display_name": f"The {region_name} Gym Circuit",
            "category": "main", "auto_start": False,
            "start_condition": {"kind": "flag", "flag": f"visited_{rid}"},
            "description": f"Defeat all eight gym leaders of {region_name} to open its League.",
            "objectives": [
                {"id": f"obj_{t}", "text": f"Earn the {t} badge ({TYPE_TITLES[t]}).",
                 "condition": {"kind": "flag", "flag": f"beat_{rid}_gym_{t}"}} for t in TYPES
            ],
            "rewards": [{"kind": "money", "amount": 1000 + 500 * order}],
            "on_complete_flag": f"league_open_{rid}",
        })

        # --- maps
        wilds_map_id = {"verdantia": "verdantia_route", "aquilon": "aquilon_shore"}.get(rid, f"{rid}_wilds")
        wilds_return_spawn = "from_crossroads" if rid in ("verdantia", "aquilon") else "from_hall"
        save(os.path.join(DATA, "regions", "maps", f"{rid}_crossroads.json"),
             crossroads_map(rid, region_name, wilds_map_id, wilds_return_spawn))
        for t in TYPES:
            save(os.path.join(DATA, "regions", "maps", f"{rid}_gym_{t}.json"),
                 gym_map(rid, region_name, t, f"from_{t}_gym"))
        league_id = f"{rid}_league" if rid in ("verdantia", "aquilon") else f"{rid}_hall"
        next_gate = f"{CHAIN_NEXT[rid]}_gate" if rid in CHAIN_NEXT else ""
        save(os.path.join(DATA, "regions", "maps", f"{league_id}.json"),
             league_map(rid, region_name, league_id, next_gate))

        # --- wire the crossroads into the world
        if rid in GENERATED:
            wp = os.path.join(DATA, "regions", "maps", f"{rid}_wilds.json")
            wilds = load(wp)
            for o in wilds["objects"]:
                if o.get("type") == "door" and o.get("x") == 13:
                    o["to_map"] = f"{rid}_crossroads"
                    o["to_spawn"] = "from_wilds"
            save(wp, wilds)
        elif rid == "verdantia":
            rp = os.path.join(DATA, "regions", "maps", "verdantia_route.json")
            route = load(rp)
            route["legend"]["D"] = "door"
            route["rows"][3] = route["rows"][3][:14] + "D"
            for obj in [{"type": "spawn", "id": "from_crossroads", "x": 13, "y": 3},
                        {"type": "door", "x": 14, "y": 3, "to_map": "verdantia_crossroads",
                         "to_spawn": "from_wilds"}]:
                if not any(o.get("type") == obj["type"] and o.get("x") == obj["x"] and o.get("y") == obj["y"]
                           for o in route["objects"]):
                    route["objects"].append(obj)
            save(rp, route)
        elif rid == "aquilon":
            sp = os.path.join(DATA, "regions", "maps", "aquilon_shore.json")
            shore = load(sp)
            shore["rows"][5] = shore["rows"][5][:14] + "D"
            for obj in [{"type": "spawn", "id": "from_crossroads", "x": 13, "y": 5},
                        {"type": "door", "x": 14, "y": 5, "to_map": "aquilon_crossroads",
                         "to_spawn": "from_wilds"}]:
                if not any(o.get("type") == obj["type"] and o.get("x") == obj["x"] and o.get("y") == obj["y"]
                           for o in shore["objects"]):
                    shore["objects"].append(obj)
            save(sp, shore)

        # --- manifest: register new maps + badge count (8 gyms + crest)
        mp = os.path.join(DATA, "regions", f"region_{rid}.json")
        manifest = load(mp)
        new_maps = [f"{rid}_crossroads"] + [f"{rid}_gym_{t}" for t in TYPES]
        if rid in ("verdantia", "aquilon"):
            new_maps.append(f"{rid}_league")
        for mid in new_maps:
            if mid not in manifest.get("maps", []):
                manifest.setdefault("maps", []).append(mid)
        manifest["badge_count"] = 9
        save(mp, manifest)

    save(os.path.join(DATA, "creatures", "creatures.json"), creatures_doc)
    save(os.path.join(DATA, "evolutions", "evolutions.json"), evolutions_doc)
    save(os.path.join(DATA, "trainers", "trainers.json"), trainers_doc)
    save(os.path.join(DATA, "encounters", "encounters.json"), encounters_doc)
    save(os.path.join(DATA, "quests", "quests.json"), quests_doc)
    n_creatures = len(creatures_doc["creatures"])
    n_trainers = len(trainers_doc["trainers"])
    print(f"League structure applied to 9 regions: 72 gyms, 36 elites, 9 champions.")
    print(f"Totals now: {n_creatures} species, {n_trainers} trainers, {len(quests_doc['quests'])} quests.")


if __name__ == "__main__":
    main()
