extends Node
## SceneRouter (autoload): centralizes scene changes, fade transitions, and the
## overworld<->battle handoff (spawn points, battle config, return position).

const BOOT := "res://scenes/boot/boot.tscn"
const TITLE := "res://scenes/menus/title.tscn"
const NEW_GAME := "res://scenes/menus/new_game.tscn"
const LOAD_MENU := "res://scenes/menus/load_menu.tscn"
const OVERWORLD := "res://scenes/overworld/overworld.tscn"
const BATTLE := "res://scenes/battle/battle.tscn"

# Data passed between scenes (never persisted).
var pending_spawn: Dictionary = {}   # { map, spawn }
var pending_battle: Dictionary = {}  # battle configuration
var last_battle_result: Dictionary = {}

var _fade: ColorRect
var _busy: bool = false
var _queued_path: String = ""

func _ready() -> void:
	var layer := CanvasLayer.new()
	layer.layer = 128
	add_child(layer)
	_fade = ColorRect.new()
	_fade.color = Color(0, 0, 0, 0)
	_fade.set_anchors_preset(Control.PRESET_FULL_RECT)
	_fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layer.add_child(_fade)

func to_title() -> void:
	_change(TITLE)

func to_new_game() -> void:
	_change(NEW_GAME)

func to_load_menu() -> void:
	_change(LOAD_MENU)

## Enter the overworld on a specific map at a named spawn marker.
func to_overworld(map_id: String, spawn_id: String = "default") -> void:
	pending_spawn = {"map": map_id, "spawn": spawn_id}
	_change(OVERWORLD)

## Start a battle. cfg is consumed by the battle scene; see battle_scene.gd.
func to_battle(cfg: Dictionary) -> void:
	pending_battle = cfg
	_change(BATTLE)

## Called by the battle scene when the battle ends; returns to the overworld.
func end_battle(result: Dictionary) -> void:
	last_battle_result = result
	pending_spawn = {}  # keep player where they were
	_change(OVERWORLD)

func _change(path: String) -> void:
	if _busy:
		# Never DROP a navigation: remember the latest request and run it once
		# the current transition finishes (dropping used to lose ferry warps
		# requested during the post-battle fade, leaving input locked forever).
		_queued_path = path
		return
	_busy = true
	await _fade_to(1.0, 0.25)
	get_tree().change_scene_to_file(path)
	await get_tree().process_frame
	await _fade_to(0.0, 0.25)
	_busy = false
	if _queued_path != "":
		var next := _queued_path
		_queued_path = ""
		_change(next)

func _fade_to(target_alpha: float, duration: float) -> void:
	if bool(SettingsManager.get_value("reduce_animations", false)):
		_fade.color.a = target_alpha
		return
	var tween := create_tween()
	tween.tween_property(_fade, "color:a", target_alpha, duration)
	await tween.finished
