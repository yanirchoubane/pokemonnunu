extends Node
## DataRegistry (autoload): loads, validates, indexes ALL external content at boot.
## The engine reads game content ONLY through this registry — nothing is hard-coded.

const DATA_ROOT := "res://data"

signal data_loaded
signal data_error(errors: Array)

# Raw + indexed data
var types_data: Dictionary = {}
var type_chart: TypeChart = TypeChart.new()
var creatures: Dictionary = {}      # id -> record
var moves: Dictionary = {}          # id -> record
var abilities: Dictionary = {}      # id -> record
var items: Dictionary = {}          # id -> record
var evolutions: Array = []          # list of rules
var evolutions_by_from: Dictionary = {}
var encounter_tables: Dictionary = {} # id -> record
var trainers: Dictionary = {}       # id -> record
var regions: Dictionary = {}        # id -> manifest
var maps: Dictionary = {}           # id -> map record
var quests: Dictionary = {}         # id -> record
var balancing: Dictionary = {}
var adaptive_config: Dictionary = {}

var load_errors: Array = []
var loaded: bool = false

func _ready() -> void:
	reload()

func reload() -> void:
	load_errors.clear()
	_load_all()               # appends file/JSON/duplicate-id errors into load_errors
	load_errors.append_array(validate())  # accumulate reference/consistency errors
	type_chart.load_from(types_data)
	loaded = true
	if load_errors.is_empty():
		data_loaded.emit()
	else:
		for e in load_errors:
			push_error("[DataRegistry] " + e)
		data_error.emit(load_errors)

func _load_all() -> void:
	types_data = _load_json("%s/types/types.json" % DATA_ROOT)
	creatures = _index(_load_json("%s/creatures/creatures.json" % DATA_ROOT).get("creatures", []), "id")
	moves = _index(_load_json("%s/moves/moves.json" % DATA_ROOT).get("moves", []), "id")
	abilities = _index(_load_json("%s/abilities/abilities.json" % DATA_ROOT).get("abilities", []), "id")
	items = _index(_load_json("%s/items/items.json" % DATA_ROOT).get("items", []), "id")
	evolutions = _load_json("%s/evolutions/evolutions.json" % DATA_ROOT).get("evolutions", [])
	evolutions_by_from.clear()
	for e in evolutions:
		evolutions_by_from[String(e.get("from", ""))] = e
	encounter_tables = _index(_load_json("%s/encounters/encounters.json" % DATA_ROOT).get("tables", []), "id")
	trainers = _index(_load_json("%s/trainers/trainers.json" % DATA_ROOT).get("trainers", []), "id")
	quests = _index(_load_json("%s/quests/quests.json" % DATA_ROOT).get("quests", []), "id")
	balancing = _load_json("%s/balancing/balancing.json" % DATA_ROOT)
	adaptive_config = _load_json("%s/balancing/adaptive.json" % DATA_ROOT)

	# Regions: files data/regions/region_*.json
	regions.clear()
	for path in _list_json("%s/regions" % DATA_ROOT):
		if path.get_file().begins_with("region_"):
			var r := _load_json(path)
			if r.has("id"):
				regions[String(r["id"])] = r
	# Maps: files under data/regions/maps/
	maps.clear()
	for path in _list_json("%s/regions/maps" % DATA_ROOT):
		var m := _load_json(path)
		if m.has("id"):
			maps[String(m["id"])] = m

# ------------------------------------------------------------------ accessors

func battle_cfg() -> Dictionary:
	return balancing.get("battle", {})

func capture_cfg() -> Dictionary:
	return balancing.get("capture", {})

func exp_cfg() -> Dictionary:
	return balancing.get("experience", {})

func party_cfg() -> Dictionary:
	return balancing.get("party", {})

func economy_cfg() -> Dictionary:
	return balancing.get("economy", {})

func get_region_in_order() -> Array:
	var arr: Array = regions.values()
	arr.sort_custom(func(a, b): return int(a.get("order", 99)) < int(b.get("order", 99)))
	return arr

func evolution_for(species_id: String) -> Dictionary:
	return evolutions_by_from.get(species_id, {})

# ------------------------------------------------------------------ validation

## Returns an array of human-readable error strings. Empty == valid.
func validate() -> Array:
	var errors: Array = []
	# Duplicate ids are impossible after _index, but detect source duplicates by count check is skipped.
	var valid_types := {}
	for t in types_data.get("types", []):
		valid_types[t["id"]] = true

	# Type chart references
	for atk in types_data.get("chart", {}).keys():
		if not valid_types.has(atk):
			errors.append("Type chart references unknown attacking type '%s'." % atk)
		for def in types_data["chart"][atk].keys():
			if not valid_types.has(def):
				errors.append("Type chart references unknown defending type '%s'." % def)

	# Moves
	for mid in moves.keys():
		var mv: Dictionary = moves[mid]
		if not valid_types.has(String(mv.get("type", ""))):
			errors.append("Move '%s' has unknown type '%s'." % [mid, mv.get("type", "")])
		if not (String(mv.get("category", "")) in ["physical", "special", "status"]):
			errors.append("Move '%s' has invalid category '%s'." % [mid, mv.get("category", "")])

	# Abilities referenced by creatures
	for cid in creatures.keys():
		var c: Dictionary = creatures[cid]
		for t in c.get("types", []):
			if not valid_types.has(String(t)):
				errors.append("Creature '%s' has unknown type '%s'." % [cid, t])
		for ab in c.get("abilities", []):
			if not abilities.has(String(ab)):
				errors.append("Creature '%s' references unknown ability '%s'." % [cid, ab])
		for entry in c.get("learnset", []):
			if not moves.has(String(entry.get("move", ""))):
				errors.append("Creature '%s' learnset references unknown move '%s'." % [cid, entry.get("move", "")])
		# Stat sanity
		for k in ["hp", "attack", "defense", "sp_attack", "sp_defense", "speed"]:
			var v: int = int(c.get("base_stats", {}).get(k, -1))
			if v < 1 or v > 255:
				errors.append("Creature '%s' has invalid base stat %s=%d." % [cid, k, v])
		if not (String(c.get("exp_curve", "")) in ExperienceCalc.VALID_CURVES):
			errors.append("Creature '%s' has unknown exp_curve '%s'." % [cid, c.get("exp_curve", "")])
		for target in c.get("evolves_to", []):
			if not creatures.has(String(target)):
				errors.append("Creature '%s' evolves_to unknown creature '%s'." % [cid, target])

	# Evolutions: valid refs + no circular chains
	for e in evolutions:
		if not creatures.has(String(e.get("from", ""))):
			errors.append("Evolution '%s' from unknown creature '%s'." % [e.get("id", "?"), e.get("from", "")])
		if not creatures.has(String(e.get("to", ""))):
			errors.append("Evolution '%s' to unknown creature '%s'." % [e.get("id", "?"), e.get("to", "")])
	errors.append_array(_detect_evolution_cycles())

	# Items
	for iid in items.keys():
		var use: Dictionary = items[iid].get("use", {})
		if String(use.get("kind", "")) == "cure_status":
			pass

	# Encounter tables reference existing creatures + region
	for tid in encounter_tables.keys():
		for entry in encounter_tables[tid].get("entries", []):
			if not creatures.has(String(entry.get("creature", ""))):
				errors.append("Encounter table '%s' references unknown creature '%s'." % [tid, entry.get("creature", "")])

	# Trainers reference existing creatures + moves + ai tier
	for tid in trainers.keys():
		var tr: Dictionary = trainers[tid]
		if not (String(tr.get("ai", "basic")) in ["basic", "intermediate", "advanced"]):
			errors.append("Trainer '%s' has invalid ai tier '%s'." % [tid, tr.get("ai", "")])
		for member in tr.get("team", []):
			if not creatures.has(String(member.get("creature", ""))):
				errors.append("Trainer '%s' references unknown creature '%s'." % [tid, member.get("creature", "")])
			for mv in member.get("moves", []):
				if not moves.has(String(mv)):
					errors.append("Trainer '%s' member uses unknown move '%s'." % [tid, mv])

	# Regions reference existing maps + encounter tables + next regions
	for rid in regions.keys():
		var reg: Dictionary = regions[rid]
		if not maps.has(String(reg.get("starting_map", ""))):
			errors.append("Region '%s' starting_map '%s' does not exist." % [rid, reg.get("starting_map", "")])
		for mid in reg.get("maps", []):
			if not maps.has(String(mid)):
				errors.append("Region '%s' lists unknown map '%s'." % [rid, mid])
		var et: String = String(reg.get("regional_rules", {}).get("encounter_table", ""))
		if et != "" and not encounter_tables.has(et):
			errors.append("Region '%s' encounter_table '%s' does not exist." % [rid, et])
		for nr in reg.get("next_regions", []):
			if not regions.has(String(nr)):
				errors.append("Region '%s' next_regions references unknown region '%s'." % [rid, nr])

	# Maps: warps/doors reference existing maps
	for mid in maps.keys():
		for obj in maps[mid].get("objects", []):
			var k := String(obj.get("type", ""))
			if k in ["warp", "door"]:
				if not maps.has(String(obj.get("to_map", ""))):
					errors.append("Map '%s' %s targets unknown map '%s'." % [mid, k, obj.get("to_map", "")])
			elif k == "trainer":
				if not trainers.has(String(obj.get("trainer_id", ""))):
					errors.append("Map '%s' trainer object references unknown trainer '%s'." % [mid, obj.get("trainer_id", "")])
			elif k == "item":
				if not items.has(String(obj.get("item", ""))):
					errors.append("Map '%s' item object references unknown item '%s'." % [mid, obj.get("item", "")])

	# Quests reference existing rewards items/regions
	for qid in quests.keys():
		for rw in quests[qid].get("rewards", []):
			match String(rw.get("kind", "")):
				"item":
					if not items.has(String(rw.get("item", ""))):
						errors.append("Quest '%s' rewards unknown item '%s'." % [qid, rw.get("item", "")])
				"unlock_region":
					if not regions.has(String(rw.get("region", ""))):
						errors.append("Quest '%s' unlocks unknown region '%s'." % [qid, rw.get("region", "")])
	return errors

func _detect_evolution_cycles() -> Array:
	var errors: Array = []
	# Build adjacency from evolves_to on creatures.
	for start in creatures.keys():
		var seen := {}
		var stack := [start]
		while not stack.is_empty():
			var cur: String = stack.pop_back()
			if cur == start and seen.size() > 0:
				errors.append("Circular evolution detected involving '%s'." % start)
				break
			if seen.has(cur):
				continue
			seen[cur] = true
			for nxt in creatures.get(cur, {}).get("evolves_to", []):
				if String(nxt) == start:
					errors.append("Circular evolution detected involving '%s'." % start)
				else:
					stack.append(String(nxt))
	return errors

# ------------------------------------------------------------------ io helpers

func _load_json(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		load_errors.append("Missing data file: %s" % path)
		return {}
	var f := FileAccess.open(path, FileAccess.READ)
	var text := f.get_as_text()
	f.close()
	var parsed = JSON.parse_string(text)
	if parsed == null:
		load_errors.append("Invalid JSON in %s" % path)
		return {}
	if parsed is Dictionary:
		return parsed
	load_errors.append("Top-level JSON in %s must be an object." % path)
	return {}

func _list_json(dir_path: String) -> Array:
	var out: Array = []
	var dir := DirAccess.open(dir_path)
	if dir == null:
		return out
	dir.list_dir_begin()
	var name := dir.get_next()
	while name != "":
		if not dir.current_is_dir() and name.ends_with(".json"):
			out.append("%s/%s" % [dir_path, name])
		name = dir.get_next()
	dir.list_dir_end()
	out.sort()
	return out

func _index(records: Array, key: String) -> Dictionary:
	var out: Dictionary = {}
	for r in records:
		if r is Dictionary and r.has(key):
			var k := String(r[key])
			if out.has(k):
				load_errors.append("Duplicate id '%s' detected." % k)
			out[k] = r
	return out
