class_name ExperienceCalc
extends RefCounted
## Experience curves and level<->exp conversion. Deterministic, pure.

const VALID_CURVES := ["fast", "medium_fast", "medium_slow", "slow"]

## Total experience required to BE at a given level (i.e. exp at start of that level).
static func exp_for_level(curve: String, level: int) -> int:
	level = max(level, 1)
	var n: float = float(level)
	match curve:
		"fast":
			return int(floor(0.8 * n * n * n))
		"medium_fast":
			return int(floor(n * n * n))
		"medium_slow":
			return int(max(0.0, floor(1.2 * n * n * n - 15.0 * n * n + 100.0 * n - 140.0)))
		"slow":
			return int(floor(1.25 * n * n * n))
		_:
			return int(floor(n * n * n))

## Level implied by a total experience amount (clamped to level_cap).
static func level_for_exp(curve: String, exp: int, level_cap: int = 100) -> int:
	var lvl: int = 1
	while lvl < level_cap and exp >= exp_for_level(curve, lvl + 1):
		lvl += 1
	return lvl

## Experience awarded for defeating a creature (before adaptive/reward multipliers).
static func award_for_defeat(defeated_base_exp: int, defeated_level: int, is_trainer: bool, trainer_bonus: float, participants: int) -> int:
	participants = max(participants, 1)
	var base: float = float(defeated_base_exp) * float(defeated_level) / 7.0
	if is_trainer:
		base *= trainer_bonus
	return int(max(1.0, floor(base / float(participants))))
