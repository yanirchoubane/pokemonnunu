#!/usr/bin/env python3
"""Story ownership — pins the narrative cast, quest shape and ending order.

Everything the story arc needs that OTHER generators would otherwise overwrite
lives here, so the pipeline always converges:
- map placements: Corin on every Crossroads, the defector Verel at Cindral
  Gate, Lieutenant Mourn in Duskbell Grove, the Archon + finale mask in the
  Zephyra wilds;
- trainer records: the named Hollow cell (Vole / Cinder / Wisp) and Lieutenant
  Mourn (generate_expansion writes generic agents — this pass renames them);
- quest shape: the Hollow Order quest gains the Lieutenant step and completes
  on the finale CHOICE (hollow_resolved), not the raw Archon battle;
- endings: upserts the choice-driven endings and enforces the ONE canonical
  first-match-wins order.

Run after generate_places.py, before nothing in particular — it must simply be
the LAST writer of story data (run_all.py guarantees that). Idempotent.
Usage: python3 tools/generators/generate_story_placements.py
"""
from __future__ import annotations

import json
import os

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA = os.path.join(ROOT, "data")
REGIONS = ["verdantia", "aquilon", "cindral", "solane", "umbra",
           "ferrock", "brume", "lumen", "zephyra"]

# The one canonical ending order (first matching condition wins).
ENDING_ORDER = ["ending_nine_crests", "ending_rivals_true", "ending_order_mercy",
                "ending_order_justice", "ending_order_undone", "ending_champion",
                "ending_bonds", "ending_lone_pioneer"]

STORY_ENDINGS = [
    {"id": "ending_rivals_true", "title": "Rivals to the End",
     "condition": {"kind": "all", "conditions": [
         {"kind": "flag", "flag": "quest_hollow_done"},
         {"kind": "relationship_at_least", "npc": "corin", "at_least": 4}]},
     "lines": [
         "Corin meets you on the Zephyra steppe, grinning through the wind.",
         "\"Start to finish, ${player} — nine regions, one Order broken, and I never fell behind.\"",
         "Two rivals, one unbroken road. Professor Maple's report has two names on the cover."]},
    {"id": "ending_order_mercy", "title": "The Hand You Didn't Raise",
     "condition": {"kind": "var_equals", "var": "order_end", "value": "mercy"},
     "lines": [
         "You gave the Archon a road back instead of a fall.",
         "The gray coats trade debt-ledgers for trail-maps, guiding travelers they once robbed.",
         "Mercy, it turns out, hollows nothing. It fills."]},
    {"id": "ending_order_justice", "title": "Ledgers to Ash",
     "condition": {"kind": "var_equals", "var": "order_end", "value": "justice"},
     "lines": [
         "The Order's debts burn on the steppe until only clean wind remains.",
         "From Verdantia to Zephyra, no trainer flinches at a gray coat again.",
         "You gave the roads back. That is a Champion's truest badge."]},
]

AGENTS = {
    "hollow_agent_cindral": ("Hollow Agent Vole",
        "Vole: The Order collects what trainers hoard. Your team is a very full ledger.",
        "Vole: ...Report to the Archon that Cindral's road has teeth now."),
    "hollow_agent_ferrock": ("Hollow Agent Cinder",
        "Cinder: Vole warned us about you. The Order does not forgive interest unpaid.",
        "Cinder: Two of us down. The Lieutenant will not be so easily read."),
    "hollow_agent_lumen": ("Hollow Agent Wisp",
        "Wisp: You've unravelled half our cell. But the Archon's debt always comes due.",
        "Wisp: Go north, then. The Archon is done sending others."),
}


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(p, d):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
        f.write("\n")


def ensure(map_id: str, obj: dict, key: str) -> bool:
    mp = os.path.join(DATA, "regions", "maps", f"{map_id}.json")
    m = load(mp)
    if any(o.get(key) == obj[key] for o in m["objects"]):
        return False
    m["objects"].append(obj)
    save(mp, m)
    return True


def main():
    # ---------------------------------------------------------- placements
    placed = 0
    for rid in REGIONS:
        placed += ensure(f"{rid}_crossroads",
                         {"type": "npc", "x": 7, "y": 6, "npc_id": "corin",
                          "sprite": "npc_rival", "dialog_id": "corin_road"}, "npc_id")
    placed += ensure("cindral_gate",
                     {"type": "npc", "x": 6, "y": 4, "npc_id": "defector",
                      "sprite": "npc_watcher", "dialog_id": "hollow_defector"}, "npc_id")
    placed += ensure("umbra_landmark",
                     {"type": "trainer", "x": 8, "y": 6, "trainer_id": "hollow_lieutenant",
                      "sprite": "trainer_hollow", "sight": 2, "facing": "left",
                      "flag": "beat_hollow_lieutenant"}, "trainer_id")
    placed += ensure("zephyra_wilds",
                     {"type": "trainer", "x": 4, "y": 1, "trainer_id": "hollow_archon",
                      "sprite": "trainer_archon", "sight": 2, "facing": "down",
                      "flag": "beat_hollow_archon"}, "trainer_id")
    placed += ensure("zephyra_wilds",
                     {"type": "npc", "x": 6, "y": 3, "npc_id": "archon_mask",
                      "sprite": "trainer_archon", "dialog_id": "archon_finale"}, "npc_id")

    # ------------------------------------------------------------ trainers
    tp = os.path.join(DATA, "trainers", "trainers.json")
    tdoc = load(tp)
    by = {t["id"]: t for t in tdoc["trainers"]}
    for tid, (name, intro, defeat) in AGENTS.items():
        if tid in by:
            by[tid]["display_name"] = name
            by[tid]["dialogue_intro"] = intro
            by[tid]["dialogue_defeat"] = defeat
    # Lieutenant Mourn (record may be absent on a clean-room run).
    creatures = load(os.path.join(DATA, "creatures", "creatures.json"))["creatures"]
    umbra_mons = [c for c in creatures if c.get("origin_region") == "umbra"
                  and c.get("rarity") != "legendary"][:3]

    def mv(spec, lvl):
        m = [e["move"] for e in spec["learnset"] if e["level"] <= lvl][-4:]
        return m or [spec["learnset"][0]["move"]]

    lo = 26
    lieutenant = {
        "id": "hollow_lieutenant", "display_name": "Hollow Lieutenant Mourn",
        "sprite": "trainer_hollow", "ai": "advanced", "boss": True, "boss_scaling": "limited",
        "reward_money": 2200,
        "dialogue_intro": "Mourn: The agents were arithmetic. I am the whole equation. The Order remembers every debt — including mine.",
        "dialogue_defeat": "Mourn: ...I joined to stop feeling hollow. It only spread. Go on. The Archon is just a tireder version of me.",
        "dialogue_victory": "Mourn: The ledger balances. As it always does.",
        "team": [{"creature": s["id"], "level": lo + 8 + i, "moves": mv(s, lo + 8 + i)}
                 for i, s in enumerate(umbra_mons)],
    }
    if "hollow_lieutenant" in by:
        by["hollow_lieutenant"].update(lieutenant)
    else:
        tdoc["trainers"].append(lieutenant)
    save(tp, tdoc)

    # -------------------------------------------------------------- quests
    qp = os.path.join(DATA, "quests", "quests.json")
    qdoc = load(qp)
    for quest in qdoc["quests"]:
        if quest["id"] != "main_hollow_order":
            continue
        ids = [o["id"] for o in quest["objectives"]]
        if "obj_lieutenant" not in ids:
            quest["objectives"].insert(3, {
                "id": "obj_lieutenant",
                "text": "Defeat Hollow Lieutenant Mourn in Duskbell Grove.",
                "condition": {"kind": "flag", "flag": "beat_hollow_lieutenant"}})
        for obj in quest["objectives"]:
            if obj["id"] == "obj_archon":
                obj["text"] = "Confront the Hollow Archon and decide the Order's fate."
                obj["condition"] = {"kind": "flag", "flag": "hollow_resolved"}
    save(qp, qdoc)

    # ------------------------------------------------------------- endings
    ep = os.path.join(DATA, "endings", "endings.json")
    edoc = load(ep)
    existing = {e["id"]: e for e in edoc["endings"]}
    for e in STORY_ENDINGS:
        existing[e["id"]] = e
    edoc["endings"] = ([existing[i] for i in ENDING_ORDER if i in existing]
                       + [v for k, v in existing.items() if k not in ENDING_ORDER])
    save(ep, edoc)

    print(f"Story ownership applied: {placed} placements inserted, agents named, "
          f"Lieutenant pinned, Hollow quest shaped, endings ordered canonically.")


if __name__ == "__main__":
    main()
