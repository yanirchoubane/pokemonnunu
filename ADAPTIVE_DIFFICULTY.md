# ADAPTIVE_DIFFICULTY.md

The `AdaptiveDirector` autoload (`scripts/autoload/adaptive_director.gd`) tunes challenge
without invalidating the player's progress. Policy lives in `data/balancing/adaptive.json`.

## Difficulty modes
Chosen in Settings (persisted): **Relaxed / Normal / Hard / Adaptive**.
- Relaxed: enemies −2 levels, AI capped at *basic*, richer rewards, no adaptation.
- Normal: baseline, no adaptation.
- Hard: enemies +2 levels, leaner rewards, no adaptation.
- Adaptive: baseline that *gently* scales to a smoothed skill score (below).

## Skill score (0–100, smoothed)
After **each battle** (not each action) the director nudges the score:
```
new = clamp(current + smoothing * delta, 0, 100)
```
`delta` rewards wins / flawless wins / using type advantage / winning as the level underdog,
and lightly penalizes heavy item reliance and losses. `smoothing = 0.25`, so it moves
slowly and never lurches. No adaptation happens until several battles are recorded
(`min_battles_before_adapt`).

## What adapts, and the hard bounds
From the skill score, and scaled by the user's **intensity** (0–1) and **max scaling**
(0–6) settings, the director may adjust:
- **Enemy level delta** — bounded to `[-3, +3]`, and it moves at most **1 level per battle**
  (no sudden spikes).
- **AI tier** — upgrades toward *advanced* at high skill, eases toward *basic* when
  struggling (still capped by the mode).
- **Rewards / EXP** — small boost when the player is struggling (never a penalty for skill).
- **Encounter rate** — small ± within `[0.5, 1.5]`.

## Guarantees (enforced in code)
- Never modifies the player's own creatures' stats/levels.
- Never makes an enemy exactly equal to the player (deltas are small and bounded).
- Preserves weak/medium/strong zones; uses min/max clamps everywhere.
- Prevents abrupt swings (per-battle step limit + smoothing).
- Adaptation state is stored **in the save** (`GameState.adaptive_state`).
- Fully disable-able (`adaptive_enabled`), and non-adaptive modes exist.
- **Never punishes good play** — good play raises rewards/challenge, not artificial walls.
- **Bosses** keep a fixed identity: `boss_policy` limits their level delta to ±1 and locks
  their scripted AI tier.

## Player-facing settings
`difficulty`, `adaptive_enabled`, `adaptive_intensity`, `adaptive_max_scaling`,
`show_adaptation_summary` (prints a one-line skill/delta summary after battles).

## Inspecting it
Enable Developer Mode → the battle screen shows AI reasoning; the dev menu (F12) prints the
live adaptive summary (mode, skill, current level delta, battles recorded).

## Cross-region leveling
Real levels are always preserved. Regions may apply a temporary **obedience/level cap**
(`regional_rules.obedience_cap_level`) so an over-leveled team can't trivialize a new region,
while your creatures keep their true level, moves, and collection progress. Level cap is 100
with prestige beyond; end-game bosses are built around strategy, not inflated stats. See the
`experience` block in `data/balancing/balancing.json` and `REGION_CREATION_GUIDE.md`.
