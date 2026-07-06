extends Control
## New Game: character creation (name, gender, starting region) then enter the world.
## The starter creature is chosen in-world at the Professor's lab.

var _name_edit: LineEdit
var _gender: OptionButton
var _region: OptionButton
var _regions_ordered: Array = []

func _ready() -> void:
	add_child(UIFactory.make_fullscreen_bg())
	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(center)
	var panel := UIFactory.make_panel(Vector2(460, 0))
	center.add_child(panel)
	var vb := VBoxContainer.new()
	vb.add_theme_constant_override("separation", 12)
	panel.add_child(vb)

	vb.add_child(UIFactory.make_title("Create Your Trainer", 30))

	vb.add_child(UIFactory.make_label("Name:"))
	_name_edit = LineEdit.new()
	_name_edit.text = "Ash-Free"
	_name_edit.max_length = 14
	_name_edit.custom_minimum_size = Vector2(300, 36)
	vb.add_child(_name_edit)

	vb.add_child(UIFactory.make_label("Gender:"))
	_gender = OptionButton.new()
	_gender.add_item("Boy")
	_gender.add_item("Girl")
	_gender.add_item("Nonbinary")
	vb.add_child(_gender)

	vb.add_child(UIFactory.make_label("Starting Region:"))
	_region = OptionButton.new()
	_regions_ordered = DataRegistry.get_region_in_order()
	for r in _regions_ordered:
		_region.add_item("%s (Lv %d-%d)" % [r.get("display_name", "?"), r.get("recommended_level_min", 1), r.get("recommended_level_max", 50)])
	vb.add_child(_region)

	var hb := HBoxContainer.new()
	hb.add_theme_constant_override("separation", 12)
	vb.add_child(hb)
	var back := UIFactory.make_button("Back")
	back.pressed.connect(func(): SceneRouter.to_title())
	hb.add_child(back)
	var start := UIFactory.make_button("Start Adventure")
	start.pressed.connect(_on_start)
	hb.add_child(start)

func _on_start() -> void:
	var pname := _name_edit.text.strip_edges()
	if pname == "":
		pname = "Trainer"
	var genders := ["boy", "girl", "nonbinary"]
	var region: Dictionary = _regions_ordered[_region.selected]
	GameState.new_game(pname, genders[_gender.selected], String(region.get("id", "verdantia")))
	GameState.mark_region_visited(String(region.get("id", "verdantia")))
	AudioManager.play_sfx("confirm")
	SceneRouter.to_overworld(String(region.get("starting_map", "verdantia_town")), "default")
