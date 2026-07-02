#!/usr/bin/env python3
"""Bulk-author creatures or moves from a CSV spreadsheet into the engine's JSON shape.

Usage:
    python3 tools/importers/csv_to_json.py creatures input.csv > data/creatures/new.json
    python3 tools/importers/csv_to_json.py moves     input.csv > data/moves/new.json

Then re-run the validator:
    python3 tools/validators/validate_data.py

Creatures CSV columns (header row required):
    id,display_name,types,hp,attack,defense,sp_attack,sp_defense,speed,
    exp_curve,capture_rate,abilities,learnset,evolves_to,rarity,origin_region,description
  - types / abilities / evolves_to: '|'-separated (e.g. "fire|wind")
  - learnset: '|'-separated "level:move_id" pairs (e.g. "1:tackle|8:flame_lash")

Moves CSV columns:
    id,display_name,type,category,power,accuracy,priority,pp,description,effects
  - effects: '|'-separated "kind:key=val,key=val" (e.g.
      "damage|apply_status:status=burn,chance=0.1,target=enemy")

This importer only shapes data; it does not validate references — the validator does.
"""
from __future__ import annotations

import csv
import json
import sys


def _split(s, sep="|"):
    return [x for x in (s or "").split(sep) if x != ""]


def creatures(path):
    out = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            learn = []
            for pair in _split(row.get("learnset", "")):
                lvl, move = pair.split(":")
                learn.append({"level": int(lvl), "move": move})
            out.append({
                "id": row["id"].strip(),
                "display_name": row.get("display_name", row["id"]).strip(),
                "description": row.get("description", "").strip(),
                "generation": row.get("generation", "imported").strip(),
                "origin_region": row.get("origin_region", "").strip(),
                "types": _split(row.get("types", "")),
                "base_stats": {k: int(row[k]) for k in
                               ["hp", "attack", "defense", "sp_attack", "sp_defense", "speed"]},
                "ev_yield": {},
                "exp_curve": row.get("exp_curve", "medium_fast").strip(),
                "gender_ratio": float(row.get("gender_ratio", 0.5) or 0.5),
                "abilities": _split(row.get("abilities", "")),
                "capture_rate": int(row.get("capture_rate", 45) or 45),
                "rarity": row.get("rarity", "common").strip(),
                "breeding_groups": _split(row.get("breeding_groups", "")),
                "learnset": learn,
                "evolves_to": _split(row.get("evolves_to", "")),
                "forms": [],
            })
    return {"$schema_version": 1, "creatures": out}


def _effect(token):
    if ":" in token:
        kind, rest = token.split(":", 1)
    else:
        kind, rest = token, ""
    eff = {"kind": kind}
    for kv in _split(rest, ","):
        k, v = kv.split("=")
        if v.replace(".", "", 1).isdigit():
            v = float(v) if "." in v else int(v)
        eff[k] = v
    return eff


def moves(path):
    out = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out.append({
                "id": row["id"].strip(),
                "display_name": row.get("display_name", row["id"]).strip(),
                "type": row["type"].strip(),
                "category": row.get("category", "physical").strip(),
                "power": int(row.get("power", 0) or 0),
                "accuracy": int(row.get("accuracy", 100) or 100),
                "priority": int(row.get("priority", 0) or 0),
                "pp": int(row.get("pp", 10) or 10),
                "description": row.get("description", "").strip(),
                "effects": [_effect(t) for t in _split(row.get("effects", "damage"))],
            })
    return {"$schema_version": 1, "moves": out}


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("creatures", "moves"):
        print(__doc__)
        return 2
    kind, path = sys.argv[1], sys.argv[2]
    data = creatures(path) if kind == "creatures" else moves(path)
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
