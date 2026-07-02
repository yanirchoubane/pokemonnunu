extends SceneTree
## Headless GDScript test runner for the engine-independent core.
## Run:  godot --headless --script res://tests/run_tests.gd
##
## Self-contained: loads data directly (no autoloads needed) and exercises the same
## class_name logic the game uses. Mirrors tests/test_reference.py so the GDScript and
## Python twins are pinned to the same numbers. Uses a fixed RNG seed for determinism.

var _pass := 0
var _fail := 0
var _data_root := "res://data"

func _initialize() -> void:
	print("== Creature RPG core tests ==")
	_test_rng()
	_test_stat_math()
	_test_type_chart()
	_test_damage()
	_test_capture()
	_test_experience()
	_test_creature_factory()
	_test_full_battle()
	print("\n%d passed, %d failed" % [_pass, _fail])
	quit(1 if _fail > 0 else 0)

func _check(name: String, cond: bool, detail: String = "") -> void:
	if cond:
		_pass += 1
		print("  ok  ", name)
	else:
		_fail += 1
		print("  FAIL ", name, "  ", detail)

func _load(path: String) -> Dictionary:
	var f := FileAccess.open(path, FileAccess.READ)
	return JSON.parse_string(f.get_as_text())

func _index(arr: Array, key: String) -> Dictionary:
	var d := {}
	for r in arr:
		d[String(r[key])] = r
	return d

# ------------------------------------------------------------------ tests

func _test_rng() -> void:
	print("RNG")
	var a := RNG.new(12345)
	var b := RNG.new(12345)
	var sa := []
	var sb := []
	for i in 5:
		sa.append(a.next_u32())
		sb.append(b.next_u32())
	_check("same seed -> same sequence", sa == sb)
	var c := RNG.new(999)
	var sc := []
	for i in 5:
		sc.append(c.next_u32())
	_check("different seed -> different sequence", sc != sa)
	var d := RNG.new(7)
	var ok := true
	for i in 100:
		var v := d.randf()
		if v < 0.0 or v >= 1.0:
			ok = false
	_check("randf in [0,1)", ok)

func _test_stat_math() -> void:
	print("StatMath")
	_check("stage +1 = 1.5", abs(StatMath.stage_multiplier(1) - 1.5) < 1e-6)
	_check("stage -1 = 2/3", abs(StatMath.stage_multiplier(-1) - (2.0 / 3.0)) < 1e-6)
	_check("nature up 1.1", abs(StatMath.nature_multiplier("brave", "attack") - 1.1) < 1e-6)
	_check("nature down 0.9", abs(StatMath.nature_multiplier("brave", "speed") - 0.9) < 1e-6)
	_check("hp formula", StatMath.compute_hp(45, 31, 0, 50) == int(floor(float((2 * 45 + 31) * 50) / 100.0)) + 50 + 10)

func _test_type_chart() -> void:
	print("TypeChart")
	var tc := TypeChart.new()
	tc.load_from(_load("%s/types/types.json" % _data_root))
	_check("fire>grass 2x", tc.pair_multiplier("fire", "grass") == 2.0)
	_check("electric>earth 0x", tc.pair_multiplier("electric", "earth") == 0.0)
	_check("dual product 4x", tc.effectiveness("water", ["fire", "earth"]) == 4.0)
	_check("default 1.0", tc.effectiveness("normal", ["water"]) == 1.0)

func _ctx() -> Dictionary:
	var creatures := _index(_load("%s/creatures/creatures.json" % _data_root)["creatures"], "id")
	var moves := _index(_load("%s/moves/moves.json" % _data_root)["moves"], "id")
	var balancing := _load("%s/balancing/balancing.json" % _data_root)
	var tc := TypeChart.new()
	tc.load_from(_load("%s/types/types.json" % _data_root))
	return {"creatures": creatures, "moves": moves, "balancing": balancing, "tc": tc}

func _mk(ctx: Dictionary, id: String, level: int) -> CreatureInstance:
	return CreatureFactory.build(ctx["creatures"][id], level, RNG.new(1), ctx["moves"], {"perfect_ivs": true})

func _test_damage() -> void:
	print("DamageCalc")
	var ctx := _ctx()
	var cfg: Dictionary = ctx["balancing"]["battle"]
	var ember := _mk(ctx, "emberpup", 12)
	var aqua := _mk(ctx, "aquafin", 12)
	var r := DamageCalc.calc(ember, aqua, ctx["moves"]["ember_burst"], ctx["tc"], RNG.new(42), cfg)
	_check("fire vs water not-very-effective", float(r["effectiveness"]) == 0.5)
	_check("damage >= 1", int(r["damage"]) >= 1)
	var zap := _mk(ctx, "zapmouse", 15)
	var pebble := _mk(ctx, "pebblet", 15)
	var r2 := DamageCalc.calc(zap, pebble, ctx["moves"]["spark_zap"], ctx["tc"], RNG.new(7), cfg)
	_check("electric vs earth deals 0", int(r2["damage"]) == 0)

func _test_capture() -> void:
	print("CaptureCalc")
	var ctx := _ctx()
	var cap: Dictionary = ctx["balancing"]["capture"]
	var r := CaptureCalc.attempt(50, 50, 45, 1.0, "none", RNG.new(3), cap)
	var r2 := CaptureCalc.attempt(50, 1, 120, 1.5, "paralyze", RNG.new(3), cap)
	_check("low-hp+status prob > full-hp prob", float(r2["probability"]) > float(r["probability"]))
	# Monte-carlo on one continuous stream
	var stream := RNG.new(1234)
	var caught := 0
	for i in 5000:
		if bool(CaptureCalc.attempt(50, 20, 90, 1.0, "none", stream, cap)["caught"]):
			caught += 1
	var emp := float(caught) / 5000.0
	var exp := float(CaptureCalc.attempt(50, 20, 90, 1.0, "none", RNG.new(1), cap)["probability"])
	_check("empirical ~ probability (±0.04)", abs(emp - exp) < 0.04, "emp=%.3f exp=%.3f" % [emp, exp])

func _test_experience() -> void:
	print("ExperienceCalc")
	_check("medium_fast L10 = 1000", ExperienceCalc.exp_for_level("medium_fast", 10) == 1000)
	_check("level_for_exp inverse", ExperienceCalc.level_for_exp("medium_fast", 1000) == 10)
	_check("cap respected", ExperienceCalc.level_for_exp("medium_fast", 1000000000000, 100) == 100)

func _test_creature_factory() -> void:
	print("CreatureFactory")
	var ctx := _ctx()
	var c := _mk(ctx, "emberpup", 5)
	_check("builds with <=4 moves", c.moves.size() <= 4 and c.moves.size() > 0)
	_check("hp initialized", c.current_hp == c.max_hp() and c.max_hp() > 0)
	_check("exp matches level", c.exp == ExperienceCalc.exp_for_level("medium_fast", 5))

func _test_full_battle() -> void:
	print("BattleEngine end-to-end")
	var ctx := _ctx()
	var player := [_mk(ctx, "emberpup", 12)]
	var enemy := [_mk(ctx, "sproutkit", 8)]
	var engine := BattleEngine.new()
	engine.setup({
		"type_chart": ctx["tc"], "moves_index": ctx["moves"], "creatures_index": ctx["creatures"],
		"abilities_index": {}, "battle_cfg": ctx["balancing"]["battle"], "capture_cfg": ctx["balancing"]["capture"],
		"exp_cfg": ctx["balancing"]["experience"], "rng": RNG.new(99),
		"player_team": player, "enemy_team": enemy, "is_trainer_battle": false,
	})
	var guard := 0
	while not engine.finished and guard < 200:
		guard += 1
		var moves := engine.player_available_moves()
		var pa := {"kind": "move", "move_index": moves[0] if moves.size() > 0 else 0}
		var ai := BattleAI.choose_action(engine, "intermediate")
		engine.resolve_turn(pa, ai["action"])
		if engine.need_player_switch:
			break
	_check("battle terminates", engine.finished, "guard=%d" % guard)
	_check("has a winner", engine.winner != "")
	_check("emberpup gained exp", player[0].exp >= ExperienceCalc.exp_for_level("medium_fast", 12))
