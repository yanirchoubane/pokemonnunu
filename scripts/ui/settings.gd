extends Control
## Settings overlay: difficulty, adaptive options, audio, text, display, accessibility,
## and key rebinding. Writes straight into SettingsManager (persisted).

signal closed

const REBINDABLE := ["move_up", "move_down", "move_left", "move_right", "interact", "cancel", "menu"]

var _rebinding_action: String = ""
var _rebind_buttons: Dictionary = {}

func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	var bg := UIFactory.make_fullscreen_bg(Color(0, 0, 0, 0.85))
	bg.mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(bg)
	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(center)
	var panel := UIFactory.make_panel(Vector2(560, 460))
	center.add_child(panel)
	var scroll := ScrollContainer.new()
	panel.add_child(scroll)
	var vb := VBoxContainer.new()
	vb.add_theme_constant_override("separation", 8)
	vb.custom_minimum_size = Vector2(520, 0)
	scroll.add_child(vb)

	vb.add_child(UIFactory.make_title("Settings", 28))

	_add_option(vb, "Difficulty", ["relaxed", "normal", "hard", "adaptive"], "difficulty")
	_add_check(vb, "Adaptive difficulty enabled", "adaptive_enabled")
	_add_slider(vb, "Adaptive intensity", "adaptive_intensity", 0.0, 1.0, 0.1)
	_add_spin(vb, "Max level scaling", "adaptive_max_scaling", 0, 6)
	_add_check(vb, "Show adaptation summary", "show_adaptation_summary")
	_add_check(vb, "Developer mode", "developer_mode")
	_add_slider(vb, "Music volume", "music_volume", 0.0, 1.0, 0.05)
	_add_slider(vb, "SFX volume", "sfx_volume", 0.0, 1.0, 0.05)
	_add_option(vb, "Text speed", ["slow", "normal", "fast", "instant"], "text_speed")
	_add_check(vb, "Fullscreen", "fullscreen")
	_add_slider(vb, "UI scale", "ui_scale", 0.8, 1.5, 0.1)
	_add_check(vb, "Reduce animations", "reduce_animations")
	_add_option(vb, "Colorblind mode", ["none", "protanopia", "deuteranopia", "tritanopia"], "colorblind_mode")
	_add_check(vb, "Confirm irreversible actions", "confirm_irreversible")

	vb.add_child(UIFactory.make_label("Key bindings (click, then press a key):", 16))
	for action in REBINDABLE:
		var row := HBoxContainer.new()
		row.add_child(UIFactory.make_label(action + ":", 15))
		var b := UIFactory.make_button(_key_name(action))
		b.custom_minimum_size = Vector2(160, 32)
		b.pressed.connect(_begin_rebind.bind(action))
		_rebind_buttons[action] = b
		row.add_child(b)
		vb.add_child(row)

	var close := UIFactory.make_button("Close")
	close.pressed.connect(_close)
	vb.add_child(close)

func _add_option(vb: VBoxContainer, label: String, options: Array, key: String) -> void:
	var row := HBoxContainer.new()
	row.add_child(UIFactory.make_label(label + ":", 16))
	var ob := OptionButton.new()
	for i in options.size():
		ob.add_item(String(options[i]).capitalize())
		if String(SettingsManager.get_value(key, options[0])) == String(options[i]):
			ob.select(i)
	ob.item_selected.connect(func(idx): SettingsManager.set_value(key, options[idx]))
	row.add_child(ob)
	vb.add_child(row)

func _add_check(vb: VBoxContainer, label: String, key: String) -> void:
	var cb := CheckBox.new()
	cb.text = label
	cb.button_pressed = bool(SettingsManager.get_value(key, false))
	cb.toggled.connect(func(on): SettingsManager.set_value(key, on))
	vb.add_child(cb)

func _add_slider(vb: VBoxContainer, label: String, key: String, mn: float, mx: float, step: float) -> void:
	var row := HBoxContainer.new()
	var l := UIFactory.make_label("%s: %.2f" % [label, float(SettingsManager.get_value(key, mn))], 16)
	row.add_child(l)
	var s := HSlider.new()
	s.min_value = mn
	s.max_value = mx
	s.step = step
	s.value = float(SettingsManager.get_value(key, mn))
	s.custom_minimum_size = Vector2(200, 20)
	s.value_changed.connect(func(v):
		SettingsManager.set_value(key, v)
		l.text = "%s: %.2f" % [label, v])
	row.add_child(s)
	vb.add_child(row)

func _add_spin(vb: VBoxContainer, label: String, key: String, mn: int, mx: int) -> void:
	var row := HBoxContainer.new()
	row.add_child(UIFactory.make_label(label + ":", 16))
	var sp := SpinBox.new()
	sp.min_value = mn
	sp.max_value = mx
	sp.value = int(SettingsManager.get_value(key, mn))
	sp.value_changed.connect(func(v): SettingsManager.set_value(key, int(v)))
	row.add_child(sp)
	vb.add_child(row)

func _begin_rebind(action: String) -> void:
	_rebinding_action = action
	_rebind_buttons[action].text = "Press a key..."

func _input(event: InputEvent) -> void:
	if _rebinding_action != "" and event is InputEventKey and event.pressed:
		var action := _rebinding_action
		_rebinding_action = ""
		InputMap.action_erase_events(action)
		var ev := InputEventKey.new()
		ev.physical_keycode = event.physical_keycode
		InputMap.action_add_event(action, ev)
		var binds: Dictionary = SettingsManager.get_value("keybinds", {})
		binds[action] = event.physical_keycode
		SettingsManager.set_value("keybinds", binds)
		_rebind_buttons[action].text = _key_name(action)
		accept_event()

func _key_name(action: String) -> String:
	for e in InputMap.action_get_events(action):
		if e is InputEventKey:
			return OS.get_keycode_string(e.physical_keycode)
	return "?"

func _close() -> void:
	closed.emit()
	queue_free()
