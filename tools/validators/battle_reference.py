#!/usr/bin/env python3
"""Executable reference implementation of the deterministic battle math.

This mirrors, line-for-line, the pure GDScript in scripts/core/ (rng.gd,
stat_math.gd, damage_calc.gd, capture_calc.gd, experience_calc.gd). Because Godot
is not always available in CI, this Python twin is what actually *runs* to pin the
numbers the engine must reproduce (see tests/test_reference.py and
scripts/core/damage_calc.gd's header). Keep the two in sync when tuning formulas.
"""
from __future__ import annotations

import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data")
MASK32 = 0xFFFFFFFF
STAT_KEYS = ["hp", "attack", "defense", "sp_attack", "sp_defense", "speed"]

NATURES = {
    "balanced": {"up": "", "down": ""},
    "brave": {"up": "attack", "down": "speed"},
    "modest": {"up": "sp_attack", "down": "attack"},
    "timid": {"up": "speed", "down": "attack"},
    "bold": {"up": "defense", "down": "attack"},
    "calm": {"up": "sp_defense", "down": "attack"},
    "adamant": {"up": "attack", "down": "sp_attack"},
    "jolly": {"up": "speed", "down": "sp_attack"},
}


def load(*parts):
    with open(os.path.join(DATA, *parts), "r", encoding="utf-8") as f:
        return json.load(f)


# ------------------------------------------------------------------ RNG (xorshift32)
class RNG:
    def __init__(self, seed=0x1234ABCD):
        self.set_seed(seed)

    def set_seed(self, seed):
        self._state = seed & MASK32
        if self._state == 0:
            self._state = 0x1234ABCD

    def get_state(self):
        return self._state

    def next_u32(self):
        x = self._state
        x = (x ^ ((x << 13) & MASK32)) & MASK32
        x = (x ^ (x >> 17)) & MASK32
        x = (x ^ ((x << 5) & MASK32)) & MASK32
        self._state = x
        return x

    def randf(self):
        return self.next_u32() / 4294967296.0

    def randi_range(self, lo, hi):
        if hi <= lo:
            return lo
        return lo + (self.next_u32() % (hi - lo + 1))

    def chance(self, p):
        if p <= 0.0:
            return False
        if p >= 1.0:
            return True
        return self.randf() < p


# ------------------------------------------------------------------ StatMath
def nature_multiplier(nature, stat):
    n = NATURES.get(nature, NATURES["balanced"])
    if stat == n["up"]:
        return 1.1
    if stat == n["down"]:
        return 0.9
    return 1.0


def compute_hp(base, iv, ev, level):
    return math.floor(((2 * base + iv + ev // 4) * level) / 100) + level + 10


def compute_stat(base, iv, ev, level, nature, stat):
    raw = math.floor(((2 * base + iv + ev // 4) * level) / 100) + 5
    return math.floor(raw * nature_multiplier(nature, stat))


def stage_multiplier(stage):
    stage = max(-6, min(6, stage))
    if stage >= 0:
        return (2 + stage) / 2.0
    return 2.0 / (2 - stage)


# ------------------------------------------------------------------ Type chart
class TypeChart:
    def __init__(self, types_data):
        self.chart = {a: {d: float(v) for d, v in row.items()}
                      for a, row in types_data.get("chart", {}).items()}

    def pair(self, atk, dfn):
        return self.chart.get(atk, {}).get(dfn, 1.0)

    def effectiveness(self, atk, defender_types):
        m = 1.0
        for dt in defender_types:
            m *= self.pair(atk, dt)
        return m


# ------------------------------------------------------------------ Creature
class Creature:
    def __init__(self, species, level, ivs=None, evs=None, nature="balanced", ability="", moves=None):
        self.species = species
        self.level = level
        self.ivs = ivs or {k: 0 for k in STAT_KEYS}
        self.evs = evs or {k: 0 for k in STAT_KEYS}
        self.nature = nature
        self.ability = ability
        self.status = "none"
        self.stat_stages = {"attack": 0, "defense": 0, "sp_attack": 0, "sp_defense": 0, "speed": 0}
        self.moves = moves or []
        self.current_hp = self.max_hp()

    def base(self, k):
        return self.species["base_stats"][k]

    def types(self):
        return self.species["types"]

    def max_hp(self):
        return compute_hp(self.base("hp"), self.ivs["hp"], self.evs["hp"], self.level)

    def stat(self, k):
        if k == "hp":
            return self.max_hp()
        return compute_stat(self.base(k), self.ivs[k], self.evs[k], self.level, self.nature, k)

    def battle_stat(self, k):
        return max(1, math.floor(self.stat(k) * stage_multiplier(self.stat_stages.get(k, 0))))

    def is_fainted(self):
        return self.current_hp <= 0


# ------------------------------------------------------------------ Damage
def calc_damage(attacker, defender, move, type_chart, rng, cfg, ability_mult=1.0):
    power = move.get("power", 0)
    if power <= 0:
        return {"damage": 0, "effectiveness": 1.0, "critical": False}
    physical = move.get("category", "physical") == "physical"
    atk_key = "attack" if physical else "sp_attack"
    def_key = "defense" if physical else "sp_defense"
    atk = attacker.battle_stat(atk_key)
    dfn = defender.battle_stat(def_key)
    if physical and attacker.status == "burn":
        atk = math.floor(atk * cfg.get("burn_physical_multiplier", 0.5))
    atk = max(1, atk)
    dfn = max(1, dfn)

    num = cfg.get("level_scale_numerator", 2)
    base_lvl = cfg.get("level_scale_base", 5)
    divisor = cfg.get("damage_base_divisor", 50)
    level_factor = (num * attacker.level) / base_lvl + 2.0
    inner = (level_factor * power * atk / dfn) / divisor
    base_damage = math.floor(inner) + 2

    is_crit = rng.chance(cfg.get("critical_chance", 0.0625))
    crit_mult = cfg.get("critical_multiplier", 1.5) if is_crit else 1.0

    rmin = int(cfg.get("damage_random_min", 0.85) * 100)
    rmax = int(cfg.get("damage_random_max", 1.0) * 100)
    rand_factor = rng.randi_range(rmin, rmax) / 100.0

    stab = cfg.get("stab_multiplier", 1.5) if move.get("type") in attacker.types() else 1.0
    eff = type_chart.effectiveness(move.get("type"), defender.types())

    total = base_damage * crit_mult * stab * eff * rand_factor * ability_mult
    damage = math.floor(total)
    damage = 0 if eff <= 0.0 else max(1, damage)
    return {"damage": damage, "effectiveness": eff, "critical": is_crit}


# ------------------------------------------------------------------ Capture
def capture_attempt(max_hp, current_hp, capture_rate, ball_rate, status, rng, cfg):
    status_bonus = cfg.get("status_bonus", {}).get(status, cfg.get("status_bonus", {}).get("none", 1.0))
    max_val = cfg.get("max_catch_value", 255)
    shakes_needed = cfg.get("shake_checks", 4)
    max_hp = max(1, max_hp)
    current_hp = max(0, min(current_hp, max_hp))
    a = ((3 * max_hp - 2 * current_hp) * capture_rate * ball_rate * status_bonus) / (3 * max_hp)
    a = min(a, max_val)
    probability = max(0.0, min(1.0, a / max_val))
    if probability >= 1.0:
        return {"caught": True, "shakes": shakes_needed, "probability": 1.0}
    shake_prob = probability ** (1.0 / shakes_needed)
    shakes = 0
    caught = True
    for _ in range(shakes_needed):
        if rng.randf() < shake_prob:
            shakes += 1
        else:
            caught = False
            break
    return {"caught": caught, "shakes": shakes, "probability": probability}


# ------------------------------------------------------------------ Experience
def exp_for_level(curve, level):
    level = max(level, 1)
    n = float(level)
    if curve == "fast":
        return math.floor(0.8 * n ** 3)
    if curve == "medium_fast":
        return math.floor(n ** 3)
    if curve == "medium_slow":
        return math.floor(max(0.0, 1.2 * n ** 3 - 15.0 * n ** 2 + 100.0 * n - 140.0))
    if curve == "slow":
        return math.floor(1.25 * n ** 3)
    return math.floor(n ** 3)


def level_for_exp(curve, exp, level_cap=100):
    lvl = 1
    while lvl < level_cap and exp >= exp_for_level(curve, lvl + 1):
        lvl += 1
    return lvl


def build_context():
    types_data = load("types", "types.json")
    creatures = {c["id"]: c for c in load("creatures", "creatures.json")["creatures"]}
    moves = {m["id"]: m for m in load("moves", "moves.json")["moves"]}
    balancing = load("balancing", "balancing.json")
    return types_data, creatures, moves, balancing


if __name__ == "__main__":
    types_data, creatures, moves, balancing = build_context()
    tc = TypeChart(types_data)
    rng = RNG(42)
    ember = Creature(creatures["emberpup"], 12, ivs={k: 15 for k in STAT_KEYS})
    aqua = Creature(creatures["aquafin"], 12, ivs={k: 15 for k in STAT_KEYS})
    res = calc_damage(ember, aqua, moves["ember_burst"], tc, rng, balancing["battle"])
    print("Emberpup Ember Burst vs Aquafin:", res)
    res2 = calc_damage(aqua, ember, moves["aqua_dart"], tc, rng, balancing["battle"])
    print("Aquafin Aqua Dart vs Emberpup:", res2)
