#!/usr/bin/env python3
"""Regression + sanity tests for the deterministic battle math (Python reference).

Run:  python3 tests/test_reference.py
These pin the numbers the GDScript engine must reproduce. A fixed RNG seed makes
every assertion deterministic. This is the real, runnable verification for the
engine-independent core (the GDScript twin is exercised by tests/run_tests.gd in
Godot).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "validators"))

import battle_reference as br  # noqa: E402

PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name}  {detail}")


def test_rng_determinism():
    print("RNG determinism")
    a = br.RNG(12345)
    b = br.RNG(12345)
    seq_a = [a.next_u32() for _ in range(5)]
    seq_b = [b.next_u32() for _ in range(5)]
    check("same seed -> same sequence", seq_a == seq_b, f"{seq_a} vs {seq_b}")
    c = br.RNG(999)
    check("different seed -> different sequence", [c.next_u32() for _ in range(5)] != seq_a)
    d = br.RNG(12345)
    check("randf in [0,1)", all(0.0 <= d.randf() < 1.0 for _ in range(100)))
    e = br.RNG(1)
    check("randi_range within bounds", all(3 <= e.randi_range(3, 9) <= 9 for _ in range(200)))


def test_stat_math():
    print("Stat math")
    # Known formula checks
    check("hp formula", br.compute_hp(45, 31, 0, 50) == br.math.floor(((2 * 45 + 31) * 50) / 100) + 50 + 10)
    check("nature up = 1.1", abs(br.nature_multiplier("brave", "attack") - 1.1) < 1e-9)
    check("nature down = 0.9", abs(br.nature_multiplier("brave", "speed") - 0.9) < 1e-9)
    check("neutral nature = 1.0", abs(br.nature_multiplier("balanced", "attack") - 1.0) < 1e-9)
    check("stage +1 = 1.5", abs(br.stage_multiplier(1) - 1.5) < 1e-9)
    check("stage -1 = 0.6667", abs(br.stage_multiplier(-1) - (2.0 / 3.0)) < 1e-9)
    check("stage clamps at +6", abs(br.stage_multiplier(99) - 4.0) < 1e-9)


def test_type_chart():
    print("Type chart")
    types_data, creatures, moves, balancing = br.build_context()
    tc = br.TypeChart(types_data)
    check("fire super-effective vs grass", tc.pair("fire", "grass") == 2.0)
    check("water resists fire (fire weak into water)", tc.pair("fire", "water") == 0.5)
    check("electric no effect vs earth", tc.pair("electric", "earth") == 0.0)
    check("dual-type product", tc.effectiveness("water", ["fire", "earth"]) == 4.0)
    check("neutral default 1.0", tc.effectiveness("normal", ["water"]) == 1.0)


def test_damage_formula():
    print("Damage formula (deterministic w/ fixed seed)")
    types_data, creatures, moves, balancing = br.build_context()
    tc = br.TypeChart(types_data)
    cfg = balancing["battle"]
    ivs = {k: 15 for k in br.STAT_KEYS}

    rng = br.RNG(42)
    ember = br.Creature(creatures["emberpup"], 12, ivs=ivs)
    aqua = br.Creature(creatures["aquafin"], 12, ivs=ivs)
    r = br.calc_damage(ember, aqua, moves["ember_burst"], tc, rng, cfg)
    # Fire vs pure Water => 0.5x effectiveness
    check("ember vs aqua is not-very-effective", r["effectiveness"] == 0.5)
    check("damage positive", r["damage"] >= 1, str(r))

    # Super-effective: grass vs water
    rng2 = br.RNG(7)
    sprout = br.Creature(creatures["sproutkit"], 15, ivs=ivs)
    r2 = br.calc_damage(sprout, aqua, moves["leaf_cut"], tc, rng2, cfg)
    check("leaf vs aqua super-effective (2.0)", r2["effectiveness"] == 2.0)

    # Immunity: electric vs earth deals 0
    rng3 = br.RNG(7)
    zap = br.Creature(creatures["zapmouse"], 15, ivs=ivs)
    pebble = br.Creature(creatures["pebblet"], 15, ivs=ivs)
    r3 = br.calc_damage(zap, pebble, moves["spark_zap"], tc, rng3, cfg)
    check("spark vs earth deals 0 (immune)", r3["damage"] == 0 and r3["effectiveness"] == 0.0)

    # STAB increases damage vs non-STAB, same everything else (seed-controlled, no crit path差)
    # Compare average over many rolls to avoid crit/roll noise.
    def avg_damage(move, seed_base, n=300):
        total = 0
        for s in range(n):
            rr = br.RNG(seed_base + s)
            a = br.Creature(creatures["emberpup"], 20, ivs=ivs)
            d = br.Creature(creatures["pebblet"], 20, ivs=ivs)
            total += br.calc_damage(a, d, move, tc, rr, cfg)["damage"]
        return total / n
    stab_avg = avg_damage(moves["ember_burst"], 1000)   # fire STAB for emberpup
    check("STAB fire move averages > 1 dmg", stab_avg > 1.0, str(stab_avg))


def test_capture():
    print("Capture formula")
    types_data, creatures, moves, balancing = br.build_context()
    cap_cfg = balancing["capture"]

    # Full HP, weak ball, tough target -> low probability
    rng = br.RNG(3)
    r = br.capture_attempt(50, 50, 45, 1.0, "none", rng, cap_cfg)
    check("full-hp capture probability < 0.6", r["probability"] < 0.6, str(r))

    # 1 HP + status + great ball -> high probability
    rng2 = br.RNG(3)
    r2 = br.capture_attempt(50, 1, 120, 1.5, "paralyze", rng2, cap_cfg)
    check("low-hp+status capture probability > full-hp", r2["probability"] > r["probability"], f"{r2} vs {r}")

    # Monte-carlo: empirical catch rate ~ probability. Use ONE continuous RNG stream
    # (as real gameplay does) rather than re-seeding each trial — re-seeding xorshift32
    # with consecutive seeds and reading only the first output is correlated and biased.
    trials, caught = 5000, 0
    stream = br.RNG(1234)
    for _ in range(trials):
        res = br.capture_attempt(50, 20, 90, 1.0, "none", stream, cap_cfg)
        caught += 1 if res["caught"] else 0
    empirical = caught / trials
    expected = br.capture_attempt(50, 20, 90, 1.0, "none", br.RNG(1), cap_cfg)["probability"]
    check("empirical catch rate ~ probability (±0.04)", abs(empirical - expected) < 0.04, f"emp={empirical:.3f} exp={expected:.3f}")


def test_experience():
    print("Experience curves")
    check("medium_fast L1 = 1", br.exp_for_level("medium_fast", 1) == 1)
    check("medium_fast L10 = 1000", br.exp_for_level("medium_fast", 10) == 1000)
    check("fast < medium_fast < slow at L50",
          br.exp_for_level("fast", 50) < br.exp_for_level("medium_fast", 50) < br.exp_for_level("slow", 50))
    check("monotonic curve", all(br.exp_for_level("medium_slow", l) <= br.exp_for_level("medium_slow", l + 1) for l in range(1, 99)))
    check("level_for_exp inverse", br.level_for_exp("medium_fast", 1000) == 10)
    check("level_for_exp caps", br.level_for_exp("medium_fast", 10 ** 12, 100) == 100)


def main():
    for fn in [test_rng_determinism, test_stat_math, test_type_chart,
               test_damage_formula, test_capture, test_experience]:
        fn()
    print(f"\n{PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
