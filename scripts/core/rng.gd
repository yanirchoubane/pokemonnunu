class_name RNG
extends RefCounted
## Deterministic, seedable pseudo-random generator (xorshift32).
##
## Uses 32-bit masked arithmetic so results are IDENTICAL across GDScript and the
## Python reference implementation in tools/validators/battle_reference.py.
## Never use Godot's global randi()/randf() in battle logic — always use an RNG
## instance so battles are reproducible from a saved seed.

const MASK32: int = 0xFFFFFFFF

var _state: int = 0x1234ABCD

func _init(seed_value: int = 0x1234ABCD) -> void:
	set_seed(seed_value)

func set_seed(seed_value: int) -> void:
	# State must be non-zero for xorshift.
	_state = (seed_value & MASK32)
	if _state == 0:
		_state = 0x1234ABCD

func get_state() -> int:
	return _state

func restore_state(state: int) -> void:
	_state = state & MASK32
	if _state == 0:
		_state = 0x1234ABCD

## Returns the next raw 32-bit unsigned integer.
func next_u32() -> int:
	var x: int = _state
	x = (x ^ ((x << 13) & MASK32)) & MASK32
	x = (x ^ (x >> 17)) & MASK32
	x = (x ^ ((x << 5) & MASK32)) & MASK32
	_state = x
	return x

## Float in [0, 1).
func randf() -> float:
	return float(next_u32()) / 4294967296.0

## Integer in [min_value, max_value] inclusive.
func randi_range(min_value: int, max_value: int) -> int:
	if max_value <= min_value:
		return min_value
	var span: int = (max_value - min_value) + 1
	return min_value + (next_u32() % span)

## True with probability p (0..1).
func chance(p: float) -> bool:
	if p <= 0.0:
		return false
	if p >= 1.0:
		return true
	return randf() < p

## Weighted pick: weights is Array[int] or Array[float]; returns the chosen index.
func weighted_index(weights: Array) -> int:
	var total: float = 0.0
	for w in weights:
		total += float(w)
	if total <= 0.0:
		return 0
	var roll: float = randf() * total
	var acc: float = 0.0
	for i in weights.size():
		acc += float(weights[i])
		if roll < acc:
			return i
	return weights.size() - 1
