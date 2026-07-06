class_name EvolutionSystem
extends RefCounted
## Resolves evolutions against data/evolutions.json. Pure: given a creature and the
## evolution rules + species index, decides whether/what it evolves into.

## Returns the target species_id if `c` should evolve now under `trigger`, else "".
## trigger: "level_up" | "use_item" (item_id in ctx) | "trade"
static func check(c: CreatureInstance, evolutions_by_from: Dictionary, trigger: String, ctx: Dictionary = {}) -> String:
	var rule: Dictionary = evolutions_by_from.get(c.species_id, {})
	if rule.is_empty():
		return ""
	var cond: Dictionary = rule.get("condition", {})
	match String(cond.get("kind", "")):
		"level_up":
			if trigger == "level_up" and c.level >= int(cond.get("level", 999)):
				return String(rule.get("to", ""))
		"use_item":
			if trigger == "use_item" and String(ctx.get("item", "")) == String(cond.get("item", "")):
				return String(rule.get("to", ""))
		"trade":
			if trigger == "trade":
				return String(rule.get("to", ""))
	return ""

## Apply an evolution in place: swap species, keep level/exp/ivs/evs/moves/nickname.
## Recomputes current_hp proportionally so the creature isn't healed or hurt by evolving.
static func evolve(c: CreatureInstance, target_species: Dictionary, moves_index: Dictionary) -> void:
	var old_max: int = c.max_hp()
	var hp_ratio: float = float(c.current_hp) / float(max(1, old_max))
	c.species = target_species
	c.species_id = String(target_species.get("id", c.species_id))
	# Keep the same ability slot if still valid; else fall back to first listed.
	var abilities: Array = target_species.get("abilities", [])
	if abilities.size() > 0 and not (c.ability in abilities):
		c.ability = String(abilities[0])
	c.current_hp = max(1, int(round(float(c.max_hp()) * hp_ratio)))
