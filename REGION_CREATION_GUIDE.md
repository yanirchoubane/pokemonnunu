# REGION_CREATION_GUIDE.md

Add a whole region without touching engine code. Everything is JSON under `data/`, validated
at boot. After editing, run `python3 tools/validators/validate_data.py`.

---

## 1. Region manifest — `data/regions/region_<id>.json`
```json
{
  "id": "region_demo_01",
  "display_name": "Verdantia",
  "order": 1,
  "starting_map": "verdantia_town",
  "recommended_level_min": 1,
  "recommended_level_max": 50,
  "badge_count": 8,
  "league_id": "verdantia_league",
  "next_regions": ["region_demo_02"],
  "maps": ["verdantia_town", "verdantia_route"],
  "regional_rules": {
    "level_scaling": "soft",
    "encounter_table": "verdantia_encounters",
    "allow_previous_team": true,
    "obedience_cap_level": 20
  }
}
```
- `order` sets the recommended sequence; `next_regions` links onward (alternate routes are
  allowed — list several). A region is playable once unlocked (a quest reward or dev tool).
- `regional_rules.obedience_cap_level` softly caps the **effective** level of your carried
  team so an old powerhouse can't steamroll a new region — real levels are never changed.

## 2. Maps — `data/regions/maps/<id>.json`
Maps are a compact grid: a `legend` mapping single characters to tile types, `rows` of those
characters, and an `objects` list. All rows must be the same width (the validator enforces
this).
```json
{
  "id": "verdantia_town", "region": "verdantia", "display_name": "Verdantia Town",
  "tile_size": 32, "bgm": "town",
  "legend": { ".":"ground", "P":"path", "T":"tree", "~":"tall_grass", "W":"water", "D":"door" },
  "rows": [ "TTTTTTT", "T.....T", "T..D..T", "TTTTTTT" ],
  "objects": [ ... ]
}
```
**Walkable** tile types: `ground, path, floor, sand, stone, tall_grass, heal_pad, door`.
Everything else blocks. Colors are auto-assigned by `PlaceholderGfx` (add new tile types
there if you want new colors).

### Object types
| type | fields | effect |
|---|---|---|
| `spawn` | `id, x, y` | named entry point (`default` is the fallback) |
| `warp` / `door` | `x, y, to_map, to_spawn`, optional `requires_flag`, `locked_text` | move to another map/region |
| `npc` | `x, y, dialogue[]`, optional `starter_choice[]`, `flag` | talk; lab NPC gives a starter |
| `sign` | `x, y, text` | readable text |
| `item` | `x, y, item, quantity, flag` | one-time pickup |
| `shop` | `x, y, stock[]` | opens the shop |
| `heal` | `x, y, sets_respawn` | full heal; optionally sets your respawn point |
| `trainer` | `x, y, trainer_id, facing, sight, flag` | line-of-sight battle |
| `encounter_zone` | `table` | enables wild encounters on tall grass for this map |

## 3. Encounter table — `data/encounters/encounters.json`
Add a `tables[]` entry with `id`, `region`, and weighted `entries` (see `DATA_FORMAT.md`).
Reference it from the region's `regional_rules.encounter_table` and/or a map's
`encounter_zone` object.

## 4. Trainer — `data/trainers/trainers.json`
Add the trainer (id, `ai` tier, `team[]`, rewards, dialogue). Place a `trainer` object on a
map with `flag: "beat_<trainer_id>"`. Set `boss:true` for gym/league leaders.

## 5. Quest — `data/quests/quests.json`
Add a quest with objectives keyed to `flag`/`counter` conditions and rewards (money, items,
`unlock_region`). Set `auto_start` or a `start_condition`. Objectives complete automatically
as flags/counters change.

## 6. Connect two regions
1. In region A's manifest, add region B to `next_regions`.
2. Put a `warp` object on one of A's maps pointing to B's arrival map/spawn (optionally
   gated by `requires_flag`, e.g. a badge flag).
3. Put a return `warp` on B's arrival map back to A.
4. Unlock B via a quest reward (`unlock_region`) or the badge flag.

The demo does exactly this: beating `gym_verdantia` sets `beat_gym_verdantia`, which unlocks
the port warp in `verdantia_forest` to `aquilon_shore`, and `aquilon_shore` has a return
warp home. Your carried team persists, subject to the region's obedience cap.

## Bulk authoring
For large content sets, use `tools/importers/csv_to_json.py` to convert spreadsheets of
creatures/moves into the JSON shapes above, then validate.
