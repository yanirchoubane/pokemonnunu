# DATA_FORMAT.md — Content schemas

Every file lives under `data/` and is loaded + validated by `DataRegistry` at boot. Run
`python3 tools/validators/validate_data.py` after any edit. All ids are lowercase
`snake_case` and must be **stable** (they appear in saves).

---

## types — `data/types/types.json`
```jsonc
{
  "types": [ { "id": "fire", "display_name": "Ember", "color": "#e6642e" } ],
  "chart": { "fire": { "grass": 2.0, "water": 0.5 } }  // attacker -> defender -> multiplier
}
```
Missing pairs default to `1.0`. `0.0` = immunity, `0.5` = resisted, `2.0` = super-effective.

## moves — `data/moves/moves.json`
```jsonc
{
  "id": "ember_burst", "display_name": "Ember Burst",
  "type": "fire", "category": "special",       // physical | special | status
  "power": 40, "accuracy": 100, "priority": 0, "pp": 25,
  "description": "...",
  "effects": [
    { "kind": "damage" },
    { "kind": "apply_status", "status": "burn", "chance": 0.1, "target": "enemy" }
  ]
}
```
Effect `kind`s: `damage`, `apply_status` (`status`, `chance`, `target`), `stat_change`
(`stat`, `stages`, `chance`, `target`), `heal` (`fraction`). `target` is `enemy` or `self`.

## abilities — `data/abilities/abilities.json`
```jsonc
{ "id": "blaze_heart", "display_name": "Blaze Heart", "description": "...",
  "hooks": ["modify_outgoing_damage"],
  "params": { "type": "fire", "hp_threshold": 0.34, "multiplier": 1.5 } }
```
Supported hooks: `modify_outgoing_damage`, `modify_incoming_damage`, `prevent_stat_drop`,
`on_contact_hit`. Params are read by `AbilityEffects`; new simple abilities need no code.

## creatures — `data/creatures/creatures.json`
```jsonc
{
  "id": "emberpup", "display_name": "Emberpup", "description": "...",
  "generation": "demo_g1", "origin_region": "verdantia",
  "types": ["fire"],                             // 1 or 2, must exist
  "base_stats": { "hp":45,"attack":52,"defense":43,"sp_attack":60,"sp_defense":50,"speed":65 }, // 1..255
  "ev_yield": { "sp_attack": 1 },
  "exp_curve": "medium_fast",                    // fast|medium_fast|medium_slow|slow
  "gender_ratio": 0.5,                            // fraction male, or -1 for genderless
  "abilities": ["blaze_heart"],
  "capture_rate": 45, "rarity": "starter",
  "breeding_groups": ["field"],                   // reserved for future breeding
  "learnset": [ { "level": 1, "move": "ember_burst" } ],
  "evolves_to": ["emberhound"],                   // must exist; no cycles
  "forms": []
}
```

## evolutions — `data/evolutions/evolutions.json`
```jsonc
{ "id":"evo_emberpup", "from":"emberpup", "to":"emberhound",
  "condition": { "kind":"level_up", "level":16 } }   // level_up | use_item(item) | trade
```

## items — `data/items/items.json`
```jsonc
{ "id":"potion","display_name":"Salve","category":"healing","price":300,"sell":150,
  "description":"...", "usable_in_battle":true, "consumable":true,
  "use": { "kind":"heal_hp", "amount":20 } }
```
`use.kind`: `capture` (`ball_rate`), `heal_hp` (`amount`), `cure_status` (`status`),
`revive` (`fraction`), `evolution_stone`.

## encounters — `data/encounters/encounters.json`
```jsonc
{ "id":"verdantia_encounters", "region":"verdantia",
  "entries":[ { "creature":"zapmouse","weight":35,"level_min":2,"level_max":5,"rarity":"common" } ] }
```
`weight` is relative; the engine normalizes. Referenced by a region's `encounter_table`
and by map `encounter_zone` objects.

## trainers — `data/trainers/trainers.json`
```jsonc
{ "id":"gym_verdantia","display_name":"Warden Sable","ai":"advanced",
  "boss":true,"boss_scaling":"limited","reward_money":1000,"reward_badge":"verdant_badge",
  "dialogue_intro":"...","dialogue_defeat":"...","dialogue_victory":"...",
  "team":[ { "creature":"bloomcat","level":13,"moves":["leaf_cut","vine_wrap","guard_up"] } ] }
```
`ai`: `basic|intermediate|advanced`. `boss:true` → limited adaptive scaling, fixed AI.
The map object's `flag` should be `beat_<trainer_id>` (the battle sets that flag on win).

## regions — `data/regions/region_<id>.json`
See `REGION_CREATION_GUIDE.md`.

## maps — `data/regions/maps/<id>.json`
See `REGION_CREATION_GUIDE.md`.

## quests — `data/quests/quests.json`
```jsonc
{ "id":"main_verdant_trial","display_name":"The Verdant Trial","category":"main",
  "auto_start":true,                              // or "start_condition": {kind:flag,flag:...}
  "description":"...",
  "objectives":[ { "id":"obj_badge","text":"...","condition": {"kind":"flag","flag":"beat_gym_verdantia"} } ],
  "rewards":[ {"kind":"money","amount":500}, {"kind":"item","item":"great_orb","quantity":3},
              {"kind":"unlock_region","region":"aquilon"} ],
  "on_complete_flag":"quest_verdant_done" }
```
Objective `condition.kind`: `flag` (`flag`) or `counter` (`counter`, `at_least`). Counters
tracked by the engine include `creatures_caught`. Flags include `got_starter`,
`visited_<region>`, `returned_to_verdantia`, and every `beat_<trainer_id>`.

## balancing — `data/balancing/balancing.json` and `adaptive.json`
Central tunables (no magic numbers in engine code). `balancing.json` holds battle/capture/
experience/economy/party constants; `adaptive.json` holds the AdaptiveDirector policy
(see `ADAPTIVE_DIFFICULTY.md`).
