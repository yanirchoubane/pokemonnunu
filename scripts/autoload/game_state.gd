extends Node
## GameState (autoload): the live, save-able world state (player, team, box, bag,
## flags, counters, quests, region progression). Emits signals the quest/UI layers
## listen to. Never stores engine/scene objects — only serializable data + live
## CreatureInstance objects (which serialize themselves).

signal flag_set(flag: String)
signal counter_changed(counter: String, value: int)
signal money_changed(amount: int)
signal team_changed
signal region_changed(region_id: String)
signal quest_updated(quest_id: String)
signal ending_triggered(ending: Dictionary)

var initialized: bool = false
var rng_seed: int = 123456789
var rng: RNG = RNG.new()

var player: Dictionary = {}
var team: Array = []          # Array[CreatureInstance]
var box: Array = []           # Array[CreatureInstance]
var inventory: Dictionary = {} # item_id -> qty
var flags: Dictionary = {}
var counters: Dictionary = {}
var story_vars: Dictionary = {}       # narrative variables: name -> int|String
var relationships: Dictionary = {}    # npc_id -> int score (choices shift it)
var badges: Array = []
var quests: Dictionary = {}    # quest_id -> { state, objectives: {obj_id: bool}, started: bool }
var region_progress: Dictionary = {} # region_id -> { unlocked, visited, completed }
var current_region: String = ""
var playtime_seconds: float = 0.0
var adaptive_state: Dictionary = {}   # owned by AdaptiveDirector, stored here for save

func _process(delta: float) -> void:
	if initialized:
		playtime_seconds += delta

func new_game(player_name: String, gender: String, start_region: String, seed_value: int = 0) -> void:
	rng_seed = seed_value if seed_value != 0 else 0x51ED5EED
	rng = RNG.new(rng_seed)
	var eco: Dictionary = DataRegistry.economy_cfg()
	player = {
		"name": player_name,
		"gender": gender,
		"appearance": {"color": "#3a7bd5"},
		"money": int(eco.get("starting_money", 1500)),
		"position": {"map": "", "x": 0, "y": 0, "facing": "down"},
		"respawn": {"map": "verdantia_center", "spawn": "entrance"},
	}
	team = []
	box = []
	inventory = {}
	flags = {}
	counters = {}
	story_vars = {}
	relationships = {}
	badges = []
	quests = {}
	region_progress = {}
	playtime_seconds = 0.0
	adaptive_state = {}
	current_region = start_region

	# Unlock the starting region.
	unlock_region(start_region)
	# Starting items.
	give_item("capture_orb", 5)
	give_item("potion", 3)
	# Initialize auto-start quests.
	for qid in DataRegistry.quests.keys():
		if bool(DataRegistry.quests[qid].get("auto_start", false)):
			start_quest(qid)
	initialized = true

# ------------------------------------------------------------------ creatures

func build_creature(species_id: String, level: int, opts: Dictionary = {}) -> CreatureInstance:
	var species: Dictionary = DataRegistry.creatures.get(species_id, {})
	if species.is_empty():
		push_error("Unknown species '%s'" % species_id)
	return CreatureFactory.build(species, level, rng, DataRegistry.moves, opts)

func add_creature(c: CreatureInstance) -> String:
	var maxsize: int = int(DataRegistry.party_cfg().get("max_team_size", 6))
	if team.size() < maxsize:
		team.append(c)
		team_changed.emit()
		return "team"
	box.append(c)
	team_changed.emit()
	return "box"

func team_first_alive() -> int:
	for i in team.size():
		if not team[i].is_fainted():
			return i
	return -1

func heal_team() -> void:
	for c in team:
		c.heal_full()
	team_changed.emit()

# ------------------------------------------------------------------ inventory / money

func give_item(item_id: String, qty: int = 1) -> void:
	inventory[item_id] = int(inventory.get(item_id, 0)) + qty

func remove_item(item_id: String, qty: int = 1) -> bool:
	var have: int = int(inventory.get(item_id, 0))
	if have < qty:
		return false
	inventory[item_id] = have - qty
	if inventory[item_id] <= 0:
		inventory.erase(item_id)
	return true

func has_item(item_id: String, qty: int = 1) -> bool:
	return int(inventory.get(item_id, 0)) >= qty

func add_money(amount: int) -> void:
	player["money"] = max(0, int(player.get("money", 0)) + amount)
	money_changed.emit(int(player["money"]))

func get_money() -> int:
	return int(player.get("money", 0))

# ------------------------------------------------------------------ flags / counters

func set_flag(flag: String, value: bool = true) -> void:
	flags[flag] = value
	flag_set.emit(flag)
	_evaluate_quests()

func get_flag(flag: String) -> bool:
	return bool(flags.get(flag, false))

func inc_counter(counter: String, by: int = 1) -> void:
	counters[counter] = int(counters.get(counter, 0)) + by
	counter_changed.emit(counter, int(counters[counter]))
	_evaluate_quests()

func get_counter(counter: String) -> int:
	return int(counters.get(counter, 0))

# ------------------------------------------------------------------ story vars / relationships

func set_var(name: String, value) -> void:
	story_vars[name] = value
	_evaluate_quests()

func get_var(name: String, default_value = null):
	return story_vars.get(name, default_value)

func adjust_relationship(npc_id: String, delta: int) -> void:
	relationships[npc_id] = int(relationships.get(npc_id, 0)) + delta
	_evaluate_quests()

func get_relationship(npc_id: String) -> int:
	return int(relationships.get(npc_id, 0))

# ------------------------------------------------------------------ actions & endings

## Apply a list of data-driven actions (used by dialog scripts and quests).
## Kinds are validated at boot by DataRegistry.VALID_ACTION_KINDS.
func apply_actions(actions: Array) -> void:
	for a in actions:
		match String(a.get("kind", "")):
			"set_flag":
				set_flag(String(a.get("flag", "")))
			"clear_flag":
				flags.erase(String(a.get("flag", "")))
			"set_var":
				set_var(String(a.get("var", "")), a.get("value"))
			"add_var":
				var vn := String(a.get("var", ""))
				set_var(vn, int(story_vars.get(vn, 0)) + int(a.get("delta", 1)))
			"adjust_relationship":
				adjust_relationship(String(a.get("npc", "")), int(a.get("delta", 0)))
			"give_item":
				give_item(String(a.get("item", "")), int(a.get("quantity", 1)))
			"take_item":
				remove_item(String(a.get("item", "")), int(a.get("quantity", 1)))
			"add_money":
				add_money(int(a.get("amount", 0)))
			"start_quest":
				start_quest(String(a.get("quest", "")))
			"heal_team":
				heal_team()
			"unlock_region":
				unlock_region(String(a.get("region", "")))
			"inc_counter":
				inc_counter(String(a.get("counter", "")), int(a.get("by", 1)))
			"trigger_ending":
				trigger_ending()

## Evaluate DataRegistry.endings in order; the first whose condition passes wins.
func evaluate_ending() -> Dictionary:
	for e in DataRegistry.endings:
		if _condition_met(e.get("condition", {})):
			return e
	return {}

func trigger_ending() -> void:
	var e := evaluate_ending()
	if not e.is_empty():
		set_flag("seen_ending_%s" % String(e.get("id", "")))
		ending_triggered.emit(e)

# ------------------------------------------------------------------ regions

func unlock_region(region_id: String) -> void:
	if not region_progress.has(region_id):
		region_progress[region_id] = {"unlocked": true, "visited": false, "completed": false}
	else:
		region_progress[region_id]["unlocked"] = true

func mark_region_visited(region_id: String) -> void:
	unlock_region(region_id)
	region_progress[region_id]["visited"] = true
	current_region = region_id
	set_flag("visited_%s" % region_id)
	region_changed.emit(region_id)

func is_region_unlocked(region_id: String) -> bool:
	return bool(region_progress.get(region_id, {}).get("unlocked", false))

# ------------------------------------------------------------------ quests

func start_quest(quest_id: String) -> void:
	if quests.has(quest_id):
		return
	var q: Dictionary = DataRegistry.quests.get(quest_id, {})
	if q.is_empty():
		return
	var objs: Dictionary = {}
	for o in q.get("objectives", []):
		objs[String(o.get("id", ""))] = false
	quests[quest_id] = {"state": "active", "objectives": objs, "started": true}
	quest_updated.emit(quest_id)
	_evaluate_single_quest(quest_id)

func _evaluate_quests() -> void:
	# Start any quests whose start_condition just became true.
	for qid in DataRegistry.quests.keys():
		var q: Dictionary = DataRegistry.quests[qid]
		if not quests.has(qid) and not bool(q.get("auto_start", false)):
			var sc: Dictionary = q.get("start_condition", {})
			if not sc.is_empty() and _condition_met(sc):
				start_quest(qid)
	for qid in quests.keys():
		_evaluate_single_quest(qid)

func _evaluate_single_quest(quest_id: String) -> void:
	var qstate: Dictionary = quests.get(quest_id, {})
	if qstate.get("state", "") != "active":
		return
	var qdef: Dictionary = DataRegistry.quests.get(quest_id, {})
	var all_done: bool = true
	for o in qdef.get("objectives", []):
		var oid := String(o.get("id", ""))
		if not bool(qstate["objectives"].get(oid, false)):
			if _condition_met(o.get("condition", {})):
				qstate["objectives"][oid] = true
				quest_updated.emit(quest_id)
			else:
				all_done = false
	if all_done and qdef.get("objectives", []).size() > 0:
		_complete_quest(quest_id, qdef)

func _complete_quest(quest_id: String, qdef: Dictionary) -> void:
	quests[quest_id]["state"] = "complete"
	for rw in qdef.get("rewards", []):
		match String(rw.get("kind", "")):
			"money":
				add_money(int(rw.get("amount", 0)))
			"item":
				give_item(String(rw.get("item", "")), int(rw.get("quantity", 1)))
			"unlock_region":
				unlock_region(String(rw.get("region", "")))
	var cf := String(qdef.get("on_complete_flag", ""))
	if cf != "":
		flags[cf] = true  # set directly to avoid recursive quest evaluation storm
		flag_set.emit(cf)
	# Optional narrative hooks (same action kinds as dialog scripts) — this is how
	# a quest can trigger an ending, shift a relationship, or start a follow-up.
	apply_actions(qdef.get("on_complete_actions", []))
	quest_updated.emit(quest_id)
	# One more pass so quests gated on this flag can start.
	call_deferred("_evaluate_quests")

## Public entry point for other systems (dialog runner, endings, UI).
func condition_met(cond: Dictionary) -> bool:
	return _condition_met(cond)

## Composable condition evaluation, shared by quests, dialog nodes and endings.
func _condition_met(cond: Dictionary) -> bool:
	match String(cond.get("kind", "")):
		"flag":
			return get_flag(String(cond.get("flag", "")))
		"counter":
			return get_counter(String(cond.get("counter", ""))) >= int(cond.get("at_least", 1))
		"var_equals":
			return str(get_var(String(cond.get("var", "")), "")) == str(cond.get("value", ""))
		"var_at_least":
			return int(get_var(String(cond.get("var", "")), 0)) >= int(cond.get("at_least", 1))
		"relationship_at_least":
			return get_relationship(String(cond.get("npc", ""))) >= int(cond.get("at_least", 1))
		"region_visited":
			return bool(region_progress.get(String(cond.get("region", "")), {}).get("visited", false))
		"not":
			return not _condition_met(cond.get("condition", {}))
		"all":
			for c in cond.get("conditions", []):
				if not _condition_met(c):
					return false
			return true
		"any":
			for c in cond.get("conditions", []):
				if _condition_met(c):
					return true
			return false
		_:
			return false

# ------------------------------------------------------------------ serialization

func to_dict() -> Dictionary:
	var team_data: Array = []
	for c in team:
		team_data.append(c.to_dict())
	var box_data: Array = []
	for c in box:
		box_data.append(c.to_dict())
	return {
		"rng_seed": rng_seed,
		"rng_state": rng.get_state(),
		"player": player,
		"team": team_data,
		"box": box_data,
		"inventory": inventory,
		"flags": flags,
		"counters": counters,
		"story_vars": story_vars,
		"relationships": relationships,
		"badges": badges,
		"quests": quests,
		"region_progress": region_progress,
		"current_region": current_region,
		"playtime_seconds": playtime_seconds,
		"adaptive_state": adaptive_state,
	}

func from_dict(d: Dictionary) -> void:
	rng_seed = int(d.get("rng_seed", 123456789))
	rng = RNG.new(rng_seed)
	rng.restore_state(int(d.get("rng_state", rng.get_state())))
	player = d.get("player", {})
	team = []
	for cd in d.get("team", []):
		team.append(CreatureFactory.from_saved(cd, DataRegistry.creatures))
	box = []
	for cd in d.get("box", []):
		box.append(CreatureFactory.from_saved(cd, DataRegistry.creatures))
	inventory = d.get("inventory", {})
	flags = d.get("flags", {})
	counters = d.get("counters", {})
	story_vars = d.get("story_vars", {})
	relationships = d.get("relationships", {})
	badges = d.get("badges", [])
	quests = d.get("quests", {})
	region_progress = d.get("region_progress", {})
	current_region = String(d.get("current_region", ""))
	playtime_seconds = float(d.get("playtime_seconds", 0.0))
	adaptive_state = d.get("adaptive_state", {})
	initialized = true
	team_changed.emit()
