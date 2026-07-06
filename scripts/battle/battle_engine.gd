class_name BattleEngine
extends RefCounted
## Headless turn-based battle engine. Emits an ordered list of event dicts that a UI
## can play back. No scene/autoload dependency — all data is injected in setup(),
## so the whole engine is unit-testable (see tests/ and tools/validators).
##
## Event dicts always carry a "type" key. See BATTLE_SYSTEM.md for the full list.

# --- Injected context ---
var type_chart: TypeChart
var moves_index: Dictionary = {}       # move_id -> record
var creatures_index: Dictionary = {}   # species_id -> record
var abilities_index: Dictionary = {}   # ability_id -> record
var battle_cfg: Dictionary = {}
var capture_cfg: Dictionary = {}
var exp_cfg: Dictionary = {}
var rng: RNG

## Fallback move used when a creature has no PP left on any move. Typeless (no STAB
## abuse), ignores PP, and recoils for a fraction of the damage dealt — so battles
## always terminate instead of soft-locking on full PP exhaustion.
const STRUGGLE := {
	"id": "struggle", "display_name": "Struggle", "type": "", "category": "physical",
	"power": 35, "accuracy": 100, "priority": 0,
	"effects": [ {"kind": "damage"}, {"kind": "recoil", "fraction": 0.25} ],
}

# --- Battle state ---
var player_team: Array = []            # Array[CreatureInstance]
var enemy_team: Array = []
var p_index: int = 0
var e_index: int = 0
var is_trainer_battle: bool = false
var is_boss: bool = false
var exp_multiplier: float = 1.0
var reward_multiplier: float = 1.0

var turn_count: int = 0
var finished: bool = false
var winner: String = ""                # "player" | "enemy" | "captured" | "fled"
var need_player_switch: bool = false
var captured_creature: CreatureInstance = null
var pending_evolutions: Array = []     # [{ "team_index": int, "to": String }]

func setup(ctx: Dictionary) -> void:
	type_chart = ctx["type_chart"]
	moves_index = ctx["moves_index"]
	creatures_index = ctx["creatures_index"]
	abilities_index = ctx.get("abilities_index", {})
	battle_cfg = ctx["battle_cfg"]
	capture_cfg = ctx["capture_cfg"]
	exp_cfg = ctx.get("exp_cfg", {})
	rng = ctx["rng"]
	player_team = ctx["player_team"]
	enemy_team = ctx["enemy_team"]
	is_trainer_battle = ctx.get("is_trainer_battle", false)
	is_boss = ctx.get("is_boss", false)
	exp_multiplier = float(ctx.get("exp_multiplier", 1.0))
	reward_multiplier = float(ctx.get("reward_multiplier", 1.0))
	p_index = _first_alive(player_team)
	e_index = _first_alive(enemy_team)
	for c in player_team:
		c.reset_battle_state()
	for c in enemy_team:
		c.reset_battle_state()

func active_player() -> CreatureInstance:
	return player_team[p_index]

func active_enemy() -> CreatureInstance:
	return enemy_team[e_index]

func player_available_moves() -> Array:
	return _usable_moves(active_player())

func _usable_moves(c: CreatureInstance) -> Array:
	var out: Array = []
	for i in c.moves.size():
		if int(c.moves[i].get("pp", 0)) > 0:
			out.append(i)
	return out

# ------------------------------------------------------------------ turn flow

func resolve_turn(player_action: Dictionary, enemy_action: Dictionary) -> Array:
	var events: Array = []
	if finished:
		return events
	turn_count += 1

	match String(player_action.get("kind", "move")):
		"capture":
			_do_capture(player_action, events)
			if not finished:
				_perform_action("enemy", enemy_action, events)
				_end_of_turn(events)
			return events
		"flee":
			if _do_flee(events):
				return events
			_perform_action("enemy", enemy_action, events)
			_end_of_turn(events)
			return events

	for entry in _order_actions(player_action, enemy_action):
		if finished:
			break
		# A queued MOVE belongs to the creature that chose it. If that creature was
		# replaced mid-turn (KO -> next sent out), the replacement does NOT inherit
		# the stale action: it gets a free switch-in, same as the player side.
		if String(entry["act"].get("kind", "move")) == "move":
			var current: CreatureInstance = active_player() if entry["side"] == "player" else active_enemy()
			if entry["actor"] != current or current.is_fainted():
				continue
		_perform_action(entry["side"], entry["act"], events)
		_check_faints(events)
		if finished or need_player_switch:
			break
	if not finished:
		# End-of-turn status ticks still run when the player must switch — the
		# (non-fainted) enemy side should not dodge its burn/poison damage.
		_end_of_turn(events)
	return events

func _order_actions(pa: Dictionary, ea: Dictionary) -> Array:
	var p := {"side": "player", "act": pa, "actor": active_player()}
	var e := {"side": "enemy", "act": ea, "actor": active_enemy()}
	var p_move: bool = String(pa.get("kind", "move")) == "move"
	var e_move: bool = String(ea.get("kind", "move")) == "move"
	# Non-move actions (switch/item) always precede moves; player before enemy.
	if not p_move and not e_move:
		return [p, e]
	if not p_move:
		return [p, e]
	if not e_move:
		return [e, p]
	# Both moves: sort by move priority, then effective speed.
	var p_prio: int = int(_move_of(active_player(), pa).get("priority", 0))
	var e_prio: int = int(_move_of(active_enemy(), ea).get("priority", 0))
	if p_prio != e_prio:
		return [p, e] if p_prio > e_prio else [e, p]
	var p_spd: int = _effective_speed(active_player())
	var e_spd: int = _effective_speed(active_enemy())
	if p_spd != e_spd:
		return [p, e] if p_spd > e_spd else [e, p]
	return [p, e] if rng.chance(0.5) else [e, p]

func _effective_speed(c: CreatureInstance) -> int:
	var spd: int = c.battle_stat("speed")
	if c.status == "paralyze":
		spd = int(floor(float(spd) * float(battle_cfg.get("paralyze_speed_multiplier", 0.5))))
	return spd

func _perform_action(side: String, act: Dictionary, events: Array) -> void:
	match String(act.get("kind", "move")):
		"switch":
			_do_switch(side, int(act.get("target_index", 0)), events)
		"item":
			_do_item(side, act, events)
		_:
			_execute_move(side, act, events)

# ------------------------------------------------------------------ moves

func _move_of(c: CreatureInstance, act: Dictionary) -> Dictionary:
	var idx: int = int(act.get("move_index", 0))
	if idx < 0 or idx >= c.moves.size():
		return {}
	return moves_index.get(String(c.moves[idx].get("id", "")), {})

func _execute_move(side: String, act: Dictionary, events: Array) -> void:
	var user: CreatureInstance = active_player() if side == "player" else active_enemy()
	var target: CreatureInstance = active_enemy() if side == "player" else active_player()
	if user.is_fainted():
		return

	# Paralysis full-skip check.
	if user.status == "paralyze" and rng.chance(float(battle_cfg.get("paralyze_skip_chance", 0.25))):
		events.append({"type": "message", "text": "%s is paralyzed and can't move!" % user.display_name()})
		return

	var move: Dictionary
	if bool(act.get("struggle", false)) or _usable_moves(user).is_empty():
		# No PP anywhere: fall back to Struggle so the battle always terminates.
		move = STRUGGLE
		events.append({"type": "message", "text": "%s has no moves left!" % user.display_name()})
	else:
		var idx: int = int(act.get("move_index", 0))
		if idx < 0 or idx >= user.moves.size():
			events.append({"type": "message", "text": "%s has no usable move!" % user.display_name()})
			return
		var move_slot: Dictionary = user.moves[idx]
		if int(move_slot.get("pp", 0)) <= 0:
			events.append({"type": "message", "text": "%s has no PP left!" % user.display_name()})
			return
		move_slot["pp"] = int(move_slot["pp"]) - 1
		move = moves_index.get(String(move_slot.get("id", "")), {})

	events.append({"type": "move_used", "side": side, "user": user.display_name(), "move": String(move.get("display_name", move.get("id", "?")))})

	if not DamageCalc.accuracy_check(move, rng):
		events.append({"type": "miss", "text": "%s's attack missed!" % user.display_name()})
		return

	for effect in move.get("effects", []):
		_apply_effect(side, user, target, move, effect, events)
		if target.is_fainted():
			break

var _last_damage_dealt: int = 0

func _apply_effect(side: String, user: CreatureInstance, target: CreatureInstance, move: Dictionary, effect: Dictionary, events: Array) -> void:
	match String(effect.get("kind", "")):
		"damage":
			_apply_damage(user, target, move, events)
		"apply_status":
			_apply_status_effect(user, target, effect, events)
		"stat_change":
			_apply_stat_change(user, target, effect, events)
		"heal":
			var amt: int = int(float(user.max_hp()) * float(effect.get("fraction", 0.5)))
			user.current_hp = min(user.max_hp(), user.current_hp + amt)
			events.append({"type": "heal", "target": user.display_name(), "amount": amt})
		"recoil":
			# Fraction of the damage just dealt bounces back onto the user (Struggle).
			var recoil: int = max(1, int(float(_last_damage_dealt) * float(effect.get("fraction", 0.25))))
			user.current_hp = max(0, user.current_hp - recoil)
			events.append({"type": "status_damage", "target": user.display_name(), "status": "recoil", "amount": recoil, "remaining": user.current_hp})
		_:
			pass

func _apply_damage(user: CreatureInstance, target: CreatureInstance, move: Dictionary, events: Array) -> void:
	var out_ab: Dictionary = abilities_index.get(user.ability, {})
	var in_ab: Dictionary = abilities_index.get(target.ability, {})
	var ability_mult: float = AbilityEffects.outgoing_multiplier(user, move, out_ab) * AbilityEffects.incoming_multiplier(target, move, in_ab)
	var res: Dictionary = DamageCalc.calc(user, target, move, type_chart, rng, battle_cfg, ability_mult)
	_last_damage_dealt = int(res["damage"])
	target.current_hp = max(0, target.current_hp - int(res["damage"]))
	var ev := {"type": "damage", "target": target.display_name(), "amount": int(res["damage"]),
		"remaining": target.current_hp, "max_hp": target.max_hp(), "critical": res["critical"], "effectiveness": res["effectiveness"]}
	events.append(ev)
	if bool(res["critical"]):
		events.append({"type": "message", "text": "A critical hit!"})
	if float(res["effectiveness"]) > 1.0:
		events.append({"type": "message", "text": "It's super effective!"})
	elif float(res["effectiveness"]) == 0.0:
		events.append({"type": "message", "text": "It had no effect..."})
	elif float(res["effectiveness"]) < 1.0:
		events.append({"type": "message", "text": "It's not very effective..."})

func _apply_status_effect(user: CreatureInstance, target: CreatureInstance, effect: Dictionary, events: Array) -> void:
	var who: CreatureInstance = user if String(effect.get("target", "enemy")) == "self" else target
	if who.status != "none":
		return
	if not rng.chance(float(effect.get("chance", 1.0))):
		return
	who.status = String(effect.get("status", "none"))
	who.status_counter = 0
	events.append({"type": "status", "target": who.display_name(), "status": who.status})

func _apply_stat_change(user: CreatureInstance, target: CreatureInstance, effect: Dictionary, events: Array) -> void:
	var who: CreatureInstance = user if String(effect.get("target", "enemy")) == "self" else target
	if not rng.chance(float(effect.get("chance", 1.0))):
		return
	var stat: String = String(effect.get("stat", ""))
	var stages: int = int(effect.get("stages", 0))
	if stages < 0 and AbilityEffects.prevents_stat_drop(who, stat, abilities_index.get(who.ability, {})):
		events.append({"type": "message", "text": "%s's %s can't be lowered!" % [who.display_name(), stat]})
		return
	var lo: int = int(battle_cfg.get("stat_stage_min", -6))
	var hi: int = int(battle_cfg.get("stat_stage_max", 6))
	who.stat_stages[stat] = clampi(int(who.stat_stages.get(stat, 0)) + stages, lo, hi)
	events.append({"type": "stat_stage", "target": who.display_name(), "stat": stat, "stages": stages})

# ------------------------------------------------------------------ switch / item / capture / flee

func _do_switch(side: String, target_index: int, events: Array) -> void:
	var team: Array = player_team if side == "player" else enemy_team
	if target_index < 0 or target_index >= team.size():
		return
	if team[target_index].is_fainted():
		return
	if side == "player":
		p_index = target_index
		need_player_switch = false
	else:
		e_index = target_index
	events.append({"type": "switch", "side": side, "name": team[target_index].display_name()})

func _do_item(side: String, act: Dictionary, events: Array) -> void:
	# Minimal in-battle item support: healing on the acting side's chosen target.
	var team: Array = player_team if side == "player" else enemy_team
	var target: CreatureInstance = team[int(act.get("target_index", p_index if side == "player" else e_index))]
	var effect: Dictionary = act.get("effect", {})
	match String(effect.get("kind", "")):
		"heal_hp":
			var amt: int = int(effect.get("amount", 0))
			target.current_hp = min(target.max_hp(), target.current_hp + amt)
			events.append({"type": "heal", "target": target.display_name(), "amount": amt})
		"cure_status":
			if target.status == String(effect.get("status", "")):
				target.status = "none"
				events.append({"type": "message", "text": "%s was cured!" % target.display_name()})
		"revive":
			if target.is_fainted():
				target.current_hp = int(float(target.max_hp()) * float(effect.get("fraction", 0.5)))
				events.append({"type": "message", "text": "%s was revived!" % target.display_name()})

func _do_capture(act: Dictionary, events: Array) -> void:
	if is_trainer_battle:
		events.append({"type": "message", "text": "You can't capture another trainer's creature!"})
		return
	var target: CreatureInstance = active_enemy()
	var ball_rate: float = float(act.get("ball_rate", 1.0))
	var res: Dictionary = CaptureCalc.attempt(target.max_hp(), target.current_hp,
		int(target.species.get("capture_rate", 45)), ball_rate, target.status, rng, capture_cfg)
	events.append({"type": "capture_attempt", "shakes": int(res["shakes"]), "caught": bool(res["caught"]), "name": target.display_name()})
	if bool(res["caught"]):
		captured_creature = target
		finished = true
		winner = "captured"
		events.append({"type": "win", "reason": "captured"})

func _do_flee(events: Array) -> bool:
	if is_trainer_battle:
		events.append({"type": "message", "text": "You can't flee from a trainer battle!"})
		return false
	var base: float = float(battle_cfg.get("flee_base", 0.5))
	var faster: bool = _effective_speed(active_player()) >= _effective_speed(active_enemy())
	var chance: float = 1.0 if faster else base
	if rng.chance(chance):
		finished = true
		winner = "fled"
		events.append({"type": "flee", "success": true})
		return true
	events.append({"type": "flee", "success": false})
	return false

# ------------------------------------------------------------------ faints / end of turn / exp

func _check_faints(events: Array) -> void:
	if active_enemy().is_fainted():
		events.append({"type": "faint", "side": "enemy", "name": active_enemy().display_name()})
		_award_exp(active_enemy(), events)
		var nxt: int = _first_alive(enemy_team)
		if nxt == -1:
			finished = true
			winner = "player"
			events.append({"type": "win", "reason": "enemy_defeated"})
		else:
			e_index = nxt
			events.append({"type": "enemy_switch", "name": active_enemy().display_name()})
	if not finished and not need_player_switch and active_player().is_fainted():
		events.append({"type": "faint", "side": "player", "name": active_player().display_name()})
		if _first_alive(player_team) == -1:
			finished = true
			winner = "enemy"
			events.append({"type": "lose", "reason": "player_defeated"})
		else:
			need_player_switch = true
			events.append({"type": "request_switch"})

func _end_of_turn(events: Array) -> void:
	for c in [active_player(), active_enemy()]:
		if c.is_fainted():
			continue
		match c.status:
			"burn":
				_status_tick(c, float(battle_cfg.get("burn_end_turn_fraction", 0.0625)), "burn", events)
			"poison":
				_status_tick(c, float(battle_cfg.get("poison_end_turn_fraction", 0.125)), "poison", events)
	_check_faints(events)

func _status_tick(c: CreatureInstance, fraction: float, label: String, events: Array) -> void:
	var dmg: int = max(1, int(float(c.max_hp()) * fraction))
	c.current_hp = max(0, c.current_hp - dmg)
	events.append({"type": "status_damage", "target": c.display_name(), "status": label, "amount": dmg, "remaining": c.current_hp})

func _award_exp(defeated: CreatureInstance, events: Array) -> void:
	var learner: CreatureInstance = active_player()
	if learner.is_fainted():
		return
	var base_exp: int = _species_base_exp(defeated.species)
	var trainer_bonus: float = float(exp_cfg.get("trainer_bonus_multiplier", 1.5))
	var gained: int = ExperienceCalc.award_for_defeat(base_exp, defeated.level, is_trainer_battle, trainer_bonus, 1)
	gained = int(max(1.0, floor(float(gained) * exp_multiplier)))
	learner.exp += gained
	events.append({"type": "exp_gain", "name": learner.display_name(), "amount": gained})
	_apply_level_ups(learner, events)

func _apply_level_ups(c: CreatureInstance, events: Array) -> void:
	var cap: int = int(exp_cfg.get("level_cap", 100))
	var curve: String = c.exp_curve()
	while c.level < cap and c.exp >= ExperienceCalc.exp_for_level(curve, c.level + 1):
		var old_max: int = c.max_hp()
		c.level += 1
		c.current_hp += (c.max_hp() - old_max)
		events.append({"type": "level_up", "name": c.display_name(), "level": c.level})
		_learn_new_moves(c, events)
		_queue_evolution(c, events)

func _learn_new_moves(c: CreatureInstance, events: Array) -> void:
	for entry in c.species.get("learnset", []):
		if int(entry.get("level", 0)) == c.level:
			var mid: String = String(entry.get("move", ""))
			if _knows_move(c, mid):
				continue
			var pp: int = int(moves_index.get(mid, {}).get("pp", 10))
			if c.moves.size() < 4:
				c.moves.append({"id": mid, "pp": pp, "max_pp": pp})
				events.append({"type": "learn_move", "name": c.display_name(), "move": mid})
			else:
				# The UI resolves this interactively (forget a move or skip).
				events.append({"type": "learn_move_full", "name": c.display_name(), "move": mid,
						"team_index": player_team.find(c)})

func _queue_evolution(c: CreatureInstance, events: Array) -> void:
	# Evolution eligibility is resolved after battle by EvolutionSystem against
	# data/evolutions.json. Here we only flag that a level-up happened so the
	# post-battle step knows to check this team member.
	var team_idx: int = player_team.find(c)
	if team_idx == -1:
		return
	events.append({"type": "check_evolution", "team_index": team_idx, "species_id": c.species_id, "level": c.level})

func _knows_move(c: CreatureInstance, mid: String) -> bool:
	for m in c.moves:
		if String(m.get("id", "")) == mid:
			return true
	return false

func _species_base_exp(species: Dictionary) -> int:
	var total: int = 0
	for k in StatMath.STAT_KEYS:
		total += int(species.get("base_stats", {}).get(k, 0))
	return int(max(20, total / 6))

func _first_alive(team: Array) -> int:
	for i in team.size():
		if not team[i].is_fainted():
			return i
	return -1
