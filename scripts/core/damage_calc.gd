class_name DamageCalc
extends RefCounted
## Deterministic damage formula. Pure: takes explicit config + RNG so it is
## unit-testable and reproducible. Mirrored byte-for-byte by the Python reference
## tools/validators/battle_reference.py (see tests/test_reference.py).
##
## RNG draw order (MUST match the reference): 1) critical check, 2) random factor.

## Returns:
##   { "damage": int, "effectiveness": float, "critical": bool, "physical": bool }
static func calc(attacker: CreatureInstance, defender: CreatureInstance, move: Dictionary,
		type_chart: TypeChart, rng: RNG, cfg: Dictionary, ability_mult: float = 1.0) -> Dictionary:
	var power: int = int(move.get("power", 0))
	if power <= 0:
		return {"damage": 0, "effectiveness": 1.0, "critical": false, "physical": false}

	var physical: bool = String(move.get("category", "physical")) == "physical"
	var atk_key: String = "attack" if physical else "sp_attack"
	var def_key: String = "defense" if physical else "sp_defense"

	var atk: int = attacker.battle_stat(atk_key)
	var def_val: int = defender.battle_stat(def_key)

	# Burn halves physical attack.
	if physical and attacker.status == "burn":
		atk = int(floor(float(atk) * float(cfg.get("burn_physical_multiplier", 0.5))))
	atk = max(1, atk)
	def_val = max(1, def_val)

	var level: int = attacker.level
	var num: float = float(cfg.get("level_scale_numerator", 2))
	var base_lvl: float = float(cfg.get("level_scale_base", 5))
	var divisor: float = float(cfg.get("damage_base_divisor", 50))
	var level_factor: float = (num * float(level)) / base_lvl + 2.0

	var inner: float = (level_factor * float(power) * float(atk) / float(def_val)) / divisor
	var base_damage: int = int(floor(inner)) + 2

	# 1) critical (one RNG draw)
	var crit_chance: float = float(cfg.get("critical_chance", 0.0625))
	var is_crit: bool = rng.chance(crit_chance)
	var crit_mult: float = float(cfg.get("critical_multiplier", 1.5)) if is_crit else 1.0

	# 2) random factor (one RNG draw)
	var rmin: int = int(float(cfg.get("damage_random_min", 0.85)) * 100.0)
	var rmax: int = int(float(cfg.get("damage_random_max", 1.0)) * 100.0)
	var rand_factor: float = float(rng.randi_range(rmin, rmax)) / 100.0

	var stab: float = float(cfg.get("stab_multiplier", 1.5)) if String(move.get("type", "")) in attacker.types() else 1.0
	var eff: float = type_chart.effectiveness(String(move.get("type", "")), defender.types())

	var total: float = float(base_damage) * crit_mult * stab * eff * rand_factor * ability_mult
	var damage: int = int(floor(total))
	if eff <= 0.0:
		damage = 0
	else:
		damage = max(1, damage)

	return {"damage": damage, "effectiveness": eff, "critical": is_crit, "physical": physical}

## Accuracy check as a separate, single RNG draw (returns true on hit).
static func accuracy_check(move: Dictionary, rng: RNG) -> bool:
	var acc: int = int(move.get("accuracy", 100))
	if acc >= 100:
		return true
	return rng.randi_range(1, 100) <= acc
