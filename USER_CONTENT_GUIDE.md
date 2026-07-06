# USER_CONTENT_GUIDE.md — Adding your own content packs

The engine is fully data-driven: everything it knows about creatures, moves, types,
items, regions, maps, trainers, quests, dialogs and endings comes from JSON files.
The repository ships only **original demo content**. You can layer your own content
on top through the `user_content/` folder — without touching a single engine file.

## ⚠️ Legal ground rules (read first)

- `user_content/` is **local and git-ignored**. Nothing in it is ever committed.
- The engine **never downloads anything**. You place files there yourself.
- Only add material you have the right to use: your own creations, freely licensed
  assets, or content you are otherwise legally permitted to use privately.
- Do **not** extract data or assets from commercial games or ROMs, and do not
  redistribute a pack containing third-party intellectual property. If you build a
  pack from protected material for private use, that stays on your machine —
  distributing it is your responsibility and generally not lawful.

## Where packs live

Two roots are scanned (later wins on conflicts):

1. `res://user_content/` — the `user_content/` folder next to `project.godot`
   (most convenient while running from the Godot editor).
2. `user://user_content/` — the Godot user directory (survives exports;
   on Linux: `~/.local/share/godot/app_userdata/Creature RPG 2D Engine/`).

```text
user_content/
├── sprites/
│   ├── creatures/<species_id>.png     # battle & menu art (any size; ~96px is ideal)
│   └── portraits/<npc_id>.png         # dialog portraits (~96px)
├── music/<zone_or_track_id>.ogg       # zone music, Ogg Vorbis, loops automatically
├── maps/                              # reserved for future graphical map packs
├── sounds/                            # reserved (SFX overlay planned)
├── canonical_data/                    # data packs (see below)
└── localization/<lang>.json           # extra languages / string overrides
```

## Data packs (`canonical_data/`)

A **pack** is either loose category folders directly under `canonical_data/`, or one
subfolder per pack. Each pack mirrors the layout of the repo's `data/` folder:

```text
user_content/canonical_data/my_pack/
├── pack.json                # optional: {"id": "my_pack", "display_name": "My Pack"}
├── creatures/anything.json  # {"creatures": [ {...}, ... ]}
├── moves/anything.json      # {"moves": [...]}
├── abilities/…  items/…  evolutions/…  encounters/…  trainers/…
├── quests/…  dialogs/…  endings/…
├── types/types.json         # merged into the type list + chart
├── regions/my_region.json   # one region manifest per file
├── regions/maps/…           # map grids (or maps/ at the pack root)
├── balancing/balancing.json # per-section overrides
└── localization/fr.json     # pack-local strings
```

Records are merged **by `id`**: a record whose id already exists replaces the base
version; a new id extends the game. Multiple JSON files per category are allowed —
split a big region into as many files as you like. Everything is validated at boot
exactly like the base data (unknown types, missing references, circular evolutions,
broken dialog jumps and invalid stats are all reported with file-level messages).

The schemas are documented in `DATA_FORMAT.md`. The quickest way to author a record
is to copy a demo record from `data/` and edit it.

### Example: adding one creature (fully original)

`user_content/canonical_data/my_pack/creatures/frostfox.json`

```json
{
  "creatures": [
    {
      "id": "frostfox",
      "display_name": "Frostfox",
      "description": "A sly fox that leaves frost footprints.",
      "generation": "my_pack_g1",
      "origin_region": "aquilon",
      "types": ["water"],
      "base_stats": { "hp": 52, "attack": 58, "defense": 50,
                      "sp_attack": 66, "sp_defense": 56, "speed": 74 },
      "ev_yield": { "speed": 1 },
      "exp_curve": "medium_fast",
      "gender_ratio": 0.5,
      "abilities": ["swift_foot"],
      "capture_rate": 90,
      "rarity": "uncommon",
      "breeding_groups": ["field"],
      "learnset": [
        { "level": 1, "move": "tackle" },
        { "level": 7, "move": "aqua_dart" }
      ],
      "evolves_to": [],
      "forms": []
    }
  ]
}
```

Drop a `user_content/sprites/creatures/frostfox.png` next to it and the engine uses
your art instead of the generated placeholder. Add the id to an encounter table (or
a new one referenced by a map's `encounter_zone`) and it appears in the wild.

### Example: adding a whole region

A region needs: a manifest (`regions/<id>.json`), maps (`regions/maps/*.json`), an
encounter table, trainers, and at least one warp connecting it to an existing map.
Follow `REGION_CREATION_GUIDE.md` — the demo Aquilon region is a complete, minimal
reference. Regions are ordered by their manifest's `order` field and unlocked
through quest rewards (`unlock_region`) or `next_regions` progression. There is no
limit on the number of regions in a save.

### Branching story content

- **Dialog scripts** (`dialogs/`): node graphs with conditions, choices, and actions
  (`set_var`, `adjust_relationship`, `give_item`, `start_quest`, `trigger_ending`…).
  Attach one to any map NPC via `"dialog_id"`.
- **Quests** (`quests/`): objectives driven by flags/counters, plus
  `on_complete_actions` for narrative side effects.
- **Endings** (`endings/`): ordered list; the first whose composable condition
  passes is shown when a `trigger_ending` action fires.
- **Conditions** compose with `all` / `any` / `not` over `flag`, `counter`,
  `var_equals`, `var_at_least`, `relationship_at_least`, `region_visited`.

### Localization

`user_content/localization/<lang>.json`:

```json
{ "language": "fr", "strings": { "ui.new_game": "Nouvelle partie" } }
```

Any dialog line or UI string starting with `@` is looked up by key (current
language → English → raw key). Set the language with the `language` setting.

## Checking a pack

Run the engine — boot reports every validation error with the offending id — or run
`python3 tools/validators/validate_data.py` for the base data. Pack JSON is parsed
with the same schemas, so a record that validates in `data/` validates in a pack.
