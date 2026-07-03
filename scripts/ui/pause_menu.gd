extends Control
## In-game pause menu: Team, Bag, Quests, Encyclopedia, Save, Settings.
## Emits `closed` when dismissed so the overworld can resume input.

signal closed

var _content: VBoxContainer
var _root_box: VBoxContainer

func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	var bg := UIFactory.make_fullscreen_bg(Color(0, 0, 0, 0.8))
	bg.mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(bg)
	var margin := MarginContainer.new()
	margin.set_anchors_preset(Control.PRESET_FULL_RECT)
	margin.add_theme_constant_override("margin_left", 30)
	margin.add_theme_constant_override("margin_top", 20)
	margin.add_theme_constant_override("margin_right", 30)
	margin.add_theme_constant_override("margin_bottom", 20)
	add_child(margin)
	var panel := UIFactory.make_panel()
	margin.add_child(panel)
	var hb := HBoxContainer.new()
	hb.add_theme_constant_override("separation", 20)
	panel.add_child(hb)

	_root_box = VBoxContainer.new()
	_root_box.add_theme_constant_override("separation", 6)
	hb.add_child(_root_box)
	_root_box.add_child(UIFactory.make_title(DataRegistry.tr_key("ui.menu"), 26))
	for entry in [[DataRegistry.tr_key("ui.team"), _view_team], [DataRegistry.tr_key("ui.bag"), _view_bag],
			[DataRegistry.tr_key("ui.quests"), _view_quests], [DataRegistry.tr_key("ui.storage"), _view_storage],
			[DataRegistry.tr_key("ui.encyclopedia"), _view_dex], [DataRegistry.tr_key("ui.save"), _view_save],
			[DataRegistry.tr_key("ui.settings"), _open_settings], [DataRegistry.tr_key("ui.close"), _close]]:
		var b := UIFactory.make_button(String(entry[0]))
		b.custom_minimum_size = Vector2(160, 34)
		b.pressed.connect(entry[1])
		_root_box.add_child(b)

	var scroll := ScrollContainer.new()
	scroll.custom_minimum_size = Vector2(620, 440)
	hb.add_child(scroll)
	_content = VBoxContainer.new()
	_content.add_theme_constant_override("separation", 6)
	scroll.add_child(_content)
	_view_team()

func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("cancel") or event.is_action_pressed("menu"):
		_close()

func _clear() -> void:
	for c in _content.get_children():
		c.queue_free()

func _header(text: String) -> void:
	_clear()
	_content.add_child(UIFactory.make_title(text, 22))

func _view_team() -> void:
	_header("Team (%d/%d)" % [GameState.team.size(), int(DataRegistry.party_cfg().get("max_team_size", 6))])
	if GameState.team.is_empty():
		_content.add_child(UIFactory.make_label("No creatures yet. Visit the Professor's lab!"))
		return
	for c in GameState.team:
		var p := UIFactory.make_panel()
		var vb := VBoxContainer.new()
		p.add_child(vb)
		var head := HBoxContainer.new()
		var icon := TextureRect.new()
		icon.texture = AssetResolver.creature_texture(c.species, 40)
		icon.custom_minimum_size = Vector2(40, 40)
		head.add_child(icon)
		head.add_child(UIFactory.make_label("%s  Lv%d  (%s)" % [c.display_name(), c.level, "/".join(c.types())], 18))
		vb.add_child(head)
		vb.add_child(UIFactory.make_label("HP %d/%d   Status: %s   Nature: %s   Ability: %s" % [
			c.current_hp, c.max_hp(), c.status, c.nature, c.ability], 14))
		vb.add_child(UIFactory.make_label("Stats  ATK %d DEF %d SPA %d SPD %d SPE %d" % [
			c.stat("attack"), c.stat("defense"), c.stat("sp_attack"), c.stat("sp_defense"), c.stat("speed")], 13))
		var moves := ""
		for m in c.moves:
			moves += "%s  " % DataRegistry.moves.get(String(m["id"]), {}).get("display_name", m["id"])
		vb.add_child(UIFactory.make_label("Moves: " + moves, 13))
		_content.add_child(p)

func _view_bag() -> void:
	_header("Bag — $%d" % GameState.get_money())
	if GameState.inventory.is_empty():
		_content.add_child(UIFactory.make_label("Your bag is empty."))
		return
	for item_id in GameState.inventory.keys():
		var rec: Dictionary = DataRegistry.items.get(item_id, {})
		_content.add_child(UIFactory.make_label("%s x%d — %s" % [
			rec.get("display_name", item_id), GameState.inventory[item_id], rec.get("description", "")], 15))

func _view_quests() -> void:
	_header("Quest Journal")
	if GameState.quests.is_empty():
		_content.add_child(UIFactory.make_label("No quests yet."))
		return
	for qid in GameState.quests.keys():
		var qdef: Dictionary = DataRegistry.quests.get(qid, {})
		var qstate: Dictionary = GameState.quests[qid]
		var p := UIFactory.make_panel()
		var vb := VBoxContainer.new()
		p.add_child(vb)
		var state_tag := "✓ COMPLETE" if qstate.get("state") == "complete" else "● ACTIVE"
		vb.add_child(UIFactory.make_label("%s  [%s]" % [qdef.get("display_name", qid), state_tag], 17))
		vb.add_child(UIFactory.make_label(String(qdef.get("description", "")), 13))
		for o in qdef.get("objectives", []):
			var done := bool(qstate.get("objectives", {}).get(String(o.get("id", "")), false))
			var mark := "[x]" if done else "[ ]"
			vb.add_child(UIFactory.make_label("  %s %s" % [mark, o.get("text", "")], 13))
		_content.add_child(p)

func _view_dex() -> void:
	_header("Encyclopedia")
	var caught := {}
	for c in GameState.team + GameState.box:
		caught[c.species_id] = true
	var seen := caught.size()
	_content.add_child(UIFactory.make_label("Caught: %d / %d species" % [seen, DataRegistry.creatures.size()], 15))
	for cid in DataRegistry.creatures.keys():
		var rec: Dictionary = DataRegistry.creatures[cid]
		if caught.has(cid):
			_content.add_child(UIFactory.make_label("• %s (%s) — %s" % [
				rec.get("display_name", cid), "/".join(rec.get("types", [])), rec.get("description", "")], 13))
		else:
			_content.add_child(UIFactory.make_label("• ??? (undiscovered)", 13, Color("#888")))

## Simplified storage box: deposit team members / withdraw boxed creatures.
func _view_storage() -> void:
	var maxsize: int = int(DataRegistry.party_cfg().get("max_team_size", 6))
	_header("Storage — Team %d/%d, Box %d" % [GameState.team.size(), maxsize, GameState.box.size()])
	_content.add_child(UIFactory.make_label("Team (select to deposit into the box):", 15))
	if GameState.team.size() <= 1:
		_content.add_child(UIFactory.make_label("You must keep at least one creature with you.", 13, Color("#888")))
	for i in GameState.team.size():
		var c: CreatureInstance = GameState.team[i]
		var b := UIFactory.make_button("▼ %s  Lv%d  HP %d/%d" % [c.display_name(), c.level, c.current_hp, c.max_hp()])
		b.pressed.connect(func():
			if GameState.deposit_creature(i):
				AudioManager.play_sfx("confirm")
			else:
				AudioManager.play_sfx("cancel")
			_view_storage())
		_content.add_child(b)
	_content.add_child(UIFactory.make_label("Box (select to withdraw into the team):", 15))
	if GameState.box.is_empty():
		_content.add_child(UIFactory.make_label("The box is empty.", 13, Color("#888")))
	for i in GameState.box.size():
		var c: CreatureInstance = GameState.box[i]
		var b := UIFactory.make_button("▲ %s  Lv%d  HP %d/%d" % [c.display_name(), c.level, c.current_hp, c.max_hp()])
		b.pressed.connect(func():
			if GameState.withdraw_creature(i):
				AudioManager.play_sfx("confirm")
			else:
				AudioManager.play_sfx("cancel")
			_view_storage())
		_content.add_child(b)

func _view_save() -> void:
	_header("Save Game")
	for slot in range(1, SaveManager.SLOT_COUNT + 1):
		var b := UIFactory.make_button("Save to Slot %d" % slot)
		b.pressed.connect(_do_save.bind(slot))
		_content.add_child(b)
	var info := UIFactory.make_label("", 14)
	_content.add_child(info)
	info.set_meta("info", true)

func _do_save(slot: int) -> void:
	if SaveManager.save_to_slot(slot):
		AudioManager.play_sfx("confirm")
		for c in _content.get_children():
			if c is Label and c.has_meta("info"):
				c.text = "Saved to Slot %d at %s." % [slot, Time.get_time_string_from_system()]
	else:
		AudioManager.play_sfx("cancel")

func _open_settings() -> void:
	# Untyped: load() returns Resource so ':=' cannot infer here (4.2 compile error).
	var s = load("res://scenes/menus/settings.tscn").instantiate()
	add_child(s)
	# Don't let Esc/cancel close the pause menu underneath while Settings is open.
	set_process_unhandled_input(false)
	s.closed.connect(func(): set_process_unhandled_input(true))

func _close() -> void:
	closed.emit()
	queue_free()
