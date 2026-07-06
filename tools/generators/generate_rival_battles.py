#!/usr/bin/env python3
"""Rival battles — Corin becomes fightable at three points of the journey.

Until now Corin only talked. This adds three battles whose TEAM GROWS coherently
across the game (the same core creatures, evolving and gaining members — including
a Sunwisp caught in Solane between fights two and three), plus a side quest
tracking the rivalry. Lines are written to fit both story forks (true rival or
fallen to the Order). All content original. Idempotent (upsert by id).

Run after generate_expansion.py (needs the species). Then run check_chain.
Usage: python3 tools/generators/generate_rival_battles.py
"""
from __future__ import annotations

import json
import os

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA = os.path.join(ROOT, "data")

# (trainer_id, map, (x, y, facing, sight), ai, money, team [(species, level)], intro, defeat, victory)
BATTLES = [
    ("corin_rival_1", "verdantia_route", (2, 3, "right", 2), "basic", 300,
     [("chirpit", 7), ("nibbit", 8)],
     "Corin: Before the crests and the gray coats — just two rookies on a dirt road. Let's mark the start properly.",
     "Corin: Good. Whatever the road does to us later, remember it started fair.",
     "Corin: I'll take this one. You'll take others. That's how it's supposed to work."),
    ("corin_rival_2", "solane_wilds", (5, 1, "down", 2), "intermediate", 900,
     [("galecrest", 24), ("gnawber", 25), ("sunwisp", 26)],
     "Corin: The dunes strip away everything that isn't real. Caught this Sunwisp out here. Let's see what's left of us both.",
     "Corin: Still behind you, then. Fine. I've made peace with harder truths than that.",
     "Corin: Ahead of you, for once. Don't make me regret how much I enjoyed it."),
    ("corin_rival_3", "brume_wilds", (5, 1, "down", 2), "advanced", 2000,
     [("galecrest", 43), ("gnawber", 44), ("sunwisp", 45), ("murkfin", 46)],
     "Corin: Third time. Whatever else I've become since Umbra — this, us, the count between us — that part was always true.",
     "Corin: ...Keep that. Whatever happens on the steppe, keep the part of you that just won.",
     "Corin: The fen keeps what it beats. Come back for this one — I'll be here."),
]


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


def main():
    creatures = {c["id"]: c for c in load(os.path.join(DATA, "creatures", "creatures.json"))["creatures"]}
    tp = os.path.join(DATA, "trainers", "trainers.json")
    trainers_doc = load(tp)

    def moves_for(cid, lvl):
        spec = creatures[cid]
        m = [e["move"] for e in spec["learnset"] if e["level"] <= lvl][-4:]
        return m or [spec["learnset"][0]["move"]]

    for tid, map_id, (x, y, facing, sight), ai, money, team_spec, intro, defeat, victory in BATTLES:
        upsert(trainers_doc["trainers"], {
            "id": tid, "display_name": "Rival Corin", "sprite": "trainer_rival",
            "ai": ai, "boss": False, "reward_money": money,
            "dialogue_intro": intro, "dialogue_defeat": defeat, "dialogue_victory": victory,
            "team": [{"creature": cid, "level": lvl, "moves": moves_for(cid, lvl)}
                     for cid, lvl in team_spec],
        })
        mp = os.path.join(DATA, "regions", "maps", f"{map_id}.json")
        m = load(mp)
        if not any(o.get("trainer_id") == tid for o in m["objects"]):
            m["objects"].append({"type": "trainer", "x": x, "y": y, "trainer_id": tid,
                                 "sprite": "trainer_rival", "sight": sight, "facing": facing,
                                 "flag": f"beat_{tid}"})
            save(mp, m)
    save(tp, trainers_doc)

    # Side quest tracking the rivalry across the game.
    qp = os.path.join(DATA, "quests", "quests.json")
    qdoc = load(qp)
    upsert(qdoc["quests"], {
        "id": "side_rival_road", "display_name": "The Count Between Us",
        "category": "side", "auto_start": False,
        "start_condition": {"kind": "flag", "flag": "got_starter"},
        "description": "Corin keeps a running count of your battles. Meet him on the road — Verdantia, Solane, Brume — and settle it.",
        "objectives": [
            {"id": "obj_r1", "text": "Beat Corin on the Verdantia route.",
             "condition": {"kind": "flag", "flag": "beat_corin_rival_1"}},
            {"id": "obj_r2", "text": "Beat Corin in the Solane wilds.",
             "condition": {"kind": "flag", "flag": "beat_corin_rival_2"}},
            {"id": "obj_r3", "text": "Beat Corin in the Brume wilds.",
             "condition": {"kind": "flag", "flag": "beat_corin_rival_3"}},
        ],
        "rewards": [{"kind": "money", "amount": 3000},
                    {"kind": "item", "item": "max_revive", "quantity": 1}],
        "on_complete_flag": "rival_road_done",
        "on_complete_actions": [{"kind": "adjust_relationship", "npc": "corin", "delta": 2}],
    })
    save(qp, qdoc)
    print("Rival battles: 3 Corin fights placed (Verdantia route, Solane wilds, Brume wilds) "
          "+ side quest 'The Count Between Us'.")


if __name__ == "__main__":
    main()
