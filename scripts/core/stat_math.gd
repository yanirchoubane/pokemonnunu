class_name StatMath
extends RefCounted
## Centralized stat & stat-stage math. No magic numbers elsewhere.

## Natures: each modifies one stat +10% and another -10% (neutral leaves both blank).
const NATURES := {
	"balanced": {"up": "", "down": ""},
	"brave":    {"up": "attack", "down": "speed"},
	"modest":   {"up": "sp_attack", "down": "attack"},
	"timid":    {"up": "speed", "down": "attack"},
	"bold":     {"up": "defense", "down": "attack"},
	"calm":     {"up": "sp_defense", "down": "attack"},
	"adamant":  {"up": "attack", "down": "sp_attack"},
	"jolly":    {"up": "speed", "down": "sp_attack"},
}

const STAT_KEYS := ["hp", "attack", "defense", "sp_attack", "sp_defense", "speed"]

static func nature_multiplier(nature: String, stat: String) -> float:
	var n: Dictionary = NATURES.get(nature, NATURES["balanced"])
	if stat == n.get("up", ""):
		return 1.1
	if stat == n.get("down", ""):
		return 0.9
	return 1.0

## Max HP formula.
static func compute_hp(base: int, iv: int, ev: int, level: int) -> int:
	return int(floor(float((2 * base + iv + int(ev / 4)) * level) / 100.0)) + level + 10

## Non-HP stat formula, with nature applied.
static func compute_stat(base: int, iv: int, ev: int, level: int, nature: String, stat: String) -> int:
	var raw: int = int(floor(float((2 * base + iv + int(ev / 4)) * level) / 100.0)) + 5
	return int(floor(float(raw) * nature_multiplier(nature, stat)))

## Multiplier for a stat stage in [-6, 6] (standard 2/(2±stage) curve).
static func stage_multiplier(stage: int) -> float:
	stage = clampi(stage, -6, 6)
	if stage >= 0:
		return float(2 + stage) / 2.0
	return 2.0 / float(2 - stage)
