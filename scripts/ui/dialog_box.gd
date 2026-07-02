class_name DialogBox
extends CanvasLayer
## Reusable dialog box with typewriter text, multi-page sequences, and optional choices.
##
## Input-consumption contract (important): every public coroutine awaits one extra
## process_frame after the final accepting key press before returning. Callers that
## poll Input in _process (e.g. the overworld) therefore never see the same
## just-pressed action that dismissed the dialog — this prevents the classic
## "dismiss reopens the sign" soft-lock.
##
## Usage:
##   var dlg = DialogBox.new(); add_child(dlg)
##   await dlg.show_lines(["Hello", "World"])
##   var idx = await dlg.show_choice("Pick one", ["Yes", "No"])

signal finished

var _panel: PanelContainer
var _label: RichTextLabel
var _choices_box: VBoxContainer

func _init() -> void:
	layer = 50
	var margin := MarginContainer.new()
	margin.set_anchors_preset(Control.PRESET_FULL_RECT)
	margin.add_theme_constant_override("margin_left", 24)
	margin.add_theme_constant_override("margin_right", 24)
	margin.add_theme_constant_override("margin_bottom", 20)
	margin.add_theme_constant_override("margin_top", 20)
	add_child(margin)

	var align := VBoxContainer.new()
	align.set_anchors_preset(Control.PRESET_FULL_RECT)
	align.alignment = BoxContainer.ALIGNMENT_END
	margin.add_child(align)

	_panel = UIFactory.make_panel()
	_panel.custom_minimum_size = Vector2(0, 120)
	align.add_child(_panel)

	var vb := VBoxContainer.new()
	_panel.add_child(vb)
	_label = RichTextLabel.new()
	_label.bbcode_enabled = true
	_label.fit_content = true
	_label.custom_minimum_size = Vector2(0, 60)
	_label.add_theme_font_size_override("normal_font_size", 20)
	vb.add_child(_label)
	_choices_box = VBoxContainer.new()
	vb.add_child(_choices_box)

func show_lines(lines: Array) -> void:
	for line in lines:
		await _type_line(String(line))
		await _wait_advance()
	# Consume the dismissing press: resume callers on the NEXT frame so their
	# Input.is_action_just_pressed polling cannot see the same press.
	await get_tree().process_frame
	finished.emit()

## Typewriter reveal. Pressing "interact" mid-typing skips to the full line
## (and that press is consumed — the next press advances the page).
func _type_line(text: String) -> void:
	_label.text = ""
	var delay := UIFactory.text_speed_delay()
	if delay <= 0.0:
		_label.text = text
		return
	var shown := 0
	var acc := 0.0
	while shown < text.length():
		await get_tree().process_frame
		if Input.is_action_just_pressed("interact"):
			shown = text.length()
			break
		acc += get_process_delta_time()
		while acc >= delay and shown < text.length():
			acc -= delay
			shown += 1
		_label.text = text.substr(0, shown)
	_label.text = text

func _wait_advance() -> void:
	while true:
		await get_tree().process_frame
		if Input.is_action_just_pressed("interact"):
			AudioManager.play_sfx("confirm")
			return

## Show a prompt with selectable choices; returns the chosen index.
## Supports keyboard (up/down + interact) AND mouse clicks on the buttons.
func show_choice(prompt: String, options: Array) -> int:
	await _type_line(prompt)
	var selected := 0
	var clicked := [-1]  # Array so the button lambdas mutate shared state (GDScript captures locals by value)
	var buttons: Array = []
	for i in options.size():
		var b := UIFactory.make_button(String(options[i]))
		b.pressed.connect(func(): clicked[0] = i)
		_choices_box.add_child(b)
		buttons.append(b)
	_highlight(buttons, selected)
	while true:
		await get_tree().process_frame
		if clicked[0] >= 0:
			selected = clicked[0]
			break
		if Input.is_action_just_pressed("move_down"):
			selected = (selected + 1) % options.size()
			_highlight(buttons, selected)
			AudioManager.play_sfx("select")
		elif Input.is_action_just_pressed("move_up"):
			selected = (selected - 1 + options.size()) % options.size()
			_highlight(buttons, selected)
			AudioManager.play_sfx("select")
		elif Input.is_action_just_pressed("interact"):
			break
	AudioManager.play_sfx("confirm")
	for b in buttons:
		b.queue_free()
	# Consume the accepting press before returning to the caller.
	await get_tree().process_frame
	return selected

func _highlight(buttons: Array, idx: int) -> void:
	for i in buttons.size():
		buttons[i].modulate = Color(1, 1, 1) if i == idx else Color(0.6, 0.6, 0.6)
