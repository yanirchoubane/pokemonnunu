extends Control
## Title screen: New Game / Continue / Settings / Quit. Keyboard + mouse driven.

var _buttons: Array = []
var _selected: int = 0

func _ready() -> void:
	add_child(UIFactory.make_fullscreen_bg())
	AudioManager.play_zone_music("title")
	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(center)
	var vb := VBoxContainer.new()
	vb.add_theme_constant_override("separation", 10)
	center.add_child(vb)
	vb.add_child(UIFactory.make_title("CREATURE RPG"))
	vb.add_child(UIFactory.make_label("An original, offline creature-collection RPG", 16))
	var spacer := Control.new()
	spacer.custom_minimum_size = Vector2(0, 20)
	vb.add_child(spacer)

	_add_button(vb, "New Game", _on_new_game)
	var has_any := false
	for slot in range(0, SaveManager.SLOT_COUNT + 1):
		if SaveManager.has_save(slot):
			has_any = true
			break
	var cont := _add_button(vb, "Continue", _on_continue)
	cont.disabled = not has_any
	_add_button(vb, "Settings", _on_settings)
	_add_button(vb, "Quit", _on_quit)
	_update_highlight()

func _add_button(vb: VBoxContainer, text: String, cb: Callable) -> Button:
	var b := UIFactory.make_button(text)
	b.pressed.connect(cb)
	vb.add_child(b)
	_buttons.append(b)
	return b

func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("move_down"):
		_move(1)
	elif event.is_action_pressed("move_up"):
		_move(-1)
	elif event.is_action_pressed("interact"):
		if not _buttons[_selected].disabled:
			_buttons[_selected].pressed.emit()

func _move(dir: int) -> void:
	_selected = (_selected + dir + _buttons.size()) % _buttons.size()
	AudioManager.play_sfx("select")
	_update_highlight()

func _update_highlight() -> void:
	for i in _buttons.size():
		_buttons[i].modulate = Color(1, 1, 1) if i == _selected else Color(0.65, 0.65, 0.7)

func _on_new_game() -> void:
	SceneRouter.to_new_game()

func _on_continue() -> void:
	SceneRouter.to_load_menu()

func _on_settings() -> void:
	# Untyped: load() returns Resource so ':=' cannot infer here (4.2 compile error).
	var settings = load("res://scenes/menus/settings.tscn").instantiate()
	add_child(settings)
	# Silence the title's keyboard handler while the overlay is open, otherwise
	# arrows/interact would keep driving the title buttons underneath.
	set_process_unhandled_input(false)
	settings.closed.connect(func(): set_process_unhandled_input(true))

func _on_quit() -> void:
	get_tree().quit()
