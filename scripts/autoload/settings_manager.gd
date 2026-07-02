extends Node
## SettingsManager (autoload): user options, persisted to user:// independently of saves.

const SETTINGS_PATH := "user://settings.cfg"

signal settings_changed

var data: Dictionary = {
	"difficulty": "adaptive",          # relaxed | normal | hard | adaptive
	"adaptive_enabled": true,
	"adaptive_intensity": 0.5,         # 0..1
	"adaptive_max_scaling": 3,         # max enemy level delta magnitude
	"show_adaptation_summary": false,
	"developer_mode": false,
	"music_volume": 0.8,
	"sfx_volume": 0.9,
	"text_speed": "normal",            # slow | normal | fast | instant
	"fullscreen": false,
	"ui_scale": 1.0,
	"reduce_animations": false,
	"colorblind_mode": "none",
	"confirm_irreversible": true,
	"keybinds": {},                    # action -> physical keycode override
}

func _ready() -> void:
	load_settings()
	_apply_display()

func get_value(key: String, default_value = null):
	return data.get(key, default_value)

func set_value(key: String, value) -> void:
	data[key] = value
	settings_changed.emit()
	save_settings()
	if key == "fullscreen":
		_apply_display()

func is_developer() -> bool:
	return bool(data.get("developer_mode", false))

func _apply_display() -> void:
	if bool(data.get("fullscreen", false)):
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN)
	else:
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED)

func save_settings() -> void:
	var f := FileAccess.open(SETTINGS_PATH, FileAccess.WRITE)
	if f:
		f.store_string(JSON.stringify(data, "  "))
		f.close()

func load_settings() -> void:
	if not FileAccess.file_exists(SETTINGS_PATH):
		return
	var f := FileAccess.open(SETTINGS_PATH, FileAccess.READ)
	if not f:
		return
	var parsed = JSON.parse_string(f.get_as_text())
	f.close()
	if parsed is Dictionary:
		for k in parsed.keys():
			data[k] = parsed[k]
