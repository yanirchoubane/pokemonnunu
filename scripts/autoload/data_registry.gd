extends Node
## DataRegistry (autoload): loads, validates, indexes ALL external content at boot.
## The engine reads game content ONLY through this registry — nothing is hard-coded.
##
## Content sources, in override order (later wins, merged by id):
##   1. res://data                          — original demo content (versioned)
##   2. res://user_content/canonical_data   — user-supplied packs (NOT versioned)
##   3. user://user_content/canonical_data  — user-supplied packs (exported builds)
## A "pack" is either loose category folders directly under canonical_data/, or a
## subfolder per pack (optionally with a pack.json manifest: id, display_name,
## priority). The engine never downloads anything: users add only data they
## created themselves or otherwise have the right to use. See USER_CONTENT_GUIDE.md.

const DATA_ROOT := "res://data"
const USER_DATA_ROOTS: Array[String] = [
	"res://user_content/canonical_data",
	"user://user_content/canonical_data",
]
const USER_LOCALE_ROOTS: Array[String] = [
	"res://user_content/localization",
	"user://user_content/localization",
]

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
var dialogs: Dictionary = {}        # id -> branching dialog script
var endings: Array = []             # ordered ending records
var strings: Dictionary = {}        # lang -> {key -> text}
var balancing: Dictionary = {}
var adaptive_config: Dictionary = {}
var content_packs: Array = []       # names of user packs applied (for display/debug)

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
	# All dialog files in the folder are merged (by id), so story arcs can live in
	# their own files (base and user packs alike).
	dialogs.clear()
	for path in _list_json("%s/dialogs" % DATA_ROOT):
		for d in _load_json(path).get("dialogs", []):
			if d is Dictionary and d.has("id"):
				dialogs[String(d["id"])] = d
	endings = _load_json("%s/endings/endings.json" % DATA_ROOT).get("endings", [])
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

	# Localization: data/localization/<lang>.json
	strings.clear()
	for path in _list_json("%s/localization" % DATA_ROOT):
		_merge_locale_file(path)

	# User content packs overlay the base data (merged by id, later packs win).
	content_packs.clear()
	for root in USER_DATA_ROOTS:
		_load_user_packs(root)
	for root in USER_LOCALE_ROOTS:
		for path in _list_json(root):
			_merge_locale_file(path)
	_rebuild_evolution_index()

# ---------------------------------------------------------------- user packs

## A pack directory mirrors data/'s layout. Every *.json inside a known category
## folder contributes records that override/extend the base set by id.
func _load_user_packs(root: String) -> void:
	if DirAccess.open(root) == null:
		return
	var pack_dirs: Array = []
	# Loose category folders directly under the root count as one implicit pack.
	pack_dirs.append(root)
	var dir := DirAccess.open(root)
	dir.list_dir_begin()
	var name := dir.get_next()
	while name != "":
		if dir.current_is_dir() and not name.begins_with("."):
			pack_dirs.append("%s/%s" % [root, name])
		name = dir.get_next()
	dir.list_dir_end()
	pack_dirs.sort()

	for pack_dir in pack_dirs:
		if _apply_pack(pack_dir):
			var manifest := _load_json_optional("%s/pack.json" % pack_dir)
			content_packs.append(String(manifest.get("display_name", pack_dir.get_file() if pack_dir != root else "(loose files)")))

## Returns true if the directory contributed at least one record.
func _apply_pack(pack_dir: String) -> bool:
	var contributed := false
	var array_categories := {
		"creatures": ["creatures", creatures],
		"moves": ["moves", moves],
		"abilities": ["abilities", abilities],
		"items": ["items", items],
		"encounters": ["tables", encounter_tables],
		"trainers": ["trainers", trainers],
		"quests": ["quests", quests],
		"dialogs": ["dialogs", dialogs],
	}
	for cat in array_categories.keys():
		var list_key: String = array_categories[cat][0]
		var target: Dictionary = array_categories[cat][1]
		for path in _list_json("%s/%s" % [pack_dir, cat]):
			for rec in _load_json(path).get(list_key, []):
				if rec is Dictionary and rec.has("id"):
					target[String(rec["id"])] = rec
					contributed = true
	# Evolutions: override by id (index rebuilt after all packs).
	for path in _list_json("%s/evolutions" % pack_dir):
		for rec in _load_json(path).get("evolutions", []):
			if rec is Dictionary and rec.has("id"):
				_upsert_evolution(rec)
				contributed = true
	# Endings: override by id, appended otherwise (array order = priority).
	for path in _list_json("%s/endings" % pack_dir):
		for rec in _load_json(path).get("endings", []):
			if rec is Dictionary and rec.has("id"):
				_upsert_ending(rec)
				contributed = true
	# Types: merge type list by id and overlay chart rows.
	for path in _list_json("%s/types" % pack_dir):
		var td := _load_json(path)
		if not td.is_empty():
			_merge_types(td)
			contributed = true
	# Regions + maps.
	for path in _list_json("%s/regions" % pack_dir):
		var r := _load_json(path)
		if r.has("id"):
			regions[String(r["id"])] = r
			contributed = true
	for path in _list_json("%s/regions/maps" % pack_dir) + _list_json("%s/maps" % pack_dir):
		var m := _load_json(path)
		if m.has("id"):
			maps[String(m["id"])] = m
			contributed = true
	# Balancing: shallow per-section merge so a pack can tune one section only.
	for path in _list_json("%s/balancing" % pack_dir):
		var b := _load_json(path)
		var target_cfg := adaptive_config if path.get_file() == "adaptive.json" else balancing
		for k in b.keys():
			if not String(k).begins_with("$"):
				target_cfg[k] = b[k]
				contributed = true
	# Pack-local localization.
	for path in _list_json("%s/localization" % pack_dir):
		_merge_locale_file(path)
		contributed = true
	return contributed

func _upsert_evolution(rec: Dictionary) -> void:
	for i in evolutions.size():
		if String(evolutions[i].get("id", "")) == String(rec["id"]):
			evolutions[i] = rec
			return
	evolutions.append(rec)

func _upsert_ending(rec: Dictionary) -> void:
	for i in endings.size():
		if String(endings[i].get("id", "")) == String(rec["id"]):
			endings[i] = rec
			return
	endings.append(rec)

func _merge_types(td: Dictionary) -> void:
	var by_id := {}
	for t in types_data.get("types", []):
		by_id[String(t["id"])] = t
	for t in td.get("types", []):
		if t is Dictionary and t.has("id"):
			by_id[String(t["id"])] = t
	types_data["types"] = by_id.values()
	var chart: Dictionary = types_data.get("chart", {})
	for atk in td.get("chart", {}).keys():
		if not chart.has(atk):
			chart[atk] = {}
		for def in td["chart"][atk].keys():
			chart[atk][def] = td["chart"][atk][def]
	types_data["chart"] = chart

func _rebuild_evolution_index() -> void:
	evolutions_by_from.clear()
	for e in evolutions:
		evolutions_by_from[String(e.get("from", ""))] = e

func _merge_locale_file(path: String) -> void:
	var d := _load_json(path)
	var lang := String(d.get("language", path.get_file().get_basename()))
	if not strings.has(lang):
		strings[lang] = {}
	for k in d.get("strings", {}).keys():
		strings[lang][k] = String(d["strings"][k])

# ---------------------------------------------------------------- localization

## Resolve a localization key: current language -> English -> the key itself.
func tr_key(key: String) -> String:
	var lang := String(SettingsManager.get_value("language", "en"))
	if strings.get(lang, {}).has(key):
		return String(strings[lang][key])
	if strings.get("en", {}).has(key):
		return String(strings["en"][key])
	return key

## Dialog/quest text convention: strings starting with '@' are localization keys.
func resolve_text(s: String) -> String:
	return tr_key(s.substr(1)) if s.begins_with("@") else s

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

	# Quest on_complete_actions use known kinds and valid references
	for qid in quests.keys():
		errors.append_array(_validate_actions(quests[qid].get("on_complete_actions", []), "quest '%s' on_complete_actions" % qid))

	# Dialog scripts: node graph integrity + known action kinds
	for did in dialogs.keys():
		var node_ids := {}
		for n in dialogs[did].get("nodes", []):
			node_ids[String(n.get("id", ""))] = true
		for n in dialogs[did].get("nodes", []):
			var nid := String(n.get("id", "?"))
			var nxt := String(n.get("next", ""))
			if nxt != "" and not node_ids.has(nxt):
				errors.append("Dialog '%s' node '%s' jumps to unknown node '%s'." % [did, nid, nxt])
			for ch in n.get("choices", []):
				var cnxt := String(ch.get("next", ""))
				if cnxt != "" and not node_ids.has(cnxt):
					errors.append("Dialog '%s' node '%s' choice jumps to unknown node '%s'." % [did, nid, cnxt])
				errors.append_array(_validate_actions(ch.get("actions", []), "dialog '%s' node '%s'" % [did, nid]))
			errors.append_array(_validate_actions(n.get("actions", []), "dialog '%s' node '%s'" % [did, nid]))

	# Maps: npc dialog_id references
	for mid in maps.keys():
		for obj in maps[mid].get("objects", []):
			if String(obj.get("type", "")) == "npc" and obj.has("dialog_id"):
				if not dialogs.has(String(obj["dialog_id"])):
					errors.append("Map '%s' npc references unknown dialog '%s'." % [mid, obj["dialog_id"]])
	return errors

const VALID_ACTION_KINDS := [
	"set_flag", "clear_flag", "set_var", "add_var", "adjust_relationship",
	"give_item", "take_item", "add_money", "start_quest", "heal_team",
	"unlock_region", "inc_counter", "trigger_ending",
]

func _validate_actions(actions: Array, where: String) -> Array:
	var errors: Array = []
	for a in actions:
		var kind := String(a.get("kind", ""))
		if not (kind in VALID_ACTION_KINDS):
			errors.append("Unknown action kind '%s' in %s." % [kind, where])
		elif kind == "give_item" or kind == "take_item":
			if not items.has(String(a.get("item", ""))):
				errors.append("Action in %s references unknown item '%s'." % [where, a.get("item", "")])
		elif kind == "start_quest":
			if not quests.has(String(a.get("quest", ""))):
				errors.append("Action in %s references unknown quest '%s'." % [where, a.get("quest", "")])
		elif kind == "unlock_region":
			if not regions.has(String(a.get("region", ""))):
				errors.append("Action in %s references unknown region '%s'." % [where, a.get("region", "")])
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

## Like _load_json but a missing file is fine (used for optional pack manifests).
func _load_json_optional(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		return {}
	return _load_json(path)

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
