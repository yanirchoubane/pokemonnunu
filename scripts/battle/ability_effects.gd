class_name AbilityEffects
extends RefCounted
## Passive-ability hooks. Data-driven: an ability's `params` drive the math so most
## abilities need no new code. Pure functions, given the ability record.

## Outgoing damage multiplier contributed by the attacker's ability.
static func outgoing_multiplier(user: CreatureInstance, move: Dictionary, ability_rec: Dictionary) -> float:
	if ability_rec.is_empty():
		return 1.0
	if "modify_outgoing_damage" in ability_rec.get("hooks", []):
		var p: Dictionary = ability_rec.get("params", {})
		if String(move.get("type", "")) == String(p.get("type", "")):
			var threshold: float = float(p.get("hp_threshold", 0.0))
			if float(user.current_hp) / float(max(1, user.max_hp())) <= threshold:
				return float(p.get("multiplier", 1.0))
	return 1.0

## Incoming damage multiplier contributed by the defender's ability.
static func incoming_multiplier(defender: CreatureInstance, move: Dictionary, ability_rec: Dictionary) -> float:
	if ability_rec.is_empty():
		return 1.0
	if "modify_incoming_damage" in ability_rec.get("hooks", []):
		var p: Dictionary = ability_rec.get("params", {})
		var cat: String = String(p.get("category", ""))
		if cat == "" or cat == String(move.get("category", "")):
			return float(p.get("multiplier", 1.0))
	return 1.0

## Whether a stat drop on `target` is prevented by its ability.
static func prevents_stat_drop(target: CreatureInstance, stat: String, ability_rec: Dictionary) -> bool:
	if ability_rec.is_empty():
		return false
	if "prevent_stat_drop" in ability_rec.get("hooks", []):
		return String(ability_rec.get("params", {}).get("stat", "")) == stat
	return false
