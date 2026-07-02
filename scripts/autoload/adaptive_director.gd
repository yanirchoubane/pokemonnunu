extends Node
## AdaptiveDirector (autoload): measures player performance across battles, keeps a
## SMOOTHED skill score (0..100), and translates it into BOUNDED scaling of enemy
## level / AI tier / rewards / encounter rate.
##
## Hard rules (enforced here):
##  - Never touches the player's own creatures' stats.
##  - Never makes each enemy exactly equal to the player (deltas are small & bounded).
##  - Smoothed: updates after several battles, not after a single action.
##  - Bosses get only limited scaling and keep their scripted identity.
##  - Fully disable-able; supports Relaxed / Normal / Hard / Adaptive modes.

signal skill_changed(score: float)

var _cfg: Dictionary = {}

func _ready() -> void:
	_cfg = DataRegistry.adaptive_config

func _state() -> Dictionary:
	# Lives inside GameState.adaptive_state so it is saved/loaded with the game.
	if GameState.adaptive_state.is_empty():
		var ss: Dictionary = _cfg.get("skill_score", {})
		GameState.adaptive_state = {
			"skill_score": float(ss.get("initial", 50.0)),
			"battles_recorded": 0,
			"current_level_delta": 0,
			"last_adaptations": [],
		}
	return GameState.adaptive_state

func skill_score() -> float:
	return float(_state().get("skill_score", 50.0))

func _mode() -> String:
	return String(SettingsManager.get_value("difficulty", "adaptive"))

func _mode_cfg() -> Dictionary:
	return _cfg.get("difficulty_modes", {}).get(_mode(), _cfg.get("difficulty_modes", {}).get("normal", {}))

func adaptation_enabled() -> bool:
	if not bool(SettingsManager.get_value("adaptive_enabled", true)):
		return false
	return bool(_mode_cfg().get("adapt", false))

# ------------------------------------------------------------------ measurement

## Record the outcome of a completed battle. `summary` keys (all optional):
##  won:bool, flawless:bool, items_used:int, used_type_advantage:bool,
##  level_underdog:bool, player_avg_level:float, enemy_avg_level:float
func record_battle_result(summary: Dictionary) -> void:
	var st := _state()
	var ss: Dictionary = _cfg.get("skill_score", {})
	var w: Dictionary = ss.get("weights", {})
	var delta: float = 0.0
	if bool(summary.get("won", false)):
		delta += float(w.get("win", 6.0))
		if bool(summary.get("flawless", false)):
			delta += float(w.get("flawless_win", 3.0))
	else:
		delta += float(w.get("loss", -8.0))
	if int(summary.get("items_used", 0)) >= 3:
		delta += float(w.get("item_heavy_penalty", -2.0))
	if bool(summary.get("used_type_advantage", false)):
		delta += float(w.get("type_advantage_usage", 2.0))
	if bool(summary.get("level_underdog", false)):
		delta += float(w.get("level_underdog_bonus", 4.0))

	var smoothing: float = float(ss.get("smoothing", 0.25))
	var lo: float = float(ss.get("min", 0.0))
	var hi: float = float(ss.get("max", 100.0))
	var cur: float = float(st.get("skill_score", 50.0))
	# Smoothed accumulation: move a fraction of the delta each battle.
	var new_score: float = clampf(cur + smoothing * delta, lo, hi)
	st["skill_score"] = new_score
	st["battles_recorded"] = int(st.get("battles_recorded", 0)) + 1
	skill_changed.emit(new_score)

# ------------------------------------------------------------------ scaling policy

## Returns enemy scaling for an upcoming battle.
##  { level_delta:int, ai_tier:String, reward_multiplier:float, reason:String }
func get_enemy_scaling(trainer_ai_tier: String, is_boss: bool) -> Dictionary:
	var mode := _mode()
	var mode_cfg := _mode_cfg()
	var bounds: Dictionary = _cfg.get("scaling_bounds", {})
	var reward: float = float(mode_cfg.get("reward_multiplier", 1.0))
	var result := {
		"level_delta": int(mode_cfg.get("enemy_level_delta", 0)),
		"ai_tier": _cap_tier(trainer_ai_tier, String(mode_cfg.get("ai_tier_cap", "advanced"))),
		"reward_multiplier": reward,
		"reason": "Fixed by '%s' difficulty." % mode,
	}

	if not adaptation_enabled():
		if is_boss:
			result["ai_tier"] = trainer_ai_tier  # bosses keep their scripted AI
		return result

	var ss: Dictionary = _cfg.get("skill_score", {})
	var st := _state()
	if int(st.get("battles_recorded", 0)) < int(ss.get("min_battles_before_adapt", 3)):
		result["reason"] = "Gathering data (need more battles before adapting)."
		return result

	var intensity: float = clampf(float(SettingsManager.get_value("adaptive_intensity", 0.5)), 0.0, 1.0)
	var max_scaling: int = int(SettingsManager.get_value("adaptive_max_scaling", 3))
	var skill := skill_score()
	var norm: float = (skill - 50.0) / 50.0  # -1..1

	# Target delta scaled by intensity & user cap, then bounded.
	var target_delta: int = int(round(norm * intensity * float(max_scaling)))
	target_delta = clampi(target_delta, int(bounds.get("enemy_level_delta_min", -3)), int(bounds.get("enemy_level_delta_max", 3)))

	# Smooth per-battle change: move current delta toward target by at most step.
	var step: int = int(bounds.get("per_battle_delta_step_max", 1))
	var cur_delta: int = int(st.get("current_level_delta", 0))
	if target_delta > cur_delta:
		cur_delta = min(cur_delta + step, target_delta)
	elif target_delta < cur_delta:
		cur_delta = max(cur_delta - step, target_delta)
	st["current_level_delta"] = cur_delta

	# AI tier from skill (still capped by mode).
	var tier := trainer_ai_tier
	if skill >= float(bounds.get("ai_upgrade_skill_threshold", 65.0)):
		tier = "advanced"
	elif skill <= float(bounds.get("ai_downgrade_skill_threshold", 35.0)):
		tier = "basic"
	tier = _cap_tier(tier, String(mode_cfg.get("ai_tier_cap", "advanced")))

	# Reward: give a small boost when the player is struggling (never a penalty for skill).
	var reward_mult: float = reward
	if skill < 40.0:
		reward_mult = min(float(bounds.get("reward_multiplier_max", 1.3)), reward * 1.15)

	if is_boss:
		var boss: Dictionary = _cfg.get("boss_policy", {})
		cur_delta = clampi(cur_delta, -int(boss.get("max_level_delta", 1)), int(boss.get("max_level_delta", 1)))
		if bool(boss.get("lock_ai_tier", true)):
			tier = trainer_ai_tier
		result["reason"] = "Boss: limited scaling (identity preserved)."
	else:
		result["reason"] = "Adaptive: skill %.0f/100 -> level delta %+d, AI '%s'." % [skill, cur_delta, tier]

	result["level_delta"] = cur_delta
	result["ai_tier"] = tier
	result["reward_multiplier"] = clampf(reward_mult, float(bounds.get("reward_multiplier_min", 0.75)), float(bounds.get("reward_multiplier_max", 1.3)))

	_record_adaptation(result)
	return result

func get_encounter_rate_multiplier() -> float:
	if not adaptation_enabled():
		return 1.0
	var bounds: Dictionary = _cfg.get("scaling_bounds", {})
	var skill := skill_score()
	# Struggling players meet slightly fewer wild battles; skilled players slightly more.
	var m: float = 1.0 + ((skill - 50.0) / 50.0) * 0.25 * clampf(float(SettingsManager.get_value("adaptive_intensity", 0.5)), 0.0, 1.0)
	return clampf(m, float(bounds.get("encounter_rate_min", 0.5)), float(bounds.get("encounter_rate_max", 1.5)))

func get_summary() -> Dictionary:
	var st := _state()
	return {
		"mode": _mode(),
		"adaptation_enabled": adaptation_enabled(),
		"skill_score": skill_score(),
		"battles_recorded": int(st.get("battles_recorded", 0)),
		"current_level_delta": int(st.get("current_level_delta", 0)),
		"recent": st.get("last_adaptations", []),
	}

func _record_adaptation(result: Dictionary) -> void:
	var st := _state()
	var hist: Array = st.get("last_adaptations", [])
	hist.push_front({"level_delta": result["level_delta"], "ai_tier": result["ai_tier"], "reason": result["reason"]})
	while hist.size() > 5:
		hist.pop_back()
	st["last_adaptations"] = hist

func _cap_tier(tier: String, cap: String) -> String:
	var order := {"basic": 0, "intermediate": 1, "advanced": 2}
	if order.get(tier, 0) > order.get(cap, 2):
		return cap
	return tier
