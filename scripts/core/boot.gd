extends Control
## Boot scene: verifies data loaded & validated, then routes to the title screen.
## If validation failed, shows the errors instead of launching (fail loud, not silent).

func _ready() -> void:
	var bg := UIFactory.make_fullscreen_bg()
	add_child(bg)
	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(center)
	var vb := VBoxContainer.new()
	vb.add_theme_constant_override("separation", 12)
	center.add_child(vb)

	vb.add_child(UIFactory.make_title("Creature RPG 2D Engine"))
	var status := UIFactory.make_label("Loading data...", 18)
	status.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	vb.add_child(status)

	# Give autoloads a frame to finish reload().
	await get_tree().process_frame

	if not DataRegistry.loaded:
		await DataRegistry.data_loaded

	if DataRegistry.load_errors.is_empty():
		status.text = "Data OK — starting..."
		AudioManager.play_zone_music("title")
		await get_tree().create_timer(0.4).timeout
		SceneRouter.to_title()
	else:
		status.text = "Data validation FAILED (%d errors):" % DataRegistry.load_errors.size()
		status.add_theme_color_override("font_color", Color("#e05a5a"))
		var scroll := ScrollContainer.new()
		scroll.custom_minimum_size = Vector2(700, 260)
		vb.add_child(scroll)
		var errbox := VBoxContainer.new()
		scroll.add_child(errbox)
		for e in DataRegistry.load_errors:
			errbox.add_child(UIFactory.make_label("• " + String(e), 14, Color("#e0a0a0")))
		vb.add_child(UIFactory.make_label("Fix the data files, then relaunch. See tools/validators/validate_data.py.", 14))
