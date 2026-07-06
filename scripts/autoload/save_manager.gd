extends Node
## SaveManager (autoload): robust local saves.
## - 3 numbered slots + a dedicated autosave slot (0)
## - atomic write: data goes to a .tmp file, the old save becomes .bak, then swap
## - versioned format with forward migration
## - validates on load; falls back to .bak on corruption
## Never executes deserialized content — only parses JSON into plain data.

const SAVE_DIR := "user://saves"
const FORMAT_VERSION := 2
const AUTOSAVE_SLOT := 0
const SLOT_COUNT := 3

signal saved(slot: int)
signal loaded(slot: int)
signal save_failed(slot: int, reason: String)

func _ready() -> void:
	DirAccess.make_dir_recursive_absolute(SAVE_DIR)

func _slot_path(slot: int) -> String:
	return "%s/slot_%d.json" % [SAVE_DIR, slot]

func _tmp_path(slot: int) -> String:
	return "%s/slot_%d.tmp" % [SAVE_DIR, slot]

func _bak_path(slot: int) -> String:
	return "%s/slot_%d.bak" % [SAVE_DIR, slot]

func has_save(slot: int) -> bool:
	# The backup counts too: load_from_slot can recover from it, so the UI must
	# not hide a slot just because the primary file was lost mid-swap.
	return FileAccess.file_exists(_slot_path(slot)) or FileAccess.file_exists(_bak_path(slot))

## Save current GameState into a slot. Returns true on success.
func save_to_slot(slot: int) -> bool:
	var payload := {
		"header": {
			"format_version": FORMAT_VERSION,
			"timestamp": Time.get_datetime_string_from_system(),
			"unix_time": Time.get_unix_time_from_system(),
			"playtime_seconds": int(GameState.playtime_seconds),
			"player_name": GameState.player.get("name", "Trainer"),
			"region": GameState.current_region,
			"team_summary": _team_summary(),
			"badges": GameState.badges.size(),
		},
		"state": GameState.to_dict(),
	}
	var text := JSON.stringify(payload, "  ")

	# 1) write to temp
	var f := FileAccess.open(_tmp_path(slot), FileAccess.WRITE)
	if f == null:
		save_failed.emit(slot, "cannot open temp file")
		return false
	f.store_string(text)
	f.close()

	# 2) verify temp parses back
	var verify := FileAccess.open(_tmp_path(slot), FileAccess.READ)
	var parsed = JSON.parse_string(verify.get_as_text()) if verify else null
	if verify:
		verify.close()
	if not (parsed is Dictionary):
		save_failed.emit(slot, "temp verification failed")
		return false

	# 3) rotate current -> backup, temp -> current (atomic-ish swap)
	var dir := DirAccess.open(SAVE_DIR)
	if has_save(slot):
		if FileAccess.file_exists(_bak_path(slot)):
			dir.remove(_bak_path(slot).get_file())
		dir.rename(_slot_path(slot).get_file(), _bak_path(slot).get_file())
	dir.rename(_tmp_path(slot).get_file(), _slot_path(slot).get_file())

	saved.emit(slot)
	return true

func autosave() -> bool:
	return save_to_slot(AUTOSAVE_SLOT)

## Load a slot into GameState. Returns true on success. Falls back to backup on corruption.
func load_from_slot(slot: int) -> bool:
	var data := _read_and_validate(_slot_path(slot))
	if data.is_empty():
		# Try backup.
		data = _read_and_validate(_bak_path(slot))
		if data.is_empty():
			save_failed.emit(slot, "save file is missing or corrupted (backup also unusable)")
			return false
		push_warning("[SaveManager] Primary save corrupted; restored from backup for slot %d." % slot)
	data = _migrate(data)
	GameState.from_dict(data.get("state", {}))
	loaded.emit(slot)
	return true

func slot_metadata(slot: int) -> Dictionary:
	var data := _read_and_validate(_slot_path(slot))
	if data.is_empty():
		data = _read_and_validate(_bak_path(slot))  # mirror load_from_slot's fallback
	if data.is_empty():
		return {}
	return data.get("header", {})

func all_slot_metadata() -> Array:
	var out: Array = []
	for slot in range(0, SLOT_COUNT + 1):  # 0 = autosave
		out.append({"slot": slot, "exists": has_save(slot), "header": slot_metadata(slot)})
	return out

func delete_slot(slot: int) -> void:
	var dir := DirAccess.open(SAVE_DIR)
	if dir == null:
		return
	for p in [_slot_path(slot), _bak_path(slot), _tmp_path(slot)]:
		if FileAccess.file_exists(p):
			dir.remove(p.get_file())

# ------------------------------------------------------------------ internals

func _read_and_validate(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		return {}
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		return {}
	var text := f.get_as_text()
	f.close()
	var parsed = JSON.parse_string(text)
	if not (parsed is Dictionary):
		return {}
	if not parsed.has("header") or not parsed.has("state"):
		return {}
	if not parsed["header"] is Dictionary:
		return {}
	if not parsed["state"] is Dictionary:
		return {}
	return parsed

## Forward-migrate an old save payload to the current FORMAT_VERSION.
func _migrate(data: Dictionary) -> Dictionary:
	var v: int = int(data.get("header", {}).get("format_version", 1))
	while v < FORMAT_VERSION:
		match v:
			1:
				# v1 -> v2: introduce region_progress / adaptive_state defaults if absent.
				var st: Dictionary = data.get("state", {})
				if not st.has("region_progress"):
					st["region_progress"] = {}
				if not st.has("adaptive_state"):
					st["adaptive_state"] = {}
				data["state"] = st
			_:
				pass
		v += 1
		data["header"]["format_version"] = v
	return data

func _team_summary() -> Array:
	var out: Array = []
	for c in GameState.team:
		out.append({"species": c.species_id, "level": c.level})
	return out
