extends Control
## Battle scene: builds the enemy team (with adaptive scaling), drives BattleEngine
## turn by turn, renders a HUD, takes player commands, queries BattleAI for the enemy,
## plays back the event log, and resolves rewards / capture / evolution / defeat.

var engine: BattleEngine
var cfg: Dictionary = {}
var ai_tier: String = "basic"
var is_boss: bool = false
var reward_multiplier: float = 1.0
var trainer: Dictionary = {}
var battle_kind: String = "wild"

var revealed_player_species: Array = []
var items_used: int = 0
var used_type_advantage: bool = false
var start_player_avg: float = 0.0
var start_enemy_avg: float = 0.0
var check_evolution_events: Array = []

# UI
var dialog: DialogBox
var enemy_name_lbl: Label
var enemy_hp_bar: ProgressBar
var player_name_lbl: Label
var player_hp_bar: ProgressBar
var player_hp_text: Label
var enemy_sprite: TextureRect
var player_sprite: TextureRect
var ai_debug_lbl: Label

func _ready() -> void:
	cfg = SceneRouter.pending_battle
	battle_kind = String(cfg.get("kind", "wild"))
	_build_ui()
	_setup_battle()
	AudioManager.play_zone_music("battle")
	await _run_battle()

# ------------------------------------------------------------------ setup

func _setup_battle() -> void:
	var battle_rng := RNG.new(GameState.rng.next_u32())
	var player_team: Array = GameState.team
	var enemy_team: Array = []

	var scaling: Dictionary
	if battle_kind == "trainer":
		trainer = DataRegistry.trainers.get(String(cfg.get("trainer_id", "")), {})
		is_boss = bool(trainer.get("boss", false))
		scaling = AdaptiveDirector.get_enemy_scaling(String(trainer.get("ai", "basic")), is_boss)
		ai_tier = String(scaling.get("ai_tier", "basic"))
		for member in trainer.get("team", []):
			var lvl: int = max(2, int(member.get("level", 5)) + int(scaling.get("level_delta", 0)))
			var c := GameState.build_creature(String(member.get("creature", "")), lvl, {"moves": member.get("moves", [])})
			enemy_team.append(c)
	else:
		scaling = AdaptiveDirector.get_enemy_scaling("basic", false)
		ai_tier = "basic"
		var lvl: int = max(2, int(cfg.get("level", 3)) + int(scaling.get("level_delta", 0)))
		enemy_team.append(GameState.build_creature(String(cfg.get("species_id", "")), lvl))

	reward_multiplier = float(scaling.get("reward_multiplier", 1.0))
	start_player_avg = _avg_level(player_team)
	start_enemy_avg = _avg_level(enemy_team)

	engine = BattleEngine.new()
	engine.setup({
		"type_chart": DataRegistry.type_chart,
		"moves_index": DataRegistry.moves,
		"creatures_index": DataRegistry.creatures,
		"abilities_index": DataRegistry.abilities,
		"battle_cfg": DataRegistry.battle_cfg(),
		"capture_cfg": DataRegistry.capture_cfg(),
		"exp_cfg": DataRegistry.exp_cfg(),
		"rng": battle_rng,
		"player_team": player_team,
		"enemy_team": enemy_team,
		"is_trainer_battle": battle_kind == "trainer",
		"is_boss": is_boss,
		"exp_multiplier": reward_multiplier,
		"reward_multiplier": reward_multiplier,
	})
	_reveal(engine.active_player())
	_update_hud()

func _avg_level(team: Array) -> float:
	if team.is_empty():
		return 1.0
	var s := 0
	for c in team:
		s += c.level
	return float(s) / float(team.size())

# ------------------------------------------------------------------ main loop

func _run_battle() -> void:
	var intro := "A wild %s appeared!" % engine.active_enemy().display_name()
	if battle_kind == "trainer":
		intro = String(trainer.get("dialogue_intro", "%s wants to battle!" % trainer.get("display_name", "Trainer")))
	await dialog.show_lines([intro])

	while not engine.finished:
		if engine.need_player_switch:
			await _forced_switch()
			continue
		var player_action := await _get_player_action()
		if player_action.is_empty():
			continue
		var ai_decision := BattleAI.choose_action(engine, ai_tier, revealed_player_species)
		_show_ai_debug(ai_decision)
		var events := engine.resolve_turn(player_action, ai_decision["action"])
		await _play_events(events)
		if engine.need_player_switch and not engine.finished:
			await _forced_switch()

	await _resolve_outcome()

func _get_player_action() -> Dictionary:
	var choice := await dialog.show_choice("What will %s do?" % engine.active_player().display_name(), ["Fight", "Bag", "Team", "Run"])
	match choice:
		0:
			return await _choose_move()
		1:
			return await _choose_item()
		2:
			return await _choose_switch(false)
		3:
			if battle_kind == "trainer":
				await dialog.show_lines(["You can't flee from a trainer battle!"])
				return {}
			return {"kind": "flee"}
	return {}

func _choose_move() -> Dictionary:
	var active := engine.active_player()
	var names: Array = []
	var indices: Array = []
	for i in active.moves.size():
		var m: Dictionary = active.moves[i]
		var rec: Dictionary = DataRegistry.moves.get(String(m["id"]), {})
		names.append("%s (PP %d/%d)" % [rec.get("display_name", m["id"]), m["pp"], m["max_pp"]])
		indices.append(i)
	names.append("Back")
	var pick := await dialog.show_choice("Choose a move:", names)
	if pick >= indices.size():
		return {}
	if int(active.moves[indices[pick]]["pp"]) <= 0:
		await dialog.show_lines(["No PP left for that move!"])
		return {}
	# Track type advantage usage for the adaptive skill score.
	var rec: Dictionary = DataRegistry.moves.get(String(active.moves[indices[pick]]["id"]), {})
	if DataRegistry.type_chart.effectiveness(String(rec.get("type", "")), engine.active_enemy().types()) > 1.0:
		used_type_advantage = true
	return {"kind": "move", "move_index": indices[pick]}

func _choose_item() -> Dictionary:
	var usable: Array = []
	var labels: Array = []
	for item_id in GameState.inventory.keys():
		var rec: Dictionary = DataRegistry.items.get(item_id, {})
		if bool(rec.get("usable_in_battle", false)) and int(GameState.inventory[item_id]) > 0:
			usable.append(item_id)
			labels.append("%s x%d" % [rec.get("display_name", item_id), GameState.inventory[item_id]])
	if usable.is_empty():
		await dialog.show_lines(["You have no usable items!"])
		return {}
	labels.append("Back")
	var pick := await dialog.show_choice("Use which item?", labels)
	if pick >= usable.size():
		return {}
	var item_id := String(usable[pick])
	var rec: Dictionary = DataRegistry.items.get(item_id, {})
	var use: Dictionary = rec.get("use", {})
	items_used += 1
	match String(use.get("kind", "")):
		"capture":
			if battle_kind == "trainer":
				await dialog.show_lines(["You can't capture a trainer's creature!"])
				items_used -= 1
				return {}
			GameState.remove_item(item_id, 1)
			return {"kind": "capture", "ball_rate": float(use.get("ball_rate", 1.0))}
		"heal_hp", "cure_status", "revive":
			GameState.remove_item(item_id, 1)
			return {"kind": "item", "effect": use, "target_index": engine.p_index}
		_:
			items_used -= 1
			await dialog.show_lines(["You can't use that here."])
			return {}

func _choose_switch(forced: bool) -> Dictionary:
	var labels: Array = []
	var indices: Array = []
	for i in GameState.team.size():
		if i == engine.p_index:
			continue
		var c: CreatureInstance = GameState.team[i]
		var tag := " (fainted)" if c.is_fainted() else ""
		labels.append("%s Lv%d HP %d/%d%s" % [c.display_name(), c.level, c.current_hp, c.max_hp(), tag])
		indices.append(i)
	if not forced:
		labels.append("Back")
	if indices.is_empty():
		await dialog.show_lines(["No other creature can battle!"])
		return {}
	var pick := await dialog.show_choice("Send out which creature?", labels)
	if pick >= indices.size():
		return {}
	if GameState.team[indices[pick]].is_fainted():
		await dialog.show_lines(["That creature has fainted!"])
		return {}
	return {"kind": "switch", "target_index": indices[pick]}

func _forced_switch() -> void:
	await dialog.show_lines(["%s fainted! Choose your next creature." % engine.active_player().display_name()])
	while true:
		var action := await _choose_switch(true)
		if action.is_empty() or action.get("kind") != "switch":
			continue
		var tmp: Array = []
		engine._do_switch("player", int(action["target_index"]), tmp)
		_reveal(engine.active_player())
		_update_hud()
		return

# ------------------------------------------------------------------ event playback

func _play_events(events: Array) -> void:
	var lines: Array = []
	for ev in events:
		var text := _describe_event(ev)
		# Apply HUD-affecting side effects immediately, batch text.
		match String(ev.get("type", "")):
			"switch", "enemy_switch":
				_reveal(engine.active_player())
				_update_hud()
			"damage", "status_damage", "heal":
				_update_hud()
			"faint":
				_update_hud()
		if text != "":
			lines.append(text)
	if not lines.is_empty():
		await dialog.show_lines(lines)
	_update_hud()

func _describe_event(ev: Dictionary) -> String:
	match String(ev.get("type", "")):
		"move_used":
			return "%s used %s!" % [ev.get("user", "?"), ev.get("move", "?")]
		"message":
			return String(ev.get("text", ""))
		"miss":
			return String(ev.get("text", "The attack missed!"))
		"status":
			return "%s was afflicted by %s!" % [ev.get("target", "?"), ev.get("status", "?")]
		"status_damage":
			return "%s is hurt by %s!" % [ev.get("target", "?"), ev.get("status", "?")]
		"stat_stage":
			var dir := "rose" if int(ev.get("stages", 0)) > 0 else "fell"
			return "%s's %s %s!" % [ev.get("target", "?"), ev.get("stat", "?"), dir]
		"faint":
			return "%s fainted!" % ev.get("name", "?")
		"exp_gain":
			return "%s gained %d EXP!" % [ev.get("name", "?"), int(ev.get("amount", 0))]
		"level_up":
			return "%s grew to Lv %d!" % [ev.get("name", "?"), int(ev.get("level", 0))]
		"learn_move":
			return "%s learned %s!" % [ev.get("name", "?"), DataRegistry.moves.get(String(ev.get("move", "")), {}).get("display_name", ev.get("move", "?"))]
		"learn_move_full":
			return "%s wants to learn %s but knows 4 moves already." % [ev.get("name", "?"), ev.get("move", "?")]
		"capture_attempt":
			if bool(ev.get("caught", false)):
				return "Gotcha! %s was caught!" % ev.get("name", "?")
			return "Oh no! %s broke free after %d shake(s)!" % [ev.get("name", "?"), int(ev.get("shakes", 0))]
		"flee":
			return "Got away safely!" if bool(ev.get("success", false)) else "Couldn't escape!"
		"check_evolution":
			check_evolution_events.append(ev)
			return ""
		_:
			return ""

# ------------------------------------------------------------------ outcome

func _resolve_outcome() -> void:
	match engine.winner:
		"player":
			await _on_win()
		"captured":
			await _on_capture()
		"enemy":
			await _on_loss()
		"fled":
			pass
	# Record adaptive metrics (after the whole battle, per the smoothing rule).
	AdaptiveDirector.record_battle_result({
		"won": engine.winner in ["player", "captured", "fled"],
		"flawless": engine.winner == "player" and not _player_took_faint(),
		"items_used": items_used,
		"used_type_advantage": used_type_advantage,
		"level_underdog": start_player_avg < start_enemy_avg,
		"player_avg_level": start_player_avg,
		"enemy_avg_level": start_enemy_avg,
	})
	if bool(SettingsManager.get_value("show_adaptation_summary", false)) and AdaptiveDirector.adaptation_enabled():
		var s := AdaptiveDirector.get_summary()
		await dialog.show_lines(["[Adaptive] Skill %.0f/100, enemy level delta %+d." % [s["skill_score"], s["current_level_delta"]]])
	_apply_evolutions_then_return()

func _on_win() -> void:
	if battle_kind == "trainer":
		var reward := int(int(trainer.get("reward_money", 0)) * reward_multiplier)
		GameState.add_money(reward)
		GameState.set_flag("beat_" + String(cfg.get("trainer_id", "")))
		if trainer.has("reward_badge"):
			var badge := String(trainer["reward_badge"])
			if not (badge in GameState.badges):
				GameState.badges.append(badge)
		await dialog.show_lines([String(trainer.get("dialogue_defeat", "You won!")), "You earned $%d!" % reward])
	else:
		await dialog.show_lines(["You defeated the wild %s!" % engine.active_enemy().display_name()])

func _on_capture() -> void:
	var caught: CreatureInstance = engine.captured_creature
	caught.reset_battle_state()
	var where := GameState.add_creature(caught)
	GameState.inc_counter("creatures_caught")
	await dialog.show_lines(["%s was added to your %s!" % [caught.display_name(), where]])

func _on_loss() -> void:
	var loss_frac := float(DataRegistry.economy_cfg().get("defeat_money_loss_fraction", 0.1))
	var lost := int(GameState.get_money() * loss_frac)
	GameState.add_money(-lost)
	await dialog.show_lines(["Your team was defeated...", "You scurry back to safety. (Lost $%d)" % lost])
	GameState.heal_team()
	var respawn: Dictionary = GameState.player.get("respawn", {"map": "verdantia_center", "spawn": "entrance"})
	SceneRouter.to_overworld(String(respawn.get("map", "verdantia_center")), String(respawn.get("spawn", "entrance")))

func _apply_evolutions_then_return() -> void:
	if engine.winner in ["player", "captured"]:
		for ev in check_evolution_events:
			var idx := int(ev.get("team_index", -1))
			if idx < 0 or idx >= GameState.team.size():
				continue
			var c: CreatureInstance = GameState.team[idx]
			var target_id := EvolutionSystem.check(c, DataRegistry.evolutions_by_from, "level_up")
			if target_id != "":
				await dialog.show_lines(["What? %s is evolving!" % c.display_name()])
				EvolutionSystem.evolve(c, DataRegistry.creatures.get(target_id, {}), DataRegistry.moves)
				await dialog.show_lines(["%s evolved!" % c.display_name()])
	# Autosave after every battle so progress is never lost.
	SaveManager.autosave()
	if engine.winner != "enemy":
		_return_to_overworld()

func _return_to_overworld() -> void:
	var rp: Dictionary = cfg.get("return_pos", {})
	SceneRouter.pending_spawn = {}
	GameState.player["position"] = {
		"map": String(cfg.get("return_map", GameState.current_region)),
		"x": int(rp.get("x", 1)), "y": int(rp.get("y", 1)), "facing": String(rp.get("facing", "down")),
	}
	SceneRouter.to_overworld(String(cfg.get("return_map", "")), "")

func _player_took_faint() -> bool:
	for c in GameState.team:
		if c.is_fainted():
			return true
	return false

func _reveal(c: CreatureInstance) -> void:
	if not (c.species_id in revealed_player_species):
		revealed_player_species.append(c.species_id)

# ------------------------------------------------------------------ UI build / update

func _build_ui() -> void:
	add_child(UIFactory.make_fullscreen_bg(Color("#20344a")))
	dialog = DialogBox.new()
	add_child(dialog)

	enemy_sprite = TextureRect.new()
	enemy_sprite.position = Vector2(620, 90)
	enemy_sprite.custom_minimum_size = Vector2(96, 96)
	enemy_sprite.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	enemy_sprite.size = Vector2(96, 96)
	add_child(enemy_sprite)

	player_sprite = TextureRect.new()
	player_sprite.position = Vector2(180, 260)
	player_sprite.size = Vector2(112, 112)
	player_sprite.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	add_child(player_sprite)

	var enemy_panel := UIFactory.make_panel(Vector2(300, 0))
	enemy_panel.position = Vector2(40, 40)
	add_child(enemy_panel)
	var evb := VBoxContainer.new()
	enemy_panel.add_child(evb)
	enemy_name_lbl = UIFactory.make_label("Enemy", 18)
	evb.add_child(enemy_name_lbl)
	enemy_hp_bar = _make_hp_bar()
	evb.add_child(enemy_hp_bar)

	var player_panel := UIFactory.make_panel(Vector2(300, 0))
	player_panel.position = Vector2(600, 230)
	add_child(player_panel)
	var pvb := VBoxContainer.new()
	player_panel.add_child(pvb)
	player_name_lbl = UIFactory.make_label("You", 18)
	pvb.add_child(player_name_lbl)
	player_hp_bar = _make_hp_bar()
	pvb.add_child(player_hp_bar)
	player_hp_text = UIFactory.make_label("", 14)
	pvb.add_child(player_hp_text)

	ai_debug_lbl = UIFactory.make_label("", 12, Color("#a0d0ff"))
	ai_debug_lbl.position = Vector2(40, 120)
	ai_debug_lbl.custom_minimum_size = Vector2(400, 0)
	add_child(ai_debug_lbl)

func _make_hp_bar() -> ProgressBar:
	var bar := ProgressBar.new()
	bar.custom_minimum_size = Vector2(260, 18)
	bar.max_value = 100
	bar.value = 100
	bar.show_percentage = false
	return bar

func _update_hud() -> void:
	if engine == null:
		return
	var e := engine.active_enemy()
	var p := engine.active_player()
	enemy_name_lbl.text = "%s  Lv%d" % [e.display_name(), e.level]
	enemy_hp_bar.value = 100.0 * float(e.current_hp) / float(max(1, e.max_hp()))
	enemy_hp_bar.modulate = _hp_color(e)
	enemy_sprite.texture = PlaceholderGfx.make_creature_texture(e.species, 96)

	player_name_lbl.text = "%s  Lv%d" % [p.display_name(), p.level]
	player_hp_bar.value = 100.0 * float(p.current_hp) / float(max(1, p.max_hp()))
	player_hp_bar.modulate = _hp_color(p)
	player_hp_text.text = "HP %d/%d  %s" % [p.current_hp, p.max_hp(), ("" if p.status == "none" else "[" + p.status.to_upper() + "]")]
	player_sprite.texture = PlaceholderGfx.make_creature_texture(p.species, 112)

func _hp_color(c: CreatureInstance) -> Color:
	var f := float(c.current_hp) / float(max(1, c.max_hp()))
	if f > 0.5:
		return Color("#4caf50")
	if f > 0.2:
		return Color("#f2c94c")
	return Color("#e05a5a")

func _show_ai_debug(decision: Dictionary) -> void:
	if not SettingsManager.is_developer():
		ai_debug_lbl.text = ""
		return
	var alts := ""
	for a in decision.get("alternatives", []):
		alts += " %s(%s)" % [a.get("move", "?"), a.get("est_damage", a.get("score", "?"))]
	ai_debug_lbl.text = "[AI %s] %s\nConfidence: %.2f\nAlternatives:%s" % [
		ai_tier, decision.get("reason", ""), float(decision.get("confidence", 0.0)), alts]
