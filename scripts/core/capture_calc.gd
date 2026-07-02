class_name CaptureCalc
extends RefCounted
## Capture probability + shake animation resolution. Pure & deterministic.
## Overall catch chance == (per-shake chance) ^ shake_checks, so the animation's
## shake count is honest about the real probability.

## Returns { "caught": bool, "shakes": int, "catch_value": float, "probability": float }
static func attempt(max_hp: int, current_hp: int, capture_rate: int, ball_rate: float,
		status: String, rng: RNG, cfg: Dictionary) -> Dictionary:
	var status_bonus_table: Dictionary = cfg.get("status_bonus", {})
	var status_bonus: float = float(status_bonus_table.get(status, status_bonus_table.get("none", 1.0)))
	var max_val: float = float(cfg.get("max_catch_value", 255))
	var shake_checks: int = int(cfg.get("shake_checks", 4))

	max_hp = max(1, max_hp)
	current_hp = clampi(current_hp, 0, max_hp)

	var a: float = (float(3 * max_hp - 2 * current_hp) * float(capture_rate) * ball_rate * status_bonus) / float(3 * max_hp)
	a = min(a, max_val)
	var probability: float = clampf(a / max_val, 0.0, 1.0)

	if probability >= 1.0:
		return {"caught": true, "shakes": shake_checks, "catch_value": a, "probability": 1.0}

	var shake_prob: float = pow(probability, 1.0 / float(shake_checks))
	var shakes: int = 0
	var caught: bool = true
	for i in shake_checks:
		if rng.randf() < shake_prob:
			shakes += 1
		else:
			caught = false
			break
	return {"caught": caught, "shakes": shakes, "catch_value": a, "probability": probability}
