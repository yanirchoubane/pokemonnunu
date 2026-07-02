class_name CreatureInstance
extends RefCounted
## A live creature: species data + individual state. Used by party, box, and battle.
##
## Kept engine-independent (no autoload access) so it is unit-testable. The species
## dictionary is injected by CreatureFactory; stat math uses StatMath.

var species_id: String = ""
var species: Dictionary = {}          # raw data record (injected)
var nickname: String = ""
var level: int = 1
var exp: int = 0
var ivs: Dictionary = {}              # stat -> 0..31
var evs: Dictionary = {}              # stat -> 0..255
var nature: String = "balanced"
var ability: String = ""
var gender: String = "genderless"
var current_hp: int = 0
var status: String = "none"           # none/burn/poison/paralyze/sleep
var status_counter: int = 0
var moves: Array = []                 # [{ "id": String, "pp": int, "max_pp": int }]

# Battle-only volatile state (never serialized)
var stat_stages: Dictionary = {"attack": 0, "defense": 0, "sp_attack": 0, "sp_defense": 0, "speed": 0}

func base_stat(key: String) -> int:
	return int(species.get("base_stats", {}).get(key, 1))

func types() -> Array:
	return species.get("types", [])

func display_name() -> String:
	if nickname != "":
		return nickname
	return String(species.get("display_name", species_id))

func max_hp() -> int:
	return StatMath.compute_hp(base_stat("hp"), int(ivs.get("hp", 0)), int(evs.get("hp", 0)), level)

## Base (non-stage) stat value.
func stat(key: String) -> int:
	if key == "hp":
		return max_hp()
	return StatMath.compute_stat(base_stat(key), int(ivs.get(key, 0)), int(evs.get(key, 0)), level, nature, key)

## Stat value with battle stat stages applied (attack/defense/sp_*/speed only).
func battle_stat(key: String) -> int:
	var base: int = stat(key)
	var stage: int = int(stat_stages.get(key, 0))
	return int(max(1.0, floor(float(base) * StatMath.stage_multiplier(stage))))

func is_fainted() -> bool:
	return current_hp <= 0

func heal_full() -> void:
	current_hp = max_hp()
	status = "none"
	status_counter = 0
	for m in moves:
		m["pp"] = m["max_pp"]

func reset_battle_state() -> void:
	stat_stages = {"attack": 0, "defense": 0, "sp_attack": 0, "sp_defense": 0, "speed": 0}

func exp_curve() -> String:
	return String(species.get("exp_curve", "medium_fast"))

## --- Serialization (only mutable state; species reattached on load) ---
func to_dict() -> Dictionary:
	return {
		"species_id": species_id,
		"nickname": nickname,
		"level": level,
		"exp": exp,
		"ivs": ivs.duplicate(),
		"evs": evs.duplicate(),
		"nature": nature,
		"ability": ability,
		"gender": gender,
		"current_hp": current_hp,
		"status": status,
		"status_counter": status_counter,
		"moves": moves.duplicate(true),
	}

func from_dict(d: Dictionary) -> void:
	species_id = String(d.get("species_id", ""))
	nickname = String(d.get("nickname", ""))
	level = int(d.get("level", 1))
	exp = int(d.get("exp", 0))
	ivs = (d.get("ivs", {}) as Dictionary).duplicate()
	evs = (d.get("evs", {}) as Dictionary).duplicate()
	nature = String(d.get("nature", "balanced"))
	ability = String(d.get("ability", ""))
	gender = String(d.get("gender", "genderless"))
	current_hp = int(d.get("current_hp", 0))
	status = String(d.get("status", "none"))
	status_counter = int(d.get("status_counter", 0))
	moves = (d.get("moves", []) as Array).duplicate(true)
