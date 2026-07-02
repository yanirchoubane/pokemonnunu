extends Control
## Simple shop: buy items from a stock list; sell not implemented in the prototype
## (documented as a future step). Prices come from data/items.

signal closed

var stock: Array = []
var _money_lbl: Label

func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	var bg := UIFactory.make_fullscreen_bg(Color(0, 0, 0, 0.8))
	bg.mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(bg)
	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(center)
	var panel := UIFactory.make_panel(Vector2(460, 0))
	center.add_child(panel)
	var vb := VBoxContainer.new()
	vb.add_theme_constant_override("separation", 8)
	panel.add_child(vb)
	vb.add_child(UIFactory.make_title("Shop", 26))
	_money_lbl = UIFactory.make_label("Money: $%d" % GameState.get_money(), 16)
	vb.add_child(_money_lbl)
	for item_id in stock:
		var rec: Dictionary = DataRegistry.items.get(String(item_id), {})
		var b := UIFactory.make_button("%s — $%d" % [rec.get("display_name", item_id), int(rec.get("price", 0))])
		b.custom_minimum_size = Vector2(400, 34)
		b.pressed.connect(_buy.bind(String(item_id)))
		vb.add_child(b)
	var close := UIFactory.make_button("Leave")
	close.pressed.connect(_close)
	vb.add_child(close)

func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("cancel") or event.is_action_pressed("menu"):
		_close()

func _buy(item_id: String) -> void:
	var rec: Dictionary = DataRegistry.items.get(item_id, {})
	var price := int(rec.get("price", 0))
	if GameState.get_money() >= price:
		GameState.add_money(-price)
		GameState.give_item(item_id, 1)
		AudioManager.play_sfx("confirm")
		_money_lbl.text = "Money: $%d" % GameState.get_money()
	else:
		AudioManager.play_sfx("cancel")
		_money_lbl.text = "Not enough money!"

func _close() -> void:
	closed.emit()
	queue_free()
