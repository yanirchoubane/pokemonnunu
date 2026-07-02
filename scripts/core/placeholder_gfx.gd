class_name PlaceholderGfx
extends RefCounted
## Generates ALL demo visuals procedurally (geometric shapes / solid colors).
## No third-party art is used or bundled. Replace by dropping real textures into
## assets/ and referencing them from data — the engine reads sprite ids from data.

const TYPE_COLORS := {
	"normal": Color("#b8b8a0"), "fire": Color("#e6642e"), "water": Color("#2e78e6"),
	"grass": Color("#4caf50"), "electric": Color("#f2c94c"), "earth": Color("#a1662f"),
	"wind": Color("#8ec9d6"), "mystic": Color("#9b59b6"),
}

const TILE_COLORS := {
	"ground": Color("#8fbf6f"), "path": Color("#d9c08a"), "wall": Color("#5a5a66"),
	"tree": Color("#2e6b34"), "tall_grass": Color("#5fa64f"), "water": Color("#3a78c9"),
	"floor": Color("#c9b48a"), "counter": Color("#8a6d3b"), "door": Color("#7a4a1e"),
	"heal_pad": Color("#e26d8a"), "sand": Color("#e6d6a8"), "palm": Color("#2e6b34"),
	"pine": Color("#255c2c"), "stone": Color("#9a9aa2"),
	"building_lab": Color("#c9c9d6"), "building_center": Color("#e2a0a0"), "building_shop": Color("#a0c9e2"),
}

static func type_color(type_id: String) -> Color:
	return TYPE_COLORS.get(type_id, Color("#aaaaaa"))

static func tile_color(tile_type: String) -> Color:
	return TILE_COLORS.get(tile_type, Color("#7f7f7f"))

## Deterministic hue from a string id, so each creature/npc looks distinct & stable.
static func id_color(id: String, sat: float = 0.55, val: float = 0.85) -> Color:
	var h := 0
	for i in id.length():
		h = (h * 31 + id.unicode_at(i)) & 0x7FFFFFFF
	var hue := float(h % 360) / 360.0
	return Color.from_hsv(hue, sat, val)

## Build a small creature "sprite": a colored body shape derived from its id and types.
static func make_creature_texture(species: Dictionary, size: int = 48) -> ImageTexture:
	var img := Image.create(size, size, false, Image.FORMAT_RGBA8)
	img.fill(Color(0, 0, 0, 0))
	var types: Array = species.get("types", [])
	var primary: Color = type_color(String(types[0])) if types.size() > 0 else id_color(String(species.get("id", "x")))
	var accent: Color = type_color(String(types[1])) if types.size() > 1 else primary.lightened(0.25)
	var cx := size / 2
	var cy := size / 2
	var r := size / 2 - 2
	# shape variant from id hash: 0 circle, 1 diamond, 2 rounded square
	var variant := 0
	for i in String(species.get("id", "x")).length():
		variant += String(species.get("id", "x")).unicode_at(i)
	variant = variant % 3
	for y in size:
		for x in size:
			var inside := false
			match variant:
				0:
					inside = (x - cx) * (x - cx) + (y - cy) * (y - cy) <= r * r
				1:
					inside = abs(x - cx) + abs(y - cy) <= r
				_:
					inside = abs(x - cx) <= r - 2 and abs(y - cy) <= r - 2
			if inside:
				var c: Color = primary if (y < cy) else accent
				img.set_pixel(x, y, c)
	# simple eyes
	img.set_pixel(cx - r / 3, cy - r / 4, Color.BLACK)
	img.set_pixel(cx + r / 3, cy - r / 4, Color.BLACK)
	return ImageTexture.create_from_image(img)

static func make_solid_texture(color: Color, w: int = 32, h: int = 32) -> ImageTexture:
	var img := Image.create(w, h, false, Image.FORMAT_RGBA8)
	img.fill(color)
	return ImageTexture.create_from_image(img)
