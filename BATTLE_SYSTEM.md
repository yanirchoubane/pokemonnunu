# BATTLE_SYSTEM.md

The battle engine (`scripts/battle/battle_engine.gd`) is **headless and deterministic**:
given the same seed it produces the same outcome, and it runs without any scene so it can
be unit-tested. The scene controller (`scripts/battle/battle_scene.gd`) only renders the
event list the engine returns and collects player input.

## Determinism
All randomness goes through a single seedable `RNG` (`scripts/core/rng.gd`, xorshift32).
The battle seed is derived from the save's RNG, so battles are reproducible and the Python
reference (`tools/validators/battle_reference.py`) reproduces the exact numbers
(pinned by `tests/test_reference.py`).

## Damage formula (`scripts/core/damage_calc.gd`)
```
level_factor = (2 * level) / 5 + 2
base         = floor( level_factor * power * atk / def / 50 ) + 2
damage       = floor( base * crit * STAB * type_eff * random * ability_mult )
```
- `atk/def` use Attack/Defense for **physical** moves, Sp.Atk/Sp.Def for **special**;
  stat stages and Burn (halves physical Attack) are applied first.
- `crit` = 1.5 with 6.25% chance. `STAB` = 1.5 if the move type matches the user's type.
- `type_eff` from the type chart (0 / 0.25 / 0.5 / 1 / 2 / 4). If 0, damage is 0.
- `random` ∈ [0.85, 1.0]. `ability_mult` from attacker/defender abilities.
- **RNG draw order (fixed):** critical check, then random factor. Accuracy is a separate
  draw handled before effects.

All constants live in `data/balancing/balancing.json` → `battle`.

## Turn resolution
1. Player and enemy each submit an action: `move`, `switch`, `item`, `capture`, or `flee`.
2. Ordering: non-move actions (switch/item) resolve first (player before enemy); then moves
   sort by `priority`, then effective Speed (Paralysis halves Speed), ties broken randomly.
3. A queued move belongs to the creature that chose it: if that creature is KO'd before
   acting, its action is cancelled — a replacement sent out mid-turn gets a free switch-in
   and does **not** inherit the fainted creature's move.
4. A move runs its `effects[]` in order. `damage` computes once; secondary effects
   (`apply_status`, `stat_change`) roll their own `chance`.
5. End of turn: Burn/Poison tick damage (these run even on turns where the player must
   choose a replacement — only the whole battle ending skips them).
6. On an enemy faint: EXP is awarded and applied (level-ups learn moves and queue evolution
   checks); the trainer sends the next creature or the battle ends. On a player faint: you
   choose a replacement, or lose if none remain.

## Struggle (PP exhaustion fallback)
When a creature has 0 PP on every move, it automatically uses **Struggle**: a typeless
35-power physical move that ignores PP and recoils for 25% of the damage dealt
(`BattleEngine.STRUGGLE`). Both the player menu and the AI route through it, so full PP
exhaustion can never soft-lock a battle — it always converges to a KO.

## Move effects — data-driven
A move lists effects instead of needing bespoke code:
```json
{ "id":"ember_burst","type":"fire","category":"special","power":40,"accuracy":100,
  "effects":[ {"kind":"damage"}, {"kind":"apply_status","status":"burn","chance":0.1,"target":"enemy"} ] }
```
Handled kinds: `damage`, `apply_status`, `stat_change`, `heal`, `recoil` (`fraction` of the
damage just dealt bounces back on the user — used by Struggle). Add a new kind by extending
`BattleEngine._apply_effect` (one `match` arm) — existing moves are unaffected.

## Statuses & stages
- Statuses: `burn` (½ physical Atk + end-turn chip), `poison` (bigger end-turn chip),
  `paralyze` (½ Speed, 25% skip). One major status at a time.
- Stat stages clamp to [-6, +6] with the standard `2/(2±stage)` multiplier.

## Capture (`scripts/core/capture_calc.gd`)
```
a = (3*maxHP - 2*HP) * captureRate * ballRate * statusBonus / (3*maxHP)   (capped at 255)
probability = a / 255
```
The 4 shake checks are computed so that P(all 4 succeed) == `probability`, i.e. the shake
animation is honest about the real odds.

## Experience (`scripts/core/experience_calc.gd`)
Four named curves. Award scales with the defeated creature's level and a trainer bonus, then
by the adaptive/reward multiplier. Level cap 100 with prestige available beyond (see
`ADAPTIVE_DIFFICULTY.md` and balancing `experience`).

## Event list (returned by `resolve_turn`)
`move_used, damage, miss, message, status, status_damage, stat_stage, faint, exp_gain,
level_up, learn_move, learn_move_full, capture_attempt, flee, switch, enemy_switch,
request_switch, check_evolution, win, lose`. The UI maps each to a line/HP update.

## AI
`scripts/ai/battle_ai.gd` picks the enemy action. It reads only visible board state and
never the player's current-turn choice, and it never consumes the battle RNG (estimates use
average factors). Tiers: **basic** (random valid move), **intermediate** (best estimated
damage + defensive switch), **advanced** (KO-awareness, status/setup value, pivots). With
Developer Mode on, the battle screen shows the AI's reasoning, confidence, and alternatives.
