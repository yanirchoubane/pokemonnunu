#!/usr/bin/env python3
"""Gameplay linter — battle-logic invariants over the whole trainer/wild dataset.

Checks things the schema validator can't see but a player would:
  E1. every trainer team member knows at least one DAMAGING move
      (a status-only boss stalls the battle into Struggle attrition);
  E2. no trainer move is absent from the species' learnset (unknown techniques);
  E3. no member uses an EVOLVED form below the level that evolution requires
      (a level-16 final form the player can't obtain until 32 breaks coherence);
  E4. member levels within [2, 100];
  E5. every wild-encounter species has a damaging move available at level_min.
Warnings (reported, non-fatal):
  W1. a trainer move learned above the member's level (tutored — tolerated).

Exit 1 on any error. Run any time: python3 tools/validators/lint_gameplay.py
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA = os.path.join(ROOT, "data")


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    creatures = {c["id"]: c for c in load("creatures/creatures.json")["creatures"]}
    moves = {m["id"]: m for m in load("moves/moves.json")["moves"]}
    trainers = load("trainers/trainers.json")["trainers"]
    tables = load("encounters/encounters.json")["tables"]
    evolutions = load("evolutions/evolutions.json")["evolutions"]

    damaging = {mid for mid, m in moves.items() if int(m.get("power", 0)) > 0}
    # species -> minimum level at which this FORM can legally exist
    # (the level of the evolution that produces it; base forms = 1)
    min_form_level = {cid: 1 for cid in creatures}
    for e in evolutions:
        to = e.get("to")
        lvl = int(e.get("condition", {}).get("level", 1))
        if to in min_form_level:
            min_form_level[to] = max(min_form_level[to], lvl)

    errors, warnings = [], 0
    for t in trainers:
        tid = t["id"]
        for m in t.get("team", []):
            cid, lvl = m.get("creature"), int(m.get("level", 0))
            spec = creatures.get(cid)
            if spec is None:
                continue  # schema validator's job
            learnable = {e["move"]: int(e["level"]) for e in spec.get("learnset", [])}
            mvs = m.get("moves", [])
            if not any(mv in damaging for mv in mvs):
                errors.append(f"E1 {tid}: {cid} L{lvl} has no damaging move ({mvs})")
            for mv in mvs:
                if mv not in learnable:
                    errors.append(f"E2 {tid}: {cid} can never learn '{mv}'")
                elif learnable[mv] > lvl:
                    warnings += 1
            if lvl < min_form_level.get(cid, 1):
                errors.append(f"E3 {tid}: {cid} at L{lvl} but that form requires L{min_form_level[cid]}")
            if not (2 <= lvl <= 100):
                errors.append(f"E4 {tid}: {cid} at illegal level {lvl}")

    for tbl in tables:
        for e in tbl.get("entries", []):
            cid, lo = e.get("creature"), int(e.get("level_min", 1))
            spec = creatures.get(cid)
            if spec is None:
                continue
            avail = [x["move"] for x in spec.get("learnset", []) if int(x["level"]) <= lo]
            if not any(mv in damaging for mv in avail):
                errors.append(f"E5 {tbl['id']}: wild {cid} at L{lo} has no damaging move")

    if errors:
        print(f"✗ {len(errors)} gameplay error(s) ({warnings} above-level move warnings):")
        seen_kinds = {}
        for e in errors:
            seen_kinds[e[:2]] = seen_kinds.get(e[:2], 0) + 1
        for k, n in sorted(seen_kinds.items()):
            print(f"  {k}: {n}")
        for e in errors[:25]:
            print("  -", e)
        if len(errors) > 25:
            print(f"  ... and {len(errors) - 25} more")
        return 1
    print(f"✓ Gameplay lint clean: every trainer member fights, knows only learnable "
          f"moves, and uses level-legal forms ({warnings} tolerated above-level moves).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
