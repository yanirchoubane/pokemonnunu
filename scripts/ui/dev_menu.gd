extends Control
## Developer menu (only reachable when SettingsManager.developer_mode is on; bound to F12).
## Tools for testing: warp, spawn creature, set level, force battle, reload data,
## validate, show AI/adaptive info, unlock region, test evolution, force save, game speed.

signal closed

var _log: Label

func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	var bg := UIFactory.make_fullscreen_bg(Color(0, 0, 0, 0.85))
	bg.mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(bg)
	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(center)
	var panel := UIFactory.make_panel(Vector2(520, 0))
	center.add_child(panel)
	var vb := VBoxContainer.new()
	vb.add_theme_constant_override("separation", 6)
	panel.add_child(vb)
	vb.add_child(UIFactory.make_title("Developer Menu", 24))
	_log = UIFactory.make_label("Ready.", 13, Color("#a0d0ff"))
	vb.add_child(_log)

	_btn(vb, "Reload data + validate", func():
		DataRegistry.reload()
		var n := DataRegistry.load_errors.size()
		_say("Reloaded. %d validation error(s)." % n))
	_btn(vb, "Heal team", func():
		GameState.heal_team()
		_say("Team healed."))
	_btn(vb, "Give test creature (Zapmouse Lv15)", func():
		var where := GameState.add_creature(GameState.build_creature("zapmouse", 15))
		_say("Added Zapmouse to %s." % where))
	_btn(vb, "Level up first team member", func():
		if GameState.team.size() > 0:
			var c: CreatureInstance = GameState.team[0]
			c.level = min(100, c.level + 1)
			c.exp = ExperienceCalc.exp_for_level(c.exp_curve(), c.level)
			c.heal_full()
			_say("%s is now Lv%d." % [c.display_name(), c.level]))
	_btn(vb, "Test evolution of first member", func():
		if GameState.team.size() > 0:
			var c: CreatureInstance = GameState.team[0]
			var t := EvolutionSystem.check(c, DataRegistry.evolutions_by_from, "level_up")
			if t == "" and DataRegistry.evolutions_by_from.has(c.species_id):
				t = String(DataRegistry.evolutions_by_from[c.species_id].get("to", ""))
			if t != "":
				EvolutionSystem.evolve(c, DataRegistry.creatures.get(t, {}), DataRegistry.moves)
				_say("Evolved into %s." % c.display_name())
			else:
				_say("No evolution available."))
	_btn(vb, "Unlock region: Aquilon", func():
		GameState.unlock_region("aquilon")
		_say("Aquilon unlocked."))
	_btn(vb, "Warp to Aquilon Shore", func():
		SceneRouter.to_overworld("aquilon_shore", "from_verdantia")
		_close())
	_btn(vb, "Start test wild battle (Gustling Lv10)", func():
		SceneRouter.to_battle({"kind": "wild", "species_id": "gustling", "level": 10,
			"return_map": String(GameState.player.get("position", {}).get("map", "verdantia_town")),
			"return_pos": GameState.player.get("position", {})})
		_close())
	_btn(vb, "Show adaptive summary", func():
		var s := AdaptiveDirector.get_summary()
		_say("Mode %s | skill %.0f | delta %+d | battles %d" % [s["mode"], s["skill_score"], s["current_level_delta"], s["battles_recorded"]]))
	_btn(vb, "Force autosave", func():
		_say("Autosaved." if SaveManager.autosave() else "Autosave failed."))
	_btn(vb, "Cycle game speed (x1/x2/x4)", func():
		var next := 1.0
		if Engine.time_scale < 2.0: next = 2.0
		elif Engine.time_scale < 4.0: next = 4.0
		Engine.time_scale = next
		_say("Game speed x%.0f." % next))
	_btn(vb, "Close", _close)

func _btn(vb: VBoxContainer, text: String, cb: Callable) -> void:
	var b := UIFactory.make_button(text)
	b.custom_minimum_size = Vector2(460, 30)
	b.pressed.connect(cb)
	vb.add_child(b)

func _say(text: String) -> void:
	_log.text = text

func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("cancel") or event.is_action_pressed("dev_menu"):
		_close()

func _close() -> void:
	Engine.time_scale = 1.0
	closed.emit()
	queue_free()
