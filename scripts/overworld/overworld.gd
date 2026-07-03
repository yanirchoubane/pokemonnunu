extends Node2D
## Overworld controller: renders a data-defined grid map, moves the player tile-by-tile
## with collisions, and handles interaction (NPCs, signs, items, shop, heal), warps,
## trainer line-of-sight battles, and random encounters in tall grass.

const WALKABLE := {
	"ground": true, "path": true, "floor": true, "sand": true, "stone": true,
	"tall_grass": true, "heal_pad": true, "door": true,
}
const MOVE_TIME := 0.14
const DIRS := {
	"up": Vector2i(0, -1), "down": Vector2i(0, 1), "left": Vector2i(-1, 0), "right": Vector2i(1, 0),
}

var map_id: String = ""
var map_data: Dictionary = {}
var tile_size: int = 32
var grid_w: int = 0
var grid_h: int = 0
var rows: Array = []
var legend: Dictionary = {}
var objects_by_pos: Dictionary = {}   # Vector2i -> Array[object]
var encounter_table_id: String = ""

var player_grid: Vector2i = Vector2i.ZERO
var facing: String = "down"
var moving: bool = false
var move_t: float = 0.0
var move_from: Vector2 = Vector2.ZERO
var move_to: Vector2 = Vector2.ZERO
var player_pixel: Vector2 = Vector2.ZERO
var steps_since_encounter: int = 0
var input_locked: bool = false

var camera: Camera2D
var dialog: DialogBox
var _npc_sprites: Dictionary = {}

func _ready() -> void:
	dialog = DialogBox.new()
	add_child(dialog)
	camera = Camera2D.new()
	camera.zoom = Vector2(2, 2)
	add_child(camera)
	GameState.ending_triggered.connect(_on_ending_triggered)
	_resolve_spawn()
	_load_map(map_id)
	_place_player_from_spawn()
	_check_region_visit()
	queue_redraw()

var _pending_ending: Dictionary = {}

## Endings can fire mid-dialog (a choice action) or from quest completion, while
## the DialogBox is busy. Store the ending and play it from _process once the
## current interaction has fully released the dialog — no re-entrancy.
func _on_ending_triggered(ending: Dictionary) -> void:
	_pending_ending = ending

## Show the epilogue chosen by the endings data, autosave, and return to the
## title screen. The save stays fully playable afterwards (post-game).
func _show_ending(ending: Dictionary) -> void:
	input_locked = true
	var lines: Array = []
	for l in ending.get("lines", []):
		lines.append(_interpolate(DataRegistry.resolve_text(String(l))))
	lines.append("%s  %s" % [DataRegistry.tr_key("ending.the_end"), String(ending.get("title", ""))])
	await dialog.show_lines(lines)
	SaveManager.autosave()
	SceneRouter.to_title()

func _resolve_spawn() -> void:
	if not SceneRouter.pending_spawn.is_empty():
		map_id = String(SceneRouter.pending_spawn.get("map", ""))
	else:
		map_id = String(GameState.player.get("position", {}).get("map", ""))
	if map_id == "" or not DataRegistry.maps.has(map_id):
		map_id = DataRegistry.regions.get(GameState.current_region, {}).get("starting_map", "verdantia_town")

func _load_map(id: String) -> void:
	map_data = DataRegistry.maps.get(id, {})
	tile_size = int(map_data.get("tile_size", 32))
	rows = map_data.get("rows", [])
	legend = map_data.get("legend", {})
	grid_h = rows.size()
	grid_w = rows[0].length() if grid_h > 0 else 0
	objects_by_pos.clear()
	encounter_table_id = ""
	for obj in map_data.get("objects", []):
		var t := String(obj.get("type", ""))
		if t == "encounter_zone":
			encounter_table_id = String(obj.get("table", ""))
			continue
		# Already-collected pickups stay collected across map reloads.
		if t == "item" and String(obj.get("flag", "")) != "" and GameState.get_flag(String(obj.get("flag", ""))):
			continue
		if obj.has("x") and obj.has("y"):
			var p := Vector2i(int(obj["x"]), int(obj["y"]))
			if not objects_by_pos.has(p):
				objects_by_pos[p] = []
			objects_by_pos[p].append(obj)
	AudioManager.play_zone_music(String(map_data.get("bgm", "town")))

func _place_player_from_spawn() -> void:
	var spawn_id := String(SceneRouter.pending_spawn.get("spawn", "")) if not SceneRouter.pending_spawn.is_empty() else ""
	var placed := false
	if spawn_id != "":
		for obj in map_data.get("objects", []):
			if String(obj.get("type", "")) == "spawn" and String(obj.get("id", "")) == spawn_id:
				player_grid = Vector2i(int(obj["x"]), int(obj["y"]))
				placed = true
				break
	if not placed:
		# restore saved position on this map, else default spawn
		var pos: Dictionary = GameState.player.get("position", {})
		if String(pos.get("map", "")) == map_id:
			player_grid = Vector2i(int(pos.get("x", 1)), int(pos.get("y", 1)))
			facing = String(pos.get("facing", "down"))
			placed = true
	if not placed:
		for obj in map_data.get("objects", []):
			if String(obj.get("type", "")) == "spawn" and String(obj.get("id", "")) == "default":
				player_grid = Vector2i(int(obj["x"]), int(obj["y"]))
				placed = true
				break
	if not placed:
		player_grid = Vector2i(grid_w / 2, grid_h / 2)
	player_pixel = _grid_to_pixel(player_grid)
	camera.global_position = player_pixel
	SceneRouter.pending_spawn = {}
	_save_position()

func _check_region_visit() -> void:
	var region := String(map_data.get("region", ""))
	if region != "" and region != GameState.current_region:
		GameState.mark_region_visited(region)
	elif region != "" and not bool(GameState.region_progress.get(region, {}).get("visited", false)):
		GameState.mark_region_visited(region)

func _grid_to_pixel(g: Vector2i) -> Vector2:
	return Vector2(g.x * tile_size + tile_size / 2.0, g.y * tile_size + tile_size / 2.0)

func _tile_type(g: Vector2i) -> String:
	if g.y < 0 or g.y >= grid_h or g.x < 0 or g.x >= grid_w:
		return "wall"
	var ch := String(rows[g.y]).substr(g.x, 1)
	return String(legend.get(ch, "wall"))

func _is_walkable(g: Vector2i) -> bool:
	if not WALKABLE.get(_tile_type(g), false):
		return false
	# Blocking objects. A defeated trainer (its flag is set) no longer blocks the tile,
	# so the player can pass to whatever lies beyond them (e.g. the gym's port warp).
	for obj in objects_by_pos.get(g, []):
		var t := String(obj.get("type", ""))
		if t in ["npc", "sign", "shop"]:
			return false
		if t == "trainer" and not GameState.get_flag(String(obj.get("flag", ""))):
			return false
	return true

# ------------------------------------------------------------------ input / movement

func _process(delta: float) -> void:
	if moving:
		move_t += delta / MOVE_TIME
		if move_t >= 1.0:
			move_t = 1.0
			moving = false
			player_pixel = move_to
			_on_arrive()
		else:
			player_pixel = move_from.lerp(move_to, move_t)
		camera.global_position = player_pixel
		queue_redraw()
		return
	if input_locked:
		return
	if not _pending_ending.is_empty():
		var e: Dictionary = _pending_ending
		_pending_ending = {}
		_show_ending(e)  # async: locks input itself, ends at the title screen
		return
	if not GameState.pending_warp.is_empty():
		# Ferry travel requested from a dialog; execute once the dialog is done.
		var w: Dictionary = GameState.pending_warp
		GameState.pending_warp = {}
		input_locked = true
		SceneRouter.to_overworld(String(w.get("map", "")), String(w.get("spawn", "default")))
		return
	if Input.is_action_just_pressed("menu"):
		_open_pause_menu()
		return
	if Input.is_action_just_pressed("dev_menu") and SettingsManager.is_developer():
		_open_dev_menu()
		return
	if Input.is_action_just_pressed("interact"):
		_interact()
		return
	for dir in DIRS.keys():
		if Input.is_action_pressed("move_" + dir):
			_try_move(dir)
			break

func _try_move(dir: String) -> void:
	facing = dir
	var target: Vector2i = player_grid + DIRS[dir]
	if _is_walkable(target):
		player_grid = target
		move_from = player_pixel
		move_to = _grid_to_pixel(target)
		move_t = 0.0
		moving = true
	else:
		queue_redraw()  # update facing

func _on_arrive() -> void:
	_save_position()
	# Item pickup
	for obj in objects_by_pos.get(player_grid, []).duplicate():
		if String(obj.get("type", "")) == "item":
			_pickup_item(obj)
	# Warp
	for obj in objects_by_pos.get(player_grid, []):
		if String(obj.get("type", "")) in ["warp", "door"]:
			_use_warp(obj)
			return
	# Heal pad
	for obj in objects_by_pos.get(player_grid, []):
		if String(obj.get("type", "")) == "heal":
			_do_heal(obj)
	# Trainer line-of-sight
	if _check_trainer_sight():
		return
	# Random encounter
	if _tile_type(player_grid) == "tall_grass" and encounter_table_id != "":
		_maybe_encounter()

func _save_position() -> void:
	GameState.player["position"] = {"map": map_id, "x": player_grid.x, "y": player_grid.y, "facing": facing}

# ------------------------------------------------------------------ interaction

func _interact() -> void:
	var front: Vector2i = player_grid + DIRS[facing]
	for obj in objects_by_pos.get(front, []):
		match String(obj.get("type", "")):
			"npc":
				_talk_npc(obj)
				return
			"sign":
				_show_dialog([String(obj.get("text", "..."))])
				return
			"shop":
				_open_shop(obj)
				return
			"trainer":
				if GameState.get_flag(String(obj.get("flag", ""))):
					# Already defeated: chat instead of an infinite reward re-battle.
					var tr: Dictionary = DataRegistry.trainers.get(String(obj.get("trainer_id", "")), {})
					_show_dialog([String(tr.get("dialogue_defeat", "You already bested me."))])
				else:
					_start_trainer_battle(obj)
				return
			"heal":
				_do_heal(obj)
				return

func _talk_npc(obj: Dictionary) -> void:
	input_locked = true
	if obj.has("starter_choice") and not GameState.get_flag(String(obj.get("flag", "got_starter"))):
		await _starter_selection(obj)
	elif obj.has("dialog_id"):
		await _run_dialog_script(String(obj["dialog_id"]))
	else:
		await _show_dialog(obj.get("dialogue", ["..."]))
	input_locked = false

## Run a data-driven branching dialog script (see data/dialogs/dialogs.json).
## Entry point = first node whose condition passes (nodes with entry:false are
## reachable only via 'next'). Each node: lines -> actions -> choices/next.
func _run_dialog_script(dialog_id: String) -> void:
	var script: Dictionary = DataRegistry.dialogs.get(dialog_id, {})
	var nodes: Array = script.get("nodes", [])
	var by_id := {}
	for n in nodes:
		by_id[String(n.get("id", ""))] = n
	var current: Dictionary = {}
	for n in nodes:
		if not bool(n.get("entry", true)):
			continue
		if GameState.condition_met(n.get("condition", {})) or not n.has("condition"):
			current = n
			break
	var hops := 0
	while not current.is_empty() and hops < 50:
		hops += 1
		dialog.set_portrait(AssetResolver.portrait(String(current.get("portrait", ""))))
		var lines: Array = []
		for l in current.get("lines", []):
			lines.append(_interpolate(DataRegistry.resolve_text(String(l))))
		if not lines.is_empty():
			await dialog.show_lines(lines)
		GameState.apply_actions(current.get("actions", []))
		# Choices may carry a "condition"; only the ones that pass are offered
		# (this is how the ferry lists only the regions you have visited).
		var choices: Array = []
		for ch in current.get("choices", []):
			if ch is Dictionary and (not ch.has("condition") or GameState.condition_met(ch.get("condition", {}))):
				choices.append(ch)
		var next_id := String(current.get("next", ""))
		if not choices.is_empty():
			var texts: Array = []
			for ch in choices:
				texts.append(_interpolate(DataRegistry.resolve_text(String(ch.get("text", "...")))))
			var pick := await dialog.show_choice(_interpolate(String(current.get("prompt", "..."))), texts)
			var chosen: Dictionary = choices[pick]
			GameState.apply_actions(chosen.get("actions", []))
			next_id = String(chosen.get("next", ""))
		current = by_id.get(next_id, {}) if next_id != "" else {}
	dialog.set_portrait(null)

## Substitute narrative placeholders in display text.
func _interpolate(s: String) -> String:
	return s.replace("${player}", String(GameState.player.get("name", "?")))

func _starter_selection(obj: Dictionary) -> void:
	var choices: Array = obj.get("starter_choice", [])
	await dialog.show_lines(obj.get("dialogue", ["Choose your partner."]))
	var names: Array = []
	for cid in choices:
		names.append(String(DataRegistry.creatures.get(String(cid), {}).get("display_name", cid)))
	var idx: int = await dialog.show_choice("Which partner will you choose?", names)
	var species_id := String(choices[idx])
	var starter := GameState.build_creature(species_id, 5)
	GameState.add_creature(starter)
	GameState.set_flag(String(obj.get("flag", "got_starter")))
	await dialog.show_lines(["You chose %s! Your journey begins." % starter.display_name()])

func _show_dialog(lines: Array) -> void:
	input_locked = true
	await dialog.show_lines(lines)
	input_locked = false

func _pickup_item(obj: Dictionary) -> void:
	var flag := String(obj.get("flag", ""))
	if flag != "" and GameState.get_flag(flag):
		return
	var item_id := String(obj.get("item", ""))
	var qty := int(obj.get("quantity", 1))
	GameState.give_item(item_id, qty)
	if flag != "":
		GameState.set_flag(flag)
	objects_by_pos[player_grid].erase(obj)
	var item_name := String(DataRegistry.items.get(item_id, {}).get("display_name", item_id))
	AudioManager.play_sfx("confirm")
	_show_dialog(["You found %d x %s!" % [qty, item_name]])

func _do_heal(obj: Dictionary) -> void:
	GameState.heal_team()
	AudioManager.play_sfx("heal")
	if bool(obj.get("sets_respawn", false)):
		# Use a spawn id that actually exists on this map (not every map has "entrance").
		var spawn_id := String(obj.get("respawn_spawn", "entrance"))
		if not _map_has_spawn(spawn_id):
			spawn_id = "default"
		GameState.player["respawn"] = {"map": map_id, "spawn": spawn_id}
	_show_dialog(["Your team is fully healed!"])

func _map_has_spawn(spawn_id: String) -> bool:
	for obj in map_data.get("objects", []):
		if String(obj.get("type", "")) == "spawn" and String(obj.get("id", "")) == spawn_id:
			return true
	return false

# ------------------------------------------------------------------ warps / regions

func _use_warp(obj: Dictionary) -> void:
	var req := String(obj.get("requires_flag", ""))
	if req != "" and not GameState.get_flag(req):
		_show_dialog([String(obj.get("locked_text", "It's locked."))])
		# step back
		player_grid -= DIRS[facing]
		player_pixel = _grid_to_pixel(player_grid)
		camera.global_position = player_pixel
		return
	var to_map := String(obj.get("to_map", ""))
	var to_spawn := String(obj.get("to_spawn", "default"))
	# Track return-trip flag for the inter-region quest.
	var target_region := String(DataRegistry.maps.get(to_map, {}).get("region", ""))
	if target_region == "verdantia" and GameState.get_flag("visited_aquilon"):
		GameState.set_flag("returned_to_verdantia")
	input_locked = true  # freeze the dying scene during the fade-out
	SceneRouter.to_overworld(to_map, to_spawn)

# ------------------------------------------------------------------ trainers & encounters

func _check_trainer_sight() -> bool:
	for pos in objects_by_pos.keys():
		for obj in objects_by_pos[pos]:
			if String(obj.get("type", "")) != "trainer":
				continue
			if GameState.get_flag(String(obj.get("flag", ""))):
				continue
			var tdir := String(obj.get("facing", "down"))
			var sight := int(obj.get("sight", 0))
			if _in_sight_line(pos, tdir, sight, player_grid):
				_start_trainer_battle(obj)
				return true
	return false

func _in_sight_line(tpos: Vector2i, tdir: String, sight: int, ppos: Vector2i) -> bool:
	var d: Vector2i = DIRS.get(tdir, Vector2i.ZERO)
	for step in range(1, sight + 1):
		var cell: Vector2i = tpos + d * step
		if cell == ppos:
			return true
		if not WALKABLE.get(_tile_type(cell), false):
			break
	return false

func _has_battler() -> bool:
	return GameState.team_first_alive() != -1

func _start_trainer_battle(obj: Dictionary) -> void:
	if not _has_battler():
		_show_dialog(["You have no creature able to battle! Visit the Professor's lab first."])
		return
	input_locked = true
	var trainer_id := String(obj.get("trainer_id", ""))
	var tr: Dictionary = DataRegistry.trainers.get(trainer_id, {})
	await dialog.show_lines([String(tr.get("dialogue_intro", "Let's battle!"))])
	SceneRouter.to_battle({
		"kind": "trainer",
		"trainer_id": trainer_id,
		"return_map": map_id,
		"return_pos": {"x": player_grid.x, "y": player_grid.y, "facing": facing},
	})

func _maybe_encounter() -> void:
	if not _has_battler():
		return
	steps_since_encounter += 1
	var base_rate := 0.14
	var rate := base_rate * AdaptiveDirector.get_encounter_rate_multiplier()
	# small ramp so you don't wait forever
	rate += min(0.1, steps_since_encounter * 0.01)
	if GameState.rng.chance(rate):
		steps_since_encounter = 0
		_start_wild_encounter()

func _start_wild_encounter() -> void:
	input_locked = true
	var table: Dictionary = DataRegistry.encounter_tables.get(encounter_table_id, {})
	var entries: Array = table.get("entries", [])
	if entries.is_empty():
		input_locked = false
		return
	var weights: Array = []
	for e in entries:
		weights.append(float(e.get("weight", 1)))
	var idx := GameState.rng.weighted_index(weights)
	var entry: Dictionary = entries[idx]
	var level := GameState.rng.randi_range(int(entry.get("level_min", 2)), int(entry.get("level_max", 5)))
	SceneRouter.to_battle({
		"kind": "wild",
		"species_id": String(entry.get("creature", "")),
		"level": level,
		"return_map": map_id,
		"return_pos": {"x": player_grid.x, "y": player_grid.y, "facing": facing},
	})

# ------------------------------------------------------------------ menus

## Unlock player input on the NEXT frame. Menus close on a key press that is still
## "just pressed" during this frame's _process — unlocking immediately would make
## _process reopen the menu (or trigger an interaction) with the same press.
func _unlock_input_deferred() -> void:
	await get_tree().process_frame
	input_locked = false

func _open_pause_menu() -> void:
	input_locked = true
	# Untyped on purpose: load() returns Resource, so ':=' cannot infer a type here
	# (compile error in 4.2), and the concrete scene scripts expose custom members.
	var menu = load("res://scenes/ui/pause_menu.tscn").instantiate()
	add_child(menu)
	menu.closed.connect(_unlock_input_deferred)

func _open_shop(obj: Dictionary) -> void:
	input_locked = true
	var shop = load("res://scenes/ui/shop.tscn").instantiate()
	shop.stock = obj.get("stock", [])
	add_child(shop)
	shop.closed.connect(_unlock_input_deferred)

func _open_dev_menu() -> void:
	input_locked = true
	var dev = load("res://scenes/ui/dev_menu.tscn").instantiate()
	add_child(dev)
	dev.closed.connect(_unlock_input_deferred)

# ------------------------------------------------------------------ rendering

func _draw() -> void:
	if grid_h == 0:
		return
	# Tiles
	for y in grid_h:
		for x in grid_w:
			var g := Vector2i(x, y)
			var col := PlaceholderGfx.tile_color(_tile_type(g))
			draw_rect(Rect2(x * tile_size, y * tile_size, tile_size, tile_size), col)
			# subtle grid line for tall grass
			if _tile_type(g) == "tall_grass":
				draw_rect(Rect2(x * tile_size + 4, y * tile_size + 4, tile_size - 8, tile_size - 8), col.darkened(0.15), false, 2.0)
	# Objects
	for pos in objects_by_pos.keys():
		for obj in objects_by_pos[pos]:
			var t := String(obj.get("type", ""))
			var center := Vector2(pos.x * tile_size + tile_size / 2.0, pos.y * tile_size + tile_size / 2.0)
			match t:
				"npc":
					_draw_marker(center, Color("#d6b24c"))
				"trainer":
					if not GameState.get_flag(String(obj.get("flag", ""))):
						_draw_marker(center, Color("#d65c5c"))
				"sign":
					draw_rect(Rect2(center.x - 8, center.y - 8, 16, 16), Color("#8a6d3b"))
				"shop":
					_draw_marker(center, Color("#4c9bd5"))
				"item":
					draw_circle(center, 6, Color("#f2d24c"))
				"warp", "door":
					draw_rect(Rect2(pos.x * tile_size + 6, pos.y * tile_size + 6, tile_size - 12, tile_size - 12), Color("#3a2a1a"), false, 2.0)
	# Player
	_draw_player()

func _draw_ring(center: Vector2, radius: float, color: Color, width: float) -> void:
	draw_arc(center, radius, 0.0, TAU, 24, color, width)

func _draw_marker(center: Vector2, color: Color) -> void:
	draw_circle(center, tile_size * 0.35, color)
	_draw_ring(center, tile_size * 0.35, Color.BLACK, 1.5)

func _draw_player() -> void:
	var color := Color(GameState.player.get("appearance", {}).get("color", "#3a7bd5"))
	draw_circle(player_pixel, tile_size * 0.35, color)
	_draw_ring(player_pixel, tile_size * 0.35, Color.WHITE, 2.0)
	# facing indicator
	var d: Vector2 = Vector2(DIRS[facing])
	draw_line(player_pixel, player_pixel + d * (tile_size * 0.3), Color.WHITE, 3.0)
