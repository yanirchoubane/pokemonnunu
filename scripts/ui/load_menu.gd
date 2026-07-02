extends Control
## Load / Save-slot menu. Shows metadata for each slot (autosave = slot 0).

func _ready() -> void:
	add_child(UIFactory.make_fullscreen_bg())
	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(center)
	var vb := VBoxContainer.new()
	vb.add_theme_constant_override("separation", 10)
	center.add_child(vb)
	vb.add_child(UIFactory.make_title("Load Game", 30))

	for meta in SaveManager.all_slot_metadata():
		var slot := int(meta["slot"])
		var label := "Autosave" if slot == 0 else "Slot %d" % slot
		if meta["exists"]:
			var h: Dictionary = meta["header"]
			var mins := int(h.get("playtime_seconds", 0)) / 60
			label += " — %s | %s | %s | %dm | %d badge(s)" % [
				h.get("player_name", "?"), h.get("region", "?"), h.get("timestamp", "?"), mins, int(h.get("badges", 0))]
			var b := UIFactory.make_button(label)
			b.custom_minimum_size = Vector2(560, 40)
			b.pressed.connect(_load_slot.bind(slot))
			vb.add_child(b)
		else:
			var b := UIFactory.make_button(label + " — (empty)")
			b.custom_minimum_size = Vector2(560, 40)
			b.disabled = true
			vb.add_child(b)

	var back := UIFactory.make_button("Back")
	back.pressed.connect(func(): SceneRouter.to_title())
	vb.add_child(back)

func _load_slot(slot: int) -> void:
	if SaveManager.load_from_slot(slot):
		AudioManager.play_sfx("confirm")
		var map_id: String = GameState.player.get("position", {}).get("map", "")
		if map_id == "":
			map_id = DataRegistry.regions.get(GameState.current_region, {}).get("starting_map", "verdantia_town")
		SceneRouter.to_overworld(map_id, "")
	else:
		AudioManager.play_sfx("cancel")
