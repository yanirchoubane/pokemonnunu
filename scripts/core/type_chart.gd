class_name TypeChart
extends RefCounted
## Type effectiveness lookup, built from data/types/types.json.
## Pure data; no scene dependencies.

var _chart: Dictionary = {}          # attacking_type -> { defending_type -> float }
var _valid_types: Dictionary = {}    # type_id -> true

func load_from(types_data: Dictionary) -> void:
	_chart = {}
	_valid_types = {}
	for t in types_data.get("types", []):
		_valid_types[t["id"]] = true
	var chart: Dictionary = types_data.get("chart", {})
	for atk in chart.keys():
		_chart[atk] = {}
		for def in chart[atk].keys():
			_chart[atk][def] = float(chart[atk][def])

func is_valid_type(type_id: String) -> bool:
	return _valid_types.has(type_id)

func all_types() -> Array:
	return _valid_types.keys()

## Multiplier of a single attacking type vs a single defending type. Default 1.0.
func pair_multiplier(attacking_type: String, defending_type: String) -> float:
	if _chart.has(attacking_type) and _chart[attacking_type].has(defending_type):
		return _chart[attacking_type][defending_type]
	return 1.0

## Multiplier of an attacking type against a (mono or dual) defender.
func effectiveness(attacking_type: String, defender_types: Array) -> float:
	var mult: float = 1.0
	for dt in defender_types:
		mult *= pair_multiplier(attacking_type, String(dt))
	return mult
