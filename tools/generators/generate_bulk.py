#!/usr/bin/env python3
"""Bulk generator — hundreds more original species + Battle Court trainers for XP.

For each of the nine regions this adds (idempotent, all ORIGINAL content):
- SPECIES_PER_REGION new species (about half in 2-stage evolution lines),
  distributed across all eight types and added to the region's wild table so
  there is far more variety (and XP) roaming the grass;
- COURTS_PER_REGION "Battle Court" training-hall maps, each packed with
  TRAINERS_PER_COURT optional trainers on isolated tiles (never blocking a
  path), wired into the region's Crossroads via new doors. These exist purely
  to grind experience: lots of beatable teams at the region's level band.

Tune the three constants to scale the world up or down. Run LAST, after
generate_regions.py, generate_expansion.py and generate_league.py.

Usage: python3 tools/generators/generate_bulk.py
"""
from __future__ import annotations

import json
import os

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA = os.path.join(ROOT, "data")

# ---- scale knobs -----------------------------------------------------------
SPECIES_PER_REGION = 200     # 9 regions -> +1800 species
COURTS_PER_REGION = 4        # training-hall maps per region
TRAINERS_PER_COURT = 72      # 9 * 4 * 72 = +2592 optional grind trainers
# ---------------------------------------------------------------------------
# Species and court ids are DETERMINISTIC (region-prefixed), and this generator
# prunes its own previous output (generation == "demo_g4") before regenerating,
# so it is fully idempotent even when the knobs above change.

TYPES = ["normal", "fire", "water", "grass", "electric", "earth", "wind", "mystic"]
REGION_ORDERS = {
    "verdantia": (1, 2), "aquilon": (2, 8), "cindral": (3, 14), "solane": (4, 20),
    "umbra": (5, 26), "ferrock": (6, 32), "brume": (7, 38), "lumen": (8, 44),
    "zephyra": (9, 50),
}
ROLE_BY_TYPE = {"normal": "balanced", "fire": "bruiser", "water": "guardian",
                "grass": "balanced", "electric": "swift", "earth": "guardian",
                "wind": "swift", "mystic": "sage"}
ROLES = {"swift": [50, 58, 44, 52, 46, 78], "bruiser": [58, 72, 55, 42, 48, 52],
         "guardian": [62, 52, 74, 44, 64, 34], "sage": [52, 40, 48, 74, 64, 56],
         "balanced": [56, 56, 56, 56, 56, 56]}
STAGE_MULT = [1.0, 1.4]
TYPE_POOLS = {
    "normal": ["tackle", "quick_jab", "rend", "battle_cry", "crush_blow"],
    "fire": ["ember_burst", "fire_fang", "flame_lash", "inferno_ray", "magma_beam"],
    "water": ["aqua_dart", "frost_jet", "tide_crash", "deluge", "tsunami"],
    "grass": ["leaf_cut", "root_snare", "vine_wrap", "bloom_burst", "solar_bloom"],
    "electric": ["spark_zap", "volt_lance", "thunder_clap", "storm_surge", "overcharge"],
    "earth": ["stone_toss", "sand_grind", "boulder_crush", "quake_stomp", "iron_guard"],
    "wind": ["gale_slash", "sky_talon", "cyclone_dive", "tempest", "hurricane"],
    "mystic": ["mind_ray", "astral_ram", "dream_pulse", "mind_shatter", "meditate"],
}
# Richer type -> ability rotation so generated species actually use the new talents.
TYPE_ABILITIES = {
    "normal": ["thick_hide", "steady_aim"], "fire": ["blaze_heart", "iron_wall"],
    "water": ["tide_soul", "spectral_veil"], "grass": ["overgrow", "sure_grip"],
    "electric": ["volt_soul", "static_skin"], "earth": ["quake_soul", "iron_wall"],
    "wind": ["gale_soul", "swift_foot"], "mystic": ["psy_soul", "keen_mind"],
}
# Big syllable space -> lots of clean unique names before any numeric fallback.
PRE = ["bram", "cinq", "dorn", "eld", "fen", "grim", "hollo", "iri", "jorv", "kest",
       "lum", "mor", "nyx", "orl", "pyr", "quill", "ryn", "sol", "tam", "umbr",
       "vex", "wyn", "yar", "zeph", "bal", "crev", "dusk", "ember", "frost", "glim"]
MID = ["a", "e", "i", "o", "u", "ae", "or", "en", "il", "ar"]
SUF = [["ling", "kit", "et", "pip", "let", "im"], ["fang", "claw", "wing", "mane", "horn", "back"]]

CLASS_TITLES = ["Ace", "Veteran", "Ranger", "Brawler", "Adept", "Nomad", "Sentinel",
                "Duelist", "Trapper", "Warden", "Scrapper", "Vanguard", "Zealot", "Rover"]
FIRST_NAMES = ["Aldo", "Bex", "Cira", "Dov", "Enna", "Faro", "Gale", "Hux", "Ivo", "Juno",
               "Kip", "Lira", "Mox", "Nell", "Osk", "Pell", "Quin", "Rhea", "Sten", "Tarn",
               "Uma", "Vek", "Wex", "Xan", "Yol", "Zara"]


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


def make_name(rid, slot, stage):
    """Deterministic, region-prefixed, unique species id for (region, slot, stage)."""
    p = PRE[slot % len(PRE)]
    m = MID[(slot // len(PRE)) % len(MID)]
    s = SUF[stage][(slot // (len(PRE) * len(MID))) % len(SUF[stage])]
    return f"{rid[:2]}{p}{m}{s}"


def learnset(types, lo, stage):
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


def species_rec(sid, name, types, region, lo, order, stage, evolves):
    role = ROLE_BY_TYPE[types[0]]
    growth = 1.0 + 0.02 * (order - 1)
    base = ROLES[role]
    hp, atk, dfn, spa, spd, spe = [min(165, int(v * STAGE_MULT[stage] * growth)) for v in base]
    return {
        "id": sid, "display_name": name,
        "description": f"A {'/'.join(types)}-attuned creature roaming the {region.capitalize()} region.",
        "generation": "demo_g4", "origin_region": region, "types": list(types),
        "base_stats": {"hp": hp, "attack": atk, "defense": dfn,
                       "sp_attack": spa, "sp_defense": spd, "speed": spe},
        "ev_yield": {"speed" if role == "swift" else "hp": 1 + stage},
        "exp_curve": "medium_fast", "gender_ratio": 0.5,
        "abilities": TYPE_ABILITIES.get(types[0], ["thick_hide"]),
        "capture_rate": 120 if stage == 0 else 60, "rarity": "common" if stage == 0 else "uncommon",
        "breeding_groups": ["field"], "learnset": learnset(list(types), lo, stage),
        "evolves_to": evolves, "forms": [],
    }


def court_map(rid, region_name, idx, n_trainers, trainer_ids):
    """A hall sized to hold the trainers on isolated even-coord pillars, aisles between.
    Interior even-coord slots = ((W-2)//2) * ((H-2)//2); size up until they fit."""
    W, H = 19, 16
    while ((W - 2) // 2) * ((H - 2) // 2) < n_trainers + 2:
        if W <= H:
            W += 2
        else:
            H += 2
    ex = W // 2  # entrance column
    rows = []
    for y in range(H):
        if y == 0 or y == H - 1:
            rows.append("#" * W)
        else:
            rows.append("#" + "." * (W - 2) + "#")
    # entrance door at bottom middle
    rows[H - 1] = rows[H - 1][:ex] + "D" + rows[H - 1][ex + 1:]
    objects = [
        {"type": "spawn", "id": "entrance", "x": ex, "y": H - 2},
        {"type": "door", "x": ex, "y": H - 1, "to_map": f"{rid}_crossroads",
         "to_spawn": f"from_court_{idx}"},
        {"type": "sign", "x": 2, "y": 1,
         "text": f"{region_name} Battle Court {idx} — endless sparring for the ambitious."},
    ]
    slots = [(x, y) for y in range(2, H - 2, 2) for x in range(2, W - 2, 2)]
    slots = [s for s in slots if not (s[0] == ex and s[1] >= H - 4)]  # keep entrance column clear
    for i in range(min(n_trainers, len(slots), len(trainer_ids))):
        x, y = slots[i]
        objects.append({"type": "trainer", "x": x, "y": y, "trainer_id": trainer_ids[i],
                        "sprite": "trainer_ace", "sight": 1, "facing": "down",
                        "flag": f"beat_{trainer_ids[i]}"})
    return {
        "$schema_version": 1, "id": f"{rid}_court_{idx}",
        "display_name": f"{region_name} Battle Court {idx}", "region": rid,
        "bgm": "town", "tile_size": 32,
        "legend": {"#": "wall", ".": "floor", "D": "door"}, "rows": rows, "objects": objects,
    }


def main():
    creatures_doc = load(os.path.join(DATA, "creatures", "creatures.json"))
    evolutions_doc = load(os.path.join(DATA, "evolutions", "evolutions.json"))
    trainers_doc = load(os.path.join(DATA, "trainers", "trainers.json"))
    encounters_doc = load(os.path.join(DATA, "encounters", "encounters.json"))

    # Prune this generator's previous output so re-runs (incl. knob changes) are clean.
    creatures_doc["creatures"] = [c for c in creatures_doc["creatures"]
                                  if c.get("generation") != "demo_g4"]
    live_ids = {c["id"] for c in creatures_doc["creatures"]}
    # Drop evolution rules whose source creature no longer exists (orphaned demo_g4);
    # the ones we recreate below are re-added with identical ids.
    evolutions_doc["evolutions"] = [e for e in evolutions_doc["evolutions"]
                                    if e.get("from") in live_ids]

    region_species = {}
    slot = 0
    for rid, (order, lo) in REGION_ORDERS.items():
        pool_ids = []
        n_lines = SPECIES_PER_REGION // 3   # ~1/3 are 2-stage lines (2 species each)
        n_singles = SPECIES_PER_REGION - n_lines * 2
        ti = 0
        # two-stage lines
        for _ in range(n_lines):
            types = [TYPES[ti % 8]]
            if ti % 3 == 0:
                types = [TYPES[ti % 8], TYPES[(ti + 3) % 8]]
            ti += 1
            base_id = make_name(rid, slot, 0)
            evo_id = make_name(rid, slot, 1)
            slot += 1
            upsert(creatures_doc["creatures"],
                   species_rec(base_id, base_id.capitalize(), types, rid, lo, order, 0, [evo_id]))
            upsert(creatures_doc["creatures"],
                   species_rec(evo_id, evo_id.capitalize(), types, rid, lo, order, 1, []))
            upsert(evolutions_doc["evolutions"],
                   {"id": f"evo_{base_id}", "from": base_id, "to": evo_id,
                    "condition": {"kind": "level_up", "level": min(58, lo + 12)}})
            pool_ids += [base_id, evo_id]
        # singles
        for _ in range(n_singles):
            types = [TYPES[ti % 8]]
            ti += 1
            sid = make_name(rid, slot, 0)
            slot += 1
            upsert(creatures_doc["creatures"],
                   species_rec(sid, sid.capitalize(), types, rid, lo, order, 0, []))
            pool_ids.append(sid)
        region_species[rid] = pool_ids

    # Trim any encounter entries that referenced now-removed demo_g4 species.
    valid_ids = {c["id"] for c in creatures_doc["creatures"]}
    for tbl in encounters_doc["tables"]:
        tbl["entries"] = [e for e in tbl["entries"] if e.get("creature") in valid_ids]

        # wild table: add every new stage-1 / single as a light-weight spawn
        tbl = next((t for t in encounters_doc["tables"] if t.get("region") == rid), None)
        if tbl is not None:
            existing = {e["creature"] for e in tbl["entries"]}
            spec_by_id = {c["id"]: c for c in creatures_doc["creatures"]}
            for sid in pool_ids:
                if sid in existing:
                    continue
                if spec_by_id[sid]["evolves_to"] or spec_by_id[sid]["rarity"] == "common":
                    tbl["entries"].append({"creature": sid, "weight": 4,
                                           "level_min": lo, "level_max": lo + 7,
                                           "rarity": "common"})

    # Battle Courts: many optional trainers per region for grinding XP.
    # pre-evolution map so no court trainer fields an under-leveled evolved form
    pre_evo, min_form_lvl = {}, {}
    for e in evolutions_doc["evolutions"]:
        if e.get("to"):
            pre_evo[e["to"]] = e.get("from")
            min_form_lvl[e["to"]] = max(min_form_lvl.get(e["to"], 1),
                                        int(e.get("condition", {}).get("level", 1)))
    court_total = 0
    for rid, (order, lo) in REGION_ORDERS.items():
        region_name = rid.capitalize()
        spec_by_id = {c["id"]: c for c in creatures_doc["creatures"]}
        pool = [s for s in region_species[rid]]
        for court_idx in range(1, COURTS_PER_REGION + 1):
            trainer_ids = []
            for t_i in range(TRAINERS_PER_COURT):
                gidx = (court_idx - 1) * TRAINERS_PER_COURT + t_i
                tid = f"{rid}_court{court_idx}_t{t_i}"
                trainer_ids.append(tid)
                # 2-3 creatures from the region pool at the band level
                size = 2 + (gidx % 2)
                team = []
                for k in range(size):
                    sid = pool[(gidx * 3 + k) % len(pool)]
                    lvl = lo + 2 + (gidx % 5) + k
                    # never field an evolved form below its evolution level
                    while min_form_lvl.get(sid, 1) > lvl and sid in pre_evo:
                        sid = pre_evo[sid]
                    spec = spec_by_id[sid]
                    moves = [e["move"] for e in spec["learnset"] if e["level"] <= lvl][-4:]
                    team.append({"creature": sid, "level": lvl,
                                 "moves": moves or [spec["learnset"][0]["move"]]})
                cls = CLASS_TITLES[gidx % len(CLASS_TITLES)]
                fn = FIRST_NAMES[(order * 7 + gidx) % len(FIRST_NAMES)]
                upsert(trainers_doc["trainers"], {
                    "id": tid, "display_name": f"{cls} {fn}",
                    "sprite": "trainer_ace", "ai": "intermediate", "boss": False,
                    "reward_money": 60 + 25 * order,
                    "dialogue_intro": f"{cls} {fn}: Here to train? Then let's make it count!",
                    "dialogue_defeat": f"{cls} {fn}: Good match — you're getting stronger!",
                    "dialogue_victory": f"{cls} {fn}: Come back when you've trained more.",
                    "team": team,
                })
            save(os.path.join(DATA, "regions", "maps", f"{rid}_court_{court_idx}.json"),
                 court_map(rid, region_name, court_idx, TRAINERS_PER_COURT, trainer_ids))
            court_total += TRAINERS_PER_COURT

        # Wire courts into the Crossroads (add doors on the free wall tiles).
        cp = os.path.join(DATA, "regions", "maps", f"{rid}_crossroads.json")
        cross = load(cp)
        # free interior wall tiles: left col rows 6-7, right col rows 2 & 6
        wiring = [(0, 6, "from_court_1", 1, 6), (15, 2, "from_court_2", 14, 2),
                  (15, 6, "from_court_3", 14, 6), (0, 7, "from_court_4", 1, 7)]
        for ci in range(COURTS_PER_REGION):
            dx, dy, spawn_id, sx, sy = wiring[ci]
            row = cross["rows"][dy]
            cross["rows"][dy] = row[:dx] + "D" + row[dx + 1:]
            for obj in [
                {"type": "door", "x": dx, "y": dy, "to_map": f"{rid}_court_{ci + 1}",
                 "to_spawn": "entrance"},
                {"type": "spawn", "id": spawn_id, "x": sx, "y": sy},
            ]:
                if not any(o.get("type") == obj["type"] and o.get("x") == obj["x"]
                           and o.get("y") == obj["y"] for o in cross["objects"]):
                    cross["objects"].append(obj)
        save(cp, cross)

        # register court maps in the manifest
        mp = os.path.join(DATA, "regions", f"region_{rid}.json")
        manifest = load(mp)
        for ci in range(1, COURTS_PER_REGION + 1):
            mid = f"{rid}_court_{ci}"
            if mid not in manifest.get("maps", []):
                manifest.setdefault("maps", []).append(mid)
        save(mp, manifest)

    save(os.path.join(DATA, "creatures", "creatures.json"), creatures_doc)
    save(os.path.join(DATA, "evolutions", "evolutions.json"), evolutions_doc)
    save(os.path.join(DATA, "trainers", "trainers.json"), trainers_doc)
    save(os.path.join(DATA, "encounters", "encounters.json"), encounters_doc)
    print(f"Bulk applied: +{SPECIES_PER_REGION * 9} species, "
          f"+{court_total} court trainers ({COURTS_PER_REGION} courts x "
          f"{TRAINERS_PER_COURT}/region).")
    print(f"Totals now: {len(creatures_doc['creatures'])} species, "
          f"{len(trainers_doc['trainers'])} trainers.")


if __name__ == "__main__":
    main()
