#!/usr/bin/env python3
"""Validate all game data in data/ before launching the game.

This is the authoritative pre-flight check and mirrors the checks in
scripts/autoload/data_registry.gd::validate(). It is engine-independent so it can
run in CI or a plain shell:

    python3 tools/validators/validate_data.py

Exit code 0 == all data valid; 1 == errors found (printed).
"""
from __future__ import annotations

import json
import os
import sys
from glob import glob

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data")

VALID_CURVES = {"fast", "medium_fast", "medium_slow", "slow"}
VALID_CATEGORIES = {"physical", "special", "status"}
VALID_AI = {"basic", "intermediate", "advanced"}
STAT_KEYS = ["hp", "attack", "defense", "sp_attack", "sp_defense", "speed"]


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def index(records, key, errors, label):
    out = {}
    for r in records:
        k = r.get(key)
        if k in out:
            errors.append(f"Duplicate id '{k}' in {label}.")
        out[k] = r
    return out


def main() -> int:
    errors: list[str] = []

    types_data = load(os.path.join(DATA, "types", "types.json"))
    valid_types = {t["id"] for t in types_data.get("types", [])}

    for atk, row in types_data.get("chart", {}).items():
        if atk not in valid_types:
            errors.append(f"Type chart references unknown attacking type '{atk}'.")
        for dfn in row:
            if dfn not in valid_types:
                errors.append(f"Type chart references unknown defending type '{dfn}'.")

    creatures = index(load(os.path.join(DATA, "creatures", "creatures.json"))["creatures"], "id", errors, "creatures")
    moves = index(load(os.path.join(DATA, "moves", "moves.json"))["moves"], "id", errors, "moves")
    abilities = index(load(os.path.join(DATA, "abilities", "abilities.json"))["abilities"], "id", errors, "abilities")
    items = index(load(os.path.join(DATA, "items", "items.json"))["items"], "id", errors, "items")
    evolutions = load(os.path.join(DATA, "evolutions", "evolutions.json"))["evolutions"]
    enc_tables = index(load(os.path.join(DATA, "encounters", "encounters.json"))["tables"], "id", errors, "encounters")
    trainers = index(load(os.path.join(DATA, "trainers", "trainers.json"))["trainers"], "id", errors, "trainers")
    quests = index(load(os.path.join(DATA, "quests", "quests.json"))["quests"], "id", errors, "quests")

    # moves
    for mid, mv in moves.items():
        if mv.get("type") not in valid_types:
            errors.append(f"Move '{mid}' has unknown type '{mv.get('type')}'.")
        if mv.get("category") not in VALID_CATEGORIES:
            errors.append(f"Move '{mid}' has invalid category '{mv.get('category')}'.")
        if not (0 <= mv.get("accuracy", 100) <= 100):
            errors.append(f"Move '{mid}' has invalid accuracy {mv.get('accuracy')}.")

    # creatures
    for cid, c in creatures.items():
        for t in c.get("types", []):
            if t not in valid_types:
                errors.append(f"Creature '{cid}' has unknown type '{t}'.")
        if not (1 <= len(c.get("types", [])) <= 2):
            errors.append(f"Creature '{cid}' must have 1 or 2 types.")
        for ab in c.get("abilities", []):
            if ab not in abilities:
                errors.append(f"Creature '{cid}' references unknown ability '{ab}'.")
        for entry in c.get("learnset", []):
            if entry.get("move") not in moves:
                errors.append(f"Creature '{cid}' learnset references unknown move '{entry.get('move')}'.")
        for k in STAT_KEYS:
            v = c.get("base_stats", {}).get(k, -1)
            if not (1 <= v <= 255):
                errors.append(f"Creature '{cid}' has invalid base stat {k}={v}.")
        if c.get("exp_curve") not in VALID_CURVES:
            errors.append(f"Creature '{cid}' has unknown exp_curve '{c.get('exp_curve')}'.")
        for target in c.get("evolves_to", []):
            if target not in creatures:
                errors.append(f"Creature '{cid}' evolves_to unknown creature '{target}'.")

    # evolution reference + cycle detection
    for e in evolutions:
        if e.get("from") not in creatures:
            errors.append(f"Evolution '{e.get('id')}' from unknown creature '{e.get('from')}'.")
        if e.get("to") not in creatures:
            errors.append(f"Evolution '{e.get('id')}' to unknown creature '{e.get('to')}'.")
    errors.extend(detect_cycles(creatures))

    # encounters
    for tid, tbl in enc_tables.items():
        for entry in tbl.get("entries", []):
            if entry.get("creature") not in creatures:
                errors.append(f"Encounter table '{tid}' references unknown creature '{entry.get('creature')}'.")
            if entry.get("level_min", 1) > entry.get("level_max", 1):
                errors.append(f"Encounter table '{tid}' entry has level_min > level_max.")

    # trainers
    for tid, tr in trainers.items():
        if tr.get("ai") not in VALID_AI:
            errors.append(f"Trainer '{tid}' has invalid ai tier '{tr.get('ai')}'.")
        for m in tr.get("team", []):
            if m.get("creature") not in creatures:
                errors.append(f"Trainer '{tid}' references unknown creature '{m.get('creature')}'.")
            for mv in m.get("moves", []):
                if mv not in moves:
                    errors.append(f"Trainer '{tid}' member uses unknown move '{mv}'.")

    # regions + maps
    region_files = glob(os.path.join(DATA, "regions", "region_*.json"))
    regions = {}
    for rf in region_files:
        r = load(rf)
        regions[r["id"]] = r
    map_files = glob(os.path.join(DATA, "regions", "maps", "*.json"))
    maps = {}
    for mf in map_files:
        m = load(mf)
        maps[m["id"]] = m

    for rid, reg in regions.items():
        if reg.get("starting_map") not in maps:
            errors.append(f"Region '{rid}' starting_map '{reg.get('starting_map')}' does not exist.")
        for mid in reg.get("maps", []):
            if mid not in maps:
                errors.append(f"Region '{rid}' lists unknown map '{mid}'.")
        et = reg.get("regional_rules", {}).get("encounter_table", "")
        if et and et not in enc_tables:
            errors.append(f"Region '{rid}' encounter_table '{et}' does not exist.")
        for nr in reg.get("next_regions", []):
            if nr not in regions:
                errors.append(f"Region '{rid}' next_regions references unknown region '{nr}'.")

    for mid, m in maps.items():
        # grid sanity: all rows same length, every legend char used exists
        rows = m.get("rows", [])
        legend = m.get("legend", {})
        width = len(rows[0]) if rows else 0
        for r_i, row in enumerate(rows):
            if len(row) != width:
                errors.append(f"Map '{mid}' row {r_i} width {len(row)} != {width}.")
            for ch in row:
                if ch not in legend:
                    errors.append(f"Map '{mid}' uses tile '{ch}' missing from legend.")
        for obj in m.get("objects", []):
            k = obj.get("type")
            if k in ("warp", "door"):
                if obj.get("to_map") not in maps:
                    errors.append(f"Map '{mid}' {k} targets unknown map '{obj.get('to_map')}'.")
            elif k == "trainer" and obj.get("trainer_id") not in trainers:
                errors.append(f"Map '{mid}' trainer references unknown trainer '{obj.get('trainer_id')}'.")
            elif k == "item" and obj.get("item") not in items:
                errors.append(f"Map '{mid}' item references unknown item '{obj.get('item')}'.")
            elif k == "encounter_zone" and obj.get("table") not in enc_tables:
                errors.append(f"Map '{mid}' encounter_zone references unknown table '{obj.get('table')}'.")

    # quests
    for qid, q in quests.items():
        for rw in q.get("rewards", []):
            if rw.get("kind") == "item" and rw.get("item") not in items:
                errors.append(f"Quest '{qid}' rewards unknown item '{rw.get('item')}'.")
            if rw.get("kind") == "unlock_region" and rw.get("region") not in regions:
                errors.append(f"Quest '{qid}' unlocks unknown region '{rw.get('region')}'.")

    # report
    print(f"Validated: {len(creatures)} creatures, {len(moves)} moves, {len(items)} items, "
          f"{len(abilities)} abilities, {len(trainers)} trainers, {len(regions)} regions, {len(maps)} maps, "
          f"{len(quests)} quests, {len(valid_types)} types.")
    if errors:
        print(f"\n✗ {len(errors)} validation error(s):")
        for e in errors:
            print("  -", e)
        return 1
    print("✓ All data valid.")
    return 0


def detect_cycles(creatures) -> list[str]:
    errors = []
    for start in creatures:
        seen = set()
        stack = list(creatures[start].get("evolves_to", []))
        while stack:
            cur = stack.pop()
            if cur == start:
                errors.append(f"Circular evolution detected involving '{start}'.")
                break
            if cur in seen:
                continue
            seen.add(cur)
            stack.extend(creatures.get(cur, {}).get("evolves_to", []))
    return errors


if __name__ == "__main__":
    sys.exit(main())
