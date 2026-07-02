class_name CreatureFactory
extends RefCounted
## Builds live CreatureInstance objects from species data.
## Pure: callers pass the species record, level, an RNG, and a move index
## (move_id -> move record). This keeps it unit-testable without autoloads.

const IV_MAX := 31

static func build(species: Dictionary, level: int, rng: RNG, moves_index: Dictionary, opts: Dictionary = {}) -> CreatureInstance:
	var c := CreatureInstance.new()
	c.species = species
	c.species_id = String(species.get("id", ""))
	c.level = max(1, level)
	c.exp = ExperienceCalc.exp_for_level(String(species.get("exp_curve", "medium_fast")), c.level)

	# IVs: random 0..31 per stat unless perfect requested.
	var perfect: bool = opts.get("perfect_ivs", false)
	for key in StatMath.STAT_KEYS:
		c.ivs[key] = IV_MAX if perfect else rng.randi_range(0, IV_MAX)
		c.evs[key] = int(opts.get("evs", {}).get(key, 0))

	# Nature (deterministic from RNG unless specified).
	if opts.has("nature"):
		c.nature = String(opts["nature"])
	else:
		var names: Array = StatMath.NATURES.keys()
		c.nature = String(names[rng.randi_range(0, names.size() - 1)])

	# Ability: first listed by default, or random among listed.
	var abilities: Array = species.get("abilities", [])
	if abilities.size() > 0:
		c.ability = String(abilities[rng.randi_range(0, abilities.size() - 1)]) if opts.get("random_ability", false) else String(abilities[0])

	# Gender from ratio (fraction male).
	var ratio: float = float(species.get("gender_ratio", -1.0))
	if ratio < 0.0:
		c.gender = "genderless"
	else:
		c.gender = "male" if rng.randf() < ratio else "female"

	# Moves: explicit list wins, else the 4 highest-level learnset moves at/under level.
	if opts.has("moves"):
		c.moves = _build_moves(opts["moves"], moves_index)
	else:
		c.moves = _build_moves(default_moveset(species, c.level), moves_index)

	c.current_hp = c.max_hp()
	c.status = "none"
	return c

## The up-to-4 most recent learnset moves the creature knows at `level`.
static func default_moveset(species: Dictionary, level: int) -> Array:
	var learned: Array = []
	for entry in species.get("learnset", []):
		if int(entry.get("level", 1)) <= level:
			learned.append(String(entry.get("move", "")))
	# Keep the last 4 learned (most recent).
	if learned.size() > 4:
		learned = learned.slice(learned.size() - 4, learned.size())
	return learned

static func _build_moves(move_ids: Array, moves_index: Dictionary) -> Array:
	var out: Array = []
	for mid_any in move_ids:
		var mid := String(mid_any)
		if mid == "":
			continue
		var pp: int = int(moves_index.get(mid, {}).get("pp", 10))
		out.append({"id": mid, "pp": pp, "max_pp": pp})
	return out

## Rebuild a saved instance, reattaching its species record.
static func from_saved(d: Dictionary, species_index: Dictionary) -> CreatureInstance:
	var c := CreatureInstance.new()
	c.from_dict(d)
	c.species = species_index.get(c.species_id, {})
	return c
