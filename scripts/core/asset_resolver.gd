class_name AssetResolver
extends RefCounted
## Resolves art/audio through the user-content overlay, falling back to the
## procedural placeholders. The engine NEVER downloads anything: user_content/
## is filled manually by the user with resources they legally own.
##
## Search order (later roots win):
##   1. res://user_content/   (project folder — convenient while using the editor)
##   2. user://user_content/  (Godot user dir — survives exports)
##
## Expected layout inside each root (all optional):
##   sprites/creatures/<species_id>.png   battle + menu art for a species
##   sprites/portraits/<npc_id>.png       dialog portraits
##   music/<zone_or_track_id>.ogg         zone music (Ogg Vorbis)

const USER_ROOTS: Array[String] = ["res://user_content", "user://user_content"]

static var _texture_cache: Dictionary = {}
static var _music_cache: Dictionary = {}

## Battle/menu texture for a species record; placeholder when no user sprite exists.
static func creature_texture(species: Dictionary, size: int) -> Texture2D:
	var id := String(species.get("id", ""))
	var key := "creature:%s:%d" % [id, size]
	if _texture_cache.has(key):
		return _texture_cache[key]
	var tex: Texture2D = _load_user_texture("sprites/creatures/%s.png" % id)
	if tex == null:
		tex = PlaceholderGfx.make_creature_texture(species, size)
	_texture_cache[key] = tex
	return tex

## Dialog portrait for an NPC id, or null when none is provided.
static func portrait(npc_id: String) -> Texture2D:
	if npc_id == "":
		return null
	var key := "portrait:%s" % npc_id
	if _texture_cache.has(key):
		return _texture_cache[key]
	var tex: Texture2D = _load_user_texture("sprites/portraits/%s.png" % npc_id)
	_texture_cache[key] = tex
	return tex

## User-supplied zone music (<root>/music/<id>.ogg), or null to use the
## generated placeholder tones.
static func music_stream(track_id: String) -> AudioStream:
	if _music_cache.has(track_id):
		return _music_cache[track_id]
	var stream: AudioStream = null
	for root in USER_ROOTS:
		var path := "%s/music/%s.ogg" % [root, track_id]
		if FileAccess.file_exists(path):
			var s := AudioStreamOggVorbis.load_from_file(path)
			if s != null:
				s.loop = true
				stream = s
	_music_cache[track_id] = stream
	return stream

static func clear_cache() -> void:
	_texture_cache.clear()
	_music_cache.clear()

static func _load_user_texture(rel_path: String) -> Texture2D:
	var found: Texture2D = null
	for root in USER_ROOTS:
		var path := "%s/%s" % [root, rel_path]
		if FileAccess.file_exists(path):
			var img := Image.load_from_file(path)
			if img != null:
				found = ImageTexture.create_from_image(img)
	return found
