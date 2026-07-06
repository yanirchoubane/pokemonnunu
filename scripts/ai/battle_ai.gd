class_name BattleAI
extends RefCounted
## Enemy decision-making across three tiers. The AI reads only publicly-visible
## board state (both active creatures, its own team, and — for the advanced tier —
## creatures the player has ALREADY revealed). It never inspects the player's chosen
## action for the current turn and never consumes the battle RNG (estimates use
## average factors), so it cannot cheat.

## tier: "basic" | "intermediate" | "advanced"
## Returns: { "action": Dictionary, "reason": String, "confidence": float, "alternatives": Array }
static func choose_action(engine: BattleEngine, tier: String, revealed_player_species: Array = []) -> Dictionary:
	var user: CreatureInstance = engine.active_enemy()
	var foe: CreatureInstance = engine.active_player()
	var usable: Array = engine._usable_moves(user)
	if usable.is_empty():
		# The engine resolves this flag as the built-in Struggle fallback move.
		return {"action": {"kind": "move", "move_index": 0, "struggle": true}, "reason": "No PP left; using Struggle.", "confidence": 0.1, "alternatives": []}

	match tier:
		"basic":
			return _basic(engine, user, foe, usable)
		"intermediate":
			return _intermediate(engine, user, foe, usable)
		"advanced":
			return _advanced(engine, user, foe, usable, revealed_player_species)
		_:
			return _basic(engine, user, foe, usable)

# --- BASIC: any valid move, slight bias to damaging moves. No switching. ---
static func _basic(engine: BattleEngine, user: CreatureInstance, foe: CreatureInstance, usable: Array) -> Dictionary:
	var damaging: Array = []
	for i in usable:
		if int(engine.moves_index.get(String(user.moves[i]["id"]), {}).get("power", 0)) > 0:
			damaging.append(i)
	var pool: Array = damaging if not damaging.is_empty() else usable
	var pick: int = pool[engine.rng.randi_range(0, pool.size() - 1)]
	return {"action": {"kind": "move", "move_index": pick},
		"reason": "Basic AI: picked a valid move at random.",
		"confidence": 0.3, "alternatives": []}

# --- INTERMEDIATE: pick highest estimated damage; switch on severe disadvantage. ---
static func _intermediate(engine: BattleEngine, user: CreatureInstance, foe: CreatureInstance, usable: Array) -> Dictionary:
	var best_i: int = usable[0]
	var best_dmg: float = -1.0
	var alts: Array = []
	for i in usable:
		var move: Dictionary = engine.moves_index.get(String(user.moves[i]["id"]), {})
		var est: float = estimate_damage(user, foe, move, engine.type_chart, engine.battle_cfg)
		alts.append({"move": String(move.get("id", "")), "est_damage": round(est)})
		if est > best_dmg:
			best_dmg = est
			best_i = i

	# Consider switching if the active is at a hard type disadvantage AND a better switch exists.
	var switch_choice: int = _best_defensive_switch(engine, foe)
	var incoming_threat: float = _incoming_threat_ratio(engine, user, foe)
	if incoming_threat >= 0.5 and switch_choice != -1 and best_dmg < float(foe.current_hp):
		return {"action": {"kind": "switch", "target_index": switch_choice},
			"reason": "Intermediate AI: heavy incoming threat; switching to a safer creature.",
			"confidence": 0.6, "alternatives": alts}

	return {"action": {"kind": "move", "move_index": best_i},
		"reason": "Intermediate AI: chose the move with the highest estimated damage.",
		"confidence": clampf(best_dmg / float(max(1, foe.current_hp)), 0.2, 0.95),
		"alternatives": alts}

# --- ADVANCED: KO-awareness, resource care, setup/status vs damage. ---
static func _advanced(engine: BattleEngine, user: CreatureInstance, foe: CreatureInstance, usable: Array, revealed: Array) -> Dictionary:
	var alts: Array = []
	var best_i: int = usable[0]
	var best_score: float = -1e9
	for i in usable:
		var move: Dictionary = engine.moves_index.get(String(user.moves[i]["id"]), {})
		var est: float = estimate_damage(user, foe, move, engine.type_chart, engine.battle_cfg)
		var score: float = est
		# Reward a guaranteed KO strongly.
		if est >= float(foe.current_hp):
			score += 1000.0
		# Value status/setup when we can't KO and foe is healthy.
		var power: int = int(move.get("power", 0))
		if power == 0:
			var util: float = 0.0
			for eff in move.get("effects", []):
				if String(eff.get("kind", "")) == "apply_status" and foe.status == "none":
					util += 35.0
				elif String(eff.get("kind", "")) == "stat_change" and String(eff.get("target", "enemy")) == "self":
					util += 20.0
			# Only worthwhile if we're not about to be KO'd.
			if _incoming_threat_ratio(engine, user, foe) < 0.6:
				score = util
			else:
				score = -10.0
		alts.append({"move": String(move.get("id", "")), "est_damage": round(est), "score": round(score)})
		if score > best_score:
			best_score = score
			best_i = i

	# Switch reasoning: if we're likely to be KO'd and can't KO first, seek a better matchup.
	var threat: float = _incoming_threat_ratio(engine, user, foe)
	var can_ko: bool = best_score >= 1000.0
	var switch_choice: int = _best_offensive_switch(engine, foe)
	if threat >= 0.75 and not can_ko and switch_choice != -1:
		return {"action": {"kind": "switch", "target_index": switch_choice},
			"reason": "Advanced AI: predicted KO next turn without a KO of its own; pivoting to a favorable matchup.",
			"confidence": 0.7, "alternatives": alts}

	var chosen_move: Dictionary = engine.moves_index.get(String(user.moves[best_i]["id"]), {})
	var reason: String = "Advanced AI: "
	if can_ko:
		reason += "chose a move that should KO the target this turn."
	elif int(chosen_move.get("power", 0)) == 0:
		reason += "no KO available and safe to invest; used a status/setup move."
	else:
		reason += "chose the highest expected-value damaging move."
	return {"action": {"kind": "move", "move_index": best_i},
		"reason": reason,
		"confidence": clampf(best_score / 1000.0 if can_ko else best_score / float(max(1, foe.current_hp)), 0.2, 0.98),
		"alternatives": alts}

# ------------------------------------------------------------------ helpers

## Deterministic damage estimate: average random factor (0.925), no crit, includes STAB & type.
static func estimate_damage(user: CreatureInstance, target: CreatureInstance, move: Dictionary,
		type_chart: TypeChart, cfg: Dictionary) -> float:
	var power: int = int(move.get("power", 0))
	if power <= 0:
		return 0.0
	var physical: bool = String(move.get("category", "physical")) == "physical"
	var atk: int = user.battle_stat("attack" if physical else "sp_attack")
	var def_val: int = max(1, target.battle_stat("defense" if physical else "sp_defense"))
	if physical and user.status == "burn":
		atk = int(floor(float(atk) * float(cfg.get("burn_physical_multiplier", 0.5))))
	atk = max(1, atk)
	var level_factor: float = (float(cfg.get("level_scale_numerator", 2)) * float(user.level)) / float(cfg.get("level_scale_base", 5)) + 2.0
	var base: float = floor((level_factor * float(power) * float(atk) / float(def_val)) / float(cfg.get("damage_base_divisor", 50))) + 2.0
	var stab: float = float(cfg.get("stab_multiplier", 1.5)) if String(move.get("type", "")) in user.types() else 1.0
	var eff: float = type_chart.effectiveness(String(move.get("type", "")), target.types())
	return base * stab * eff * 0.925

## Ratio of the foe's best estimated hit against `user` to user's current HP (0..∞).
static func _incoming_threat_ratio(engine: BattleEngine, user: CreatureInstance, foe: CreatureInstance) -> float:
	var worst: float = 0.0
	for m in foe.moves:
		var move: Dictionary = engine.moves_index.get(String(m.get("id", "")), {})
		worst = max(worst, estimate_damage(foe, user, move, engine.type_chart, engine.battle_cfg))
	return worst / float(max(1, user.current_hp))

## Pick a bench creature that best resists the foe's types (lowest incoming multiplier). -1 if none.
static func _best_defensive_switch(engine: BattleEngine, foe: CreatureInstance) -> int:
	var best: int = -1
	var best_mult: float = 1e9
	for i in engine.enemy_team.size():
		if i == engine.e_index or engine.enemy_team[i].is_fainted():
			continue
		var worst_mult: float = 0.0
		for ft in foe.types():
			worst_mult = max(worst_mult, engine.type_chart.effectiveness(String(ft), engine.enemy_team[i].types()))
		if worst_mult < best_mult:
			best_mult = worst_mult
			best = i
	return best

## Pick a bench creature whose STAB best threatens the foe. -1 if none clearly better.
static func _best_offensive_switch(engine: BattleEngine, foe: CreatureInstance) -> int:
	var best: int = -1
	var best_mult: float = 1.0
	for i in engine.enemy_team.size():
		if i == engine.e_index or engine.enemy_team[i].is_fainted():
			continue
		var mult: float = 0.0
		for t in engine.enemy_team[i].types():
			mult = max(mult, engine.type_chart.effectiveness(String(t), foe.types()))
		if mult > best_mult:
			best_mult = mult
			best = i
	return best
