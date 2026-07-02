extends Node
## AudioManager (autoload): per-zone background music and SFX using ONLY procedurally
## generated tones (no third-party audio assets). Everything is honest placeholder
## content; swap in your own legally-obtained audio via assets/placeholder_audio later.

const MIX_RATE := 22050

var _music_player: AudioStreamPlayer
var _sfx_player: AudioStreamPlayer
var _current_zone: String = ""
var _tone_cache: Dictionary = {}

# Simple original zone themes: each is a short arpeggio (Hz) looped.
const ZONE_THEMES := {
	"town":   [262.0, 330.0, 392.0, 330.0],
	"route":  [294.0, 370.0, 440.0, 370.0],
	"forest": [220.0, 262.0, 330.0, 262.0],
	"indoor": [349.0, 440.0, 523.0, 440.0],
	"shore":  [247.0, 311.0, 370.0, 311.0],
	"ridge":  [196.0, 247.0, 294.0, 247.0],
	"battle": [330.0, 415.0, 494.0, 587.0],
	"title":  [262.0, 392.0, 523.0, 392.0],
}

func _ready() -> void:
	_music_player = AudioStreamPlayer.new()
	_music_player.bus = "Master"
	add_child(_music_player)
	_sfx_player = AudioStreamPlayer.new()
	_sfx_player.bus = "Master"
	add_child(_sfx_player)
	_apply_volumes()
	if SettingsManager.has_signal("settings_changed"):
		SettingsManager.settings_changed.connect(_apply_volumes)

func _apply_volumes() -> void:
	var music_v: float = float(SettingsManager.get_value("music_volume", 0.8))
	var sfx_v: float = float(SettingsManager.get_value("sfx_volume", 0.9))
	_music_player.volume_db = linear_to_db(clampf(music_v, 0.0, 1.0)) if music_v > 0.0 else -80.0
	_sfx_player.volume_db = linear_to_db(clampf(sfx_v, 0.0, 1.0)) if sfx_v > 0.0 else -80.0

func play_zone_music(zone: String) -> void:
	if zone == _current_zone and _music_player.playing:
		return
	_current_zone = zone
	var theme: Array = ZONE_THEMES.get(zone, ZONE_THEMES["town"])
	_music_player.stream = _theme_stream(zone, theme)
	if float(SettingsManager.get_value("music_volume", 0.8)) > 0.0:
		_music_player.play()

func stop_music() -> void:
	_music_player.stop()
	_current_zone = ""

func play_sfx(kind: String) -> void:
	var freq := 660.0
	match kind:
		"select": freq = 660.0
		"confirm": freq = 880.0
		"cancel": freq = 330.0
		"hit": freq = 220.0
		"faint": freq = 165.0
		"heal": freq = 990.0
	_sfx_player.stream = _make_tone("sfx_%s" % kind, freq, 0.12, false)
	if float(SettingsManager.get_value("sfx_volume", 0.9)) > 0.0:
		_sfx_player.play()

# ------------------------------------------------------------------ tone generation

func _theme_stream(zone: String, notes: Array) -> AudioStreamWAV:
	var key := "theme_%s" % zone
	if _tone_cache.has(key):
		return _tone_cache[key]
	var note_len := 0.35
	var frames := int(MIX_RATE * note_len)
	var data := PackedByteArray()
	for n in notes:
		var freq: float = float(n)
		for i in frames:
			var t := float(i) / float(MIX_RATE)
			# soft envelope to avoid clicks
			var env := sin(PI * float(i) / float(frames))
			var s := sin(TAU * freq * t) * 0.25 * env
			var v := int(clampf(s, -1.0, 1.0) * 32767.0)
			data.append(v & 0xFF)
			data.append((v >> 8) & 0xFF)
	var stream := AudioStreamWAV.new()
	stream.format = AudioStreamWAV.FORMAT_16_BITS
	stream.mix_rate = MIX_RATE
	stream.stereo = false
	stream.data = data
	stream.loop_mode = AudioStreamWAV.LOOP_FORWARD
	stream.loop_begin = 0
	stream.loop_end = notes.size() * frames
	_tone_cache[key] = stream
	return stream

func _make_tone(key: String, freq: float, seconds: float, loop: bool) -> AudioStreamWAV:
	if _tone_cache.has(key):
		return _tone_cache[key]
	var frames := int(MIX_RATE * seconds)
	var data := PackedByteArray()
	for i in frames:
		var t := float(i) / float(MIX_RATE)
		var env := 1.0 - float(i) / float(frames)  # decay
		var s := sin(TAU * freq * t) * 0.3 * env
		var v := int(clampf(s, -1.0, 1.0) * 32767.0)
		data.append(v & 0xFF)
		data.append((v >> 8) & 0xFF)
	var stream := AudioStreamWAV.new()
	stream.format = AudioStreamWAV.FORMAT_16_BITS
	stream.mix_rate = MIX_RATE
	stream.stereo = false
	stream.data = data
	if loop:
		stream.loop_mode = AudioStreamWAV.LOOP_FORWARD
		stream.loop_end = frames
	_tone_cache[key] = stream
	return stream
