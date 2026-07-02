# SAVE_FORMAT.md

Saves are plain JSON written to Godot's `user://` directory (never the project folder), so
they are per-user and safe to delete. `SaveManager` (`scripts/autoload/save_manager.gd`)
handles everything.

## Location
`user://saves/` — resolves to, e.g.:
- Windows: `%APPDATA%\Godot\app_userdata\Creature RPG 2D Engine\saves\`
- Linux: `~/.local/share/godot/app_userdata/Creature RPG 2D Engine/saves/`
- macOS: `~/Library/Application Support/Godot/app_userdata/Creature RPG 2D Engine/saves/`

## Slots
- `slot_0` = **autosave** (fires after each battle).
- `slot_1..3` = manual save slots (pause menu → Save).
- Each slot has `slot_N.json` (current), `slot_N.bak` (previous), and transient `slot_N.tmp`.

## Robust write (atomic-ish)
1. Serialize to `slot_N.tmp`.
2. Re-read and re-parse the temp file to confirm it is valid JSON.
3. Rotate current → `slot_N.bak`, then rename temp → current.

This means an interrupted save cannot destroy a good previous save.

## Load & recovery
On load, the primary file is read and structurally validated. If it is missing or corrupted,
the `.bak` is tried automatically. Corrupt data yields a clear error, never a crash, and the
game **never executes** deserialized content — it only parses JSON into plain data.

## File shape
```jsonc
{
  "header": {
    "format_version": 2,
    "timestamp": "2026-07-02T14:31:07",
    "unix_time": 1782000667,
    "playtime_seconds": 3540,
    "player_name": "Nova",
    "region": "verdantia",
    "team_summary": [ {"species":"emberhound","level":18} ],
    "badges": 1
  },
  "state": {
    "rng_seed": 1374389535, "rng_state": 91237744,   // seed + PRNG state for reproducibility
    "player": { "name":"Nova","gender":"girl","money":2200,
                "position": {"map":"verdantia_route","x":6,"y":3,"facing":"down"},
                "respawn": {"map":"verdantia_center","spawn":"entrance"} },
    "team": [ /* CreatureInstance.to_dict(): species_id, level, exp, ivs, evs, nature,
                 ability, gender, current_hp, status, moves[{id,pp,max_pp}] */ ],
    "box": [ /* same shape as team */ ],
    "inventory": { "capture_orb": 4, "potion": 2 },
    "flags": { "got_starter": true, "beat_route_scout": true },
    "counters": { "creatures_caught": 3 },
    "badges": [ "verdant_badge" ],
    "quests": { "main_verdant_trial": { "state":"active", "objectives": {"obj_starter":true} } },
    "region_progress": { "verdantia": {"unlocked":true,"visited":true,"completed":false} },
    "current_region": "verdantia",
    "playtime_seconds": 3540,
    "adaptive_state": { "skill_score": 57.5, "battles_recorded": 9, "current_level_delta": 1 }
  }
}
```
Only serializable data is stored — creatures save their mutable state and reattach their
(immutable) species record from `DataRegistry` on load. The saved `rng_state` keeps wild
encounters and battles reproducible across a save/load.

## Versioning & migration
`header.format_version` is the current save schema (2). `SaveManager._migrate` upgrades older
saves forward step by step (e.g. v1→v2 adds `region_progress`/`adaptive_state` defaults).
Add a new `case` when you bump `FORMAT_VERSION`.

## What is saved (per the brief)
format version, timestamp, playtime, position, current region, team, box, inventory, quests,
settings (separately in `user://settings.cfg`), adaptive state, region progression, and the
RNG seed/state.
