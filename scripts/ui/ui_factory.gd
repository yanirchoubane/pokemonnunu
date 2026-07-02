class_name UIFactory
extends RefCounted
## Small helpers to build consistent UI controls in code (keeps .tscn files tiny and
## avoids brittle scene wiring). Colors here are original placeholder styling.

const BG := Color("#1e2330")
const PANEL := Color("#2b3247")
const ACCENT := Color("#4c7bd5")
const TEXT := Color("#e8ecf5")

static func make_panel(size: Vector2 = Vector2.ZERO) -> PanelContainer:
	var p := PanelContainer.new()
	var sb := StyleBoxFlat.new()
	sb.bg_color = PANEL
	sb.set_corner_radius_all(8)
	sb.set_content_margin_all(10)
	sb.border_color = ACCENT
	sb.set_border_width_all(2)
	p.add_theme_stylebox_override("panel", sb)
	if size != Vector2.ZERO:
		p.custom_minimum_size = size
	return p

static func make_label(text: String, size: int = 18, color: Color = TEXT) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	return l

static func make_title(text: String, size: int = 40) -> Label:
	var l := make_label(text, size, ACCENT)
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	return l

static func make_button(text: String) -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size = Vector2(220, 40)
	b.add_theme_font_size_override("font_size", 18)
	return b

static func make_fullscreen_bg(color: Color = BG) -> ColorRect:
	var r := ColorRect.new()
	r.color = color
	r.set_anchors_preset(Control.PRESET_FULL_RECT)
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return r

## Convert a text-speed setting into seconds-per-character for typewriter effects.
static func text_speed_delay() -> float:
	match String(SettingsManager.get_value("text_speed", "normal")):
		"slow": return 0.05
		"fast": return 0.012
		"instant": return 0.0
		_: return 0.025
