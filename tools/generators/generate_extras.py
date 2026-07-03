#!/usr/bin/env python3
"""Extras generator — more functional items, abilities, moves and side quests.

Everything added here uses ONLY mechanics the engine already implements, so it is
real, working content (no dead data):
- items: use.kind in {capture, heal_hp, cure_status, revive} (see BattleEngine._do_item);
- abilities: hooks in {modify_outgoing_damage, modify_incoming_damage, prevent_stat_drop}
  with the param shapes AbilityEffects reads;
- moves: effect kinds in {damage, apply_status, stat_change, heal, recoil};
- side quests: objectives on the creatures_caught counter and on court-trainer win flags.

Idempotent (upsert by id). Run any time after the other generators.
Usage: python3 tools/generators/generate_extras.py
"""
from __future__ import annotations

import json
import os

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA = os.path.join(ROOT, "data")
TYPES = ["normal", "fire", "water", "grass", "electric", "earth", "wind", "mystic"]
REGION_ORDER = ["verdantia", "aquilon", "cindral", "solane", "umbra",
                "ferrock", "brume", "lumen", "zephyra"]


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


# --------------------------------------------------------------------- items
NEW_ITEMS = [
    {"id": "master_orb", "display_name": "Master Orb", "description": "The finest capture orb.",
     "price": 0, "usable_in_battle": True, "use": {"kind": "capture", "ball_rate": 3.0}},
    {"id": "dusk_orb", "display_name": "Dusk Orb", "description": "A capture orb tuned for the wild north.",
     "price": 600, "usable_in_battle": True, "use": {"kind": "capture", "ball_rate": 2.0}},
    {"id": "hyper_potion", "display_name": "Hyper Potion", "description": "Restores 120 HP.",
     "price": 1200, "usable_in_battle": True, "use": {"kind": "heal_hp", "amount": 120}},
    {"id": "max_potion", "display_name": "Max Potion", "description": "Fully restores HP.",
     "price": 2500, "usable_in_battle": True, "use": {"kind": "heal_hp", "amount": 9999}},
    {"id": "burn_salve", "display_name": "Burn Salve", "description": "Cures a burn.",
     "price": 250, "usable_in_battle": True, "use": {"kind": "cure_status", "status": "burn"}},
    {"id": "spark_charm", "display_name": "Spark Charm", "description": "Cures paralysis.",
     "price": 250, "usable_in_battle": True, "use": {"kind": "cure_status", "status": "paralyze"}},
    {"id": "max_revive", "display_name": "Max Revive", "description": "Revives a fainted creature to full HP.",
     "price": 4000, "usable_in_battle": True, "use": {"kind": "revive", "fraction": 1.0}},
]

# ----------------------------------------------------------------- abilities
NEW_ABILITIES = [
    {"id": "gale_soul", "display_name": "Gale Soul", "description": "Boosts Gale moves at low HP.",
     "hooks": ["modify_outgoing_damage"], "params": {"type": "wind", "hp_threshold": 0.34, "multiplier": 1.5}},
    {"id": "quake_soul", "display_name": "Quake Soul", "description": "Boosts Terra moves at low HP.",
     "hooks": ["modify_outgoing_damage"], "params": {"type": "earth", "hp_threshold": 0.34, "multiplier": 1.5}},
    {"id": "volt_soul", "display_name": "Volt Soul", "description": "Boosts Spark moves at low HP.",
     "hooks": ["modify_outgoing_damage"], "params": {"type": "electric", "hp_threshold": 0.34, "multiplier": 1.5}},
    {"id": "psy_soul", "display_name": "Psy Soul", "description": "Boosts Mystic moves at low HP.",
     "hooks": ["modify_outgoing_damage"], "params": {"type": "mystic", "hp_threshold": 0.34, "multiplier": 1.5}},
    {"id": "iron_wall", "display_name": "Iron Wall", "description": "Takes less physical damage.",
     "hooks": ["modify_incoming_damage"], "params": {"category": "physical", "multiplier": 0.8}},
    {"id": "spectral_veil", "display_name": "Spectral Veil", "description": "Takes less special damage.",
     "hooks": ["modify_incoming_damage"], "params": {"category": "special", "multiplier": 0.8}},
    {"id": "sure_grip", "display_name": "Sure Grip", "description": "Its Defense cannot be lowered.",
     "hooks": ["prevent_stat_drop"], "params": {"stat": "defense"}},
    {"id": "steady_aim", "display_name": "Steady Aim", "description": "Its Attack cannot be lowered.",
     "hooks": ["prevent_stat_drop"], "params": {"stat": "attack"}},
]

# --------------------------------------------------------------------- moves
# Rich variety, all from supported effect kinds.
def dmg(pid, name, t, cat, power, acc, pp, desc, pri=0, extra=None):
    fx = [{"kind": "damage"}]
    if extra:
        fx.append(extra)
    return {"id": pid, "display_name": name, "type": t, "category": cat, "power": power,
            "accuracy": acc, "priority": pri, "pp": pp, "description": desc, "effects": fx}


def status_move(pid, name, t, pp, desc, effect):
    return {"id": pid, "display_name": name, "type": t, "category": "status", "power": 0,
            "accuracy": 100, "priority": 0, "pp": pp, "description": desc, "effects": [effect]}


NEW_MOVES = [
    dmg("crush_blow", "Crush Blow", "normal", "physical", 90, 85, 8, "A heavy, risky slam."),
    dmg("swift_strike", "Swift Strike", "normal", "physical", 55, 100, 20, "A fast dependable hit.", pri=1),
    dmg("fire_fang", "Fire Fang", "fire", "physical", 65, 95, 15, "A searing bite.",
        extra={"kind": "apply_status", "status": "burn", "chance": 0.15, "target": "enemy"}),
    dmg("magma_beam", "Magma Beam", "fire", "special", 100, 85, 6, "A molten lance of heat."),
    dmg("frost_jet", "Frost Jet", "water", "special", 65, 100, 15, "A biting cold jet.",
        extra={"kind": "stat_change", "stat": "speed", "stages": -1, "chance": 0.3, "target": "enemy"}),
    dmg("tsunami", "Tsunami", "water", "special", 100, 80, 6, "An overwhelming wall of sea."),
    dmg("root_snare", "Root Snare", "grass", "physical", 60, 100, 15, "Roots that bind and tear.",
        extra={"kind": "stat_change", "stat": "speed", "stages": -1, "chance": 0.5, "target": "enemy"}),
    dmg("solar_bloom", "Solar Bloom", "grass", "special", 100, 90, 6, "A radiant floral blast."),
    dmg("thunder_clap", "Thunder Clap", "electric", "special", 70, 100, 12, "A jarring boom.",
        extra={"kind": "apply_status", "status": "paralyze", "chance": 0.3, "target": "enemy"}),
    dmg("overcharge", "Overcharge", "electric", "special", 110, 80, 5, "A reckless full discharge.",
        extra={"kind": "recoil", "fraction": 0.2}),
    dmg("boulder_crush", "Boulder Crush", "earth", "physical", 90, 85, 8, "A crushing rockfall."),
    dmg("fault_line", "Fault Line", "earth", "physical", 100, 80, 6, "The ground splits open."),
    dmg("sky_talon", "Sky Talon", "wind", "physical", 70, 100, 12, "A raking dive.", pri=1),
    dmg("hurricane", "Hurricane", "wind", "special", 100, 80, 6, "A region-scouring storm."),
    dmg("mind_shatter", "Mind Shatter", "mystic", "special", 95, 90, 8, "A psychic detonation.",
        extra={"kind": "stat_change", "stat": "sp_attack", "stages": -1, "chance": 0.3, "target": "enemy"}),
    dmg("astral_ram", "Astral Ram", "mystic", "physical", 80, 95, 10, "A charge of focused will."),
    status_move("iron_guard", "Iron Guard", "earth", 15, "Sharply raises Defense.",
                {"kind": "stat_change", "stat": "defense", "stages": 2, "chance": 1.0, "target": "self"}),
    status_move("battle_cry", "Battle Cry", "normal", 15, "Sharply raises Attack.",
                {"kind": "stat_change", "stat": "attack", "stages": 2, "chance": 1.0, "target": "self"}),
    status_move("meditate", "Meditate", "mystic", 15, "Sharply raises Sp. Attack.",
                {"kind": "stat_change", "stat": "sp_attack", "stages": 2, "chance": 1.0, "target": "self"}),
    status_move("quicken", "Quicken", "wind", 15, "Sharply raises Speed.",
                {"kind": "stat_change", "stat": "speed", "stages": 2, "chance": 1.0, "target": "self"}),
    status_move("mend", "Mend", "grass", 10, "Restores half the user's HP.",
                {"kind": "heal", "fraction": 0.5, "target": "self"}),
    status_move("wilt", "Wilt", "grass", 15, "Sharply lowers the foe's Attack.",
                {"kind": "stat_change", "stat": "attack", "stages": -2, "chance": 1.0, "target": "enemy"}),
    status_move("scary_face", "Scary Face", "normal", 15, "Sharply lowers the foe's Speed.",
                {"kind": "stat_change", "stat": "speed", "stages": -2, "chance": 1.0, "target": "enemy"}),
    status_move("smother", "Smother", "fire", 15, "Burns the foe.",
                {"kind": "apply_status", "status": "burn", "chance": 1.0, "target": "enemy"}),
    status_move("toxic_spore", "Toxic Spore", "grass", 15, "Poisons the foe.",
                {"kind": "apply_status", "status": "poison", "chance": 1.0, "target": "enemy"}),
]


def main():
    items_doc = load(os.path.join(DATA, "items", "items.json"))
    abilities_doc = load(os.path.join(DATA, "abilities", "abilities.json"))
    moves_doc = load(os.path.join(DATA, "moves", "moves.json"))
    quests_doc = load(os.path.join(DATA, "quests", "quests.json"))
    trainers = {t["id"] for t in load(os.path.join(DATA, "trainers", "trainers.json"))["trainers"]}

    for it in NEW_ITEMS:
        upsert(items_doc["items"], it)
    for ab in NEW_ABILITIES:
        upsert(abilities_doc["abilities"], ab)
    for mv in NEW_MOVES:
        upsert(moves_doc["moves"], mv)

    # Side quests: a global "collector" tier chain + a per-region "sparring" quest
    # tied to real court-trainer win flags (only added when those trainers exist).
    caught_tiers = [(3, "Novice Catcher", "great_orb", 1),
                    (10, "Field Cataloguer", "super_potion", 3),
                    (25, "Regional Naturalist", "dusk_orb", 3),
                    (50, "Master Collector", "master_orb", 1),
                    (100, "Living Encyclopedia", "max_revive", 2)]
    for n, title, reward_item, qty in caught_tiers:
        upsert(quests_doc["quests"], {
            "id": f"side_collect_{n}", "display_name": title, "category": "side",
            "auto_start": True,
            "description": f"Catch {n} creatures in total across your journey.",
            "objectives": [{"id": "obj_catch", "text": f"Catch {n} creatures.",
                            "condition": {"kind": "counter", "counter": "creatures_caught", "at_least": n}}],
            "rewards": [{"kind": "item", "item": reward_item, "quantity": qty},
                        {"kind": "money", "amount": 200 * (caught_tiers.index((n, title, reward_item, qty)) + 1)}],
            "on_complete_flag": f"collect_{n}_done",
        })

    sparring = 0
    for order, rid in enumerate(REGION_ORDER, start=1):
        targets = [f"{rid}_court1_t0", f"{rid}_court1_t1", f"{rid}_court1_t2"]
        targets = [t for t in targets if t in trainers]
        if len(targets) < 3:
            continue
        upsert(quests_doc["quests"], {
            "id": f"side_spar_{rid}", "display_name": f"{rid.capitalize()} Sparring League",
            "category": "side", "auto_start": False,
            "start_condition": {"kind": "flag", "flag": f"visited_{rid}"},
            "description": f"Prove yourself against three regulars of the {rid.capitalize()} Battle Court.",
            "objectives": [{"id": f"obj_{i}", "text": f"Defeat a {rid.capitalize()} Court regular ({i + 1}/3).",
                            "condition": {"kind": "flag", "flag": f"beat_{tid}"}}
                           for i, tid in enumerate(targets)],
            "rewards": [{"kind": "money", "amount": 500 + 200 * order},
                        {"kind": "item", "item": "hyper_potion", "quantity": 2}],
            "on_complete_flag": f"spar_{rid}_done",
        })
        sparring += 1

    save(os.path.join(DATA, "items", "items.json"), items_doc)
    save(os.path.join(DATA, "abilities", "abilities.json"), abilities_doc)
    save(os.path.join(DATA, "moves", "moves.json"), moves_doc)
    save(os.path.join(DATA, "quests", "quests.json"), quests_doc)
    print(f"Extras: +{len(NEW_ITEMS)} items, +{len(NEW_ABILITIES)} abilities, "
          f"+{len(NEW_MOVES)} moves, +{len(caught_tiers)} collector + {sparring} sparring quests.")


if __name__ == "__main__":
    main()
