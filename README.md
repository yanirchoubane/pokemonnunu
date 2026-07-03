# Creature RPG 2D Engine

An original, **offline, single-player** creature-capture & turn-based-battle RPG built
with **Godot 4** (2D, typed GDScript). The engine is fully **data-driven**: creatures,
moves, types, items, abilities, regions, maps, trainers, and quests all live in external
JSON files that are validated at boot. You can add content without touching engine code.

> ⚠️ **No third-party IP.** All demo content is original. This project contains no
> Nintendo / Game Freak / The Pokémon Company assets, names, or data. See
> [`LICENSE_NOTES.md`](LICENSE_NOTES.md). Graphics and audio are generated procedurally.

---

## What works today (verified)

- ✅ Deterministic, seedable battle math (damage, capture, experience, type chart) —
  covered by **runnable tests** (`python3 tests/test_reference.py`, 30 assertions) and a
  Godot headless runner (`tests/run_tests.gd`).
- ✅ Data validation catches duplicate ids, dangling references, unknown types/moves,
  circular evolutions, bad stats, malformed maps (`python3 tools/validators/validate_data.py`).
- 🟩 Full playable loop: title → new game → starter → overworld → wild & trainer battles →
  capture → level up → evolution → quest completion → inter-region travel → return → save/load.
- ✅ **Nine connected regions** (Verdantia → Aquilon → Cindral → Solane → Umbra → Ferrock →
  Brume → Lumen → Zephyra): each with a gate town (heal + shop), wilds (encounters + scout +
  route trainers), and a Summit Hall (boss champion + crest badge), chained by flag-gated
  ports with return trips. The whole chain's walkability is **verified by a BFS simulation**
  over the map data.
- ✅ **2,097 original creatures** — every one of the 8 types has evolution lines in every
  region, plus hundreds of region natives (all generators are parameterized, so the dex
  can grow further with one constant). **56 moves, 15 abilities, 14 items** — all wired to
  the mechanics the engine actually implements (no dead data).
- ✅ **2,750 trainers** across all 9 regions: per region a Crossroads city with **8
  type-themed gyms** (72 leaders, one badge each), a **gym-circuit quest** that opens the
  League corridor where the **four Elites** must be beaten in sequence before the
  **Champion** (5-creature team), route classes, and **4 "Battle Court" training halls per
  region (36 total, ~2,600 optional trainers) built for grinding XP**. 149 maps, **35
  quests** (main crest arcs, the Hollow Order arc, collector and sparring side quests),
  8 endings. The whole world — entries, gyms, elite sequences, ports, return trips, and
  every Battle Court trainer — is verified reachable by
  `python3 tools/validators/check_chain.py`.
- ✅ **Branching story arc**: a recurring rival, **Corin**, meets you at every region's
  Crossroads; your answers move a relationship score that decides whether he stays a true
  rival or is drawn into the antagonist **Hollow Order** (named agents Vole/Cinder/Wisp, a
  Lieutenant, and the Archon). A defector reveals the Order's rot, and after the Archon
  boss you choose **mercy or justice** — the finale, and which of the 8 endings you get,
  follows your choices (see `STORY.md`).
- ✅ **A distinctive landmark in every region** (Verdant Glade, Frostwatch Lighthouse,
  Ashfall Caldera, Mirage Oasis, Duskbell Grove, the Old Foundry, the Sunken Chapel,
  Prism Cavern, Skyreach Shrine): each hand-written with lore signs, a keeper NPC, a
  first-visit reward, and a `Wonders of <region>` exploration quest. **158 maps, 44 quests,
  14 dialogs.**
- ✅ **Navigable atlas**: `python3 tools/world_summary.py` regenerates [`WORLD.md`](WORLD.md) from the live data (region-by-region table, progression spine, landmarks, story arc, endings) and flags any structural gaps.

Because Godot may not be installed where this was authored, **scene-level runtime testing
is done in the Godot editor** (below). The engine-independent core is verified now via the
Python twin so the numbers are pinned regardless.

---

## Prerequisites

- **Godot 4.2+** (standard build, GDScript — *not* the .NET/C# build required).
  Download from <https://godotengine.org/download>. No add-ons required.
- Optional, for the pre-flight validators/tests without Godot: **Python 3.8+**.

Runs on Windows, Linux, and macOS. No internet, account, or server needed.

## Run the game

1. Install Godot 4.2+ and launch it.
2. **Import** this project: in the Project Manager, click *Import*, select this folder's
   `project.godot`, then *Import & Edit*.
3. Press **F5** (Play). The main scene is `scenes/boot/boot.tscn`, which validates data
   and routes to the title screen.

From a terminal you can also run:

```bash
# from the project root
godot --path . run/main_scene           # or simply:
godot --path .
```

### Controls

| Action | Keys |
|---|---|
| Move | WASD / Arrow keys |
| Interact / confirm / advance text | Space / Enter |
| Cancel / back | X / Backspace |
| Pause menu (Team, Bag, Quests, Dex, Save, Settings) | Esc |
| Developer menu (only if Developer Mode is on in Settings) | F12 |

All keys are **rebindable** in Settings.

## Run the tests

```bash
# Pure-logic tests (no Godot needed) — pins the deterministic battle math:
python3 tests/test_reference.py

# Data pre-flight validation (run before launching):
python3 tools/validators/validate_data.py

# In-Godot headless tests (same cases, real GDScript classes):
godot --headless --script res://tests/run_tests.gd
```

---

## Folder structure

```
project.godot            Godot project + autoloads + input map
scripts/
  autoload/   Global singletons: SettingsManager, DataRegistry, GameState,
              SaveManager, AudioManager, AdaptiveDirector, SceneRouter
  core/       Pure, testable logic: RNG, TypeChart, StatMath, DamageCalc,
              CaptureCalc, ExperienceCalc, CreatureInstance/Factory, EvolutionSystem,
              placeholder graphics, boot
  battle/     BattleEngine, AbilityEffects, battle scene controller
  ai/         BattleAI (basic / intermediate / advanced tiers + debug reasoning)
  overworld/  Grid movement, collisions, interaction, encounters, warps
  ui/         Title, new game, load, settings, pause menu, dialog, shop, dev menu
scenes/       Thin .tscn wrappers that attach the scripts above
data/         ALL game content as JSON (creatures, moves, types, items, abilities,
              evolutions, encounters, trainers, regions, maps, quests, balancing)
tests/        Python reference tests + Godot headless runner
tools/
  validators/ validate_data.py (pre-flight) + battle_reference.py (math twin)
  importers/  CSV→JSON helper for bulk-authoring content
assets/       Placeholder folders (visuals/audio are generated at runtime)
```

## How the data works

Everything the game knows is loaded by `DataRegistry` at boot from `data/**`. Each file is
validated; if anything is wrong the boot screen lists the errors instead of launching.
See [`DATA_FORMAT.md`](DATA_FORMAT.md) for every schema.

### Add a creature
Add an entry to `data/creatures/creatures.json` (unique `id`, 1–2 known `types`, valid
`abilities`, a `learnset` of known moves, `base_stats` 1–255, a known `exp_curve`). Add it
to an encounter table or a trainer to make it appear. Run the validator.

### Add a move
Add to `data/moves/moves.json`: `id`, `type`, `category` (`physical|special|status`),
`power`, `accuracy`, `pp`, and an `effects[]` list. Effects are data-driven — see
[`BATTLE_SYSTEM.md`](BATTLE_SYSTEM.md) for the available `kind`s (`damage`, `apply_status`,
`stat_change`, `heal`). Most moves need **no** new code.

### Add a trainer
Add to `data/trainers/trainers.json`: `id`, `ai` tier, a `team[]` (each with `creature`,
`level`, `moves`), rewards, and dialogue. Place a `trainer` object on a map to encounter them.

### Add a region / map / connection
See [`REGION_CREATION_GUIDE.md`](REGION_CREATION_GUIDE.md). In short: drop a
`data/regions/region_<id>.json` manifest and one or more `data/regions/maps/<id>.json` grid
maps, and connect them with `warp`/`door` objects. `next_regions` links regions together.
For a full scaffold (three maps, encounter table, scout + boss trainers, quest, port
wiring), add a spec to `tools/generators/generate_regions.py` and re-run it — that is how
regions 3–9 were produced. The generator is idempotent (records upsert by id).

### Create a save
Play, open the pause menu (Esc) → **Save**, pick a slot. Autosave fires after each battle.
See [`SAVE_FORMAT.md`](SAVE_FORMAT.md).

### User content packs (`user_content/`)
The engine also loads **local, git-ignored** content packs from `user_content/` —
your own creatures, moves, regions, maps, trainers, quests, dialogs, endings,
sprites (`sprites/creatures/<id>.png`), portraits and music (`music/<zone>.ogg`) —
merged by id over the demo data and validated identically at boot. The engine never
downloads anything; only add material you legally may use, and never commit it.
See [`USER_CONTENT_GUIDE.md`](USER_CONTENT_GUIDE.md).

### Branching story
NPCs can run data-driven **dialog scripts** (`data/dialogs/`) with conditions,
choices and actions that set story variables, shift **relationships**, give items,
start quests, or trigger one of several data-defined **endings** (`data/endings/`).
Try it: talk to Corin in the demo town, and revisit Professor Maple after finishing
the Aquilon quest to conclude the story two different ways.

---

## Difficulty & adaptation

Four modes: **Relaxed / Normal / Hard / Adaptive**. In Adaptive mode the `AdaptiveDirector`
keeps a smoothed skill score (0–100) from your recent battles and *gently* scales enemy
level / AI tier / rewards / encounter rate within hard bounds. It never edits your
creatures, never mirrors your team exactly, and never punishes good play. Bosses keep a
fixed identity with only limited scaling. See [`ADAPTIVE_DIFFICULTY.md`](ADAPTIVE_DIFFICULTY.md).

## Current limitations

- Scene runtime not auto-verified here (no Godot in the authoring env). Logic **is** verified.
- Box storage is functional but minimal (auto-overflow from a full team; no drag UI yet).
- No breeding, weather, day/night, surf/fly/bike, or localization yet (architecture leaves
  room — see `PROJECT_PLAN.md` section 1.C).
- Placeholder visuals are geometric; audio is synthesized tones.

## Next priorities

1. Verify scenes in the Godot editor and fix any runtime wiring.
2. Full box management UI + move-replacement prompt on level-up.
3. More regions/quests, richer AI item usage, save-slot management screen.

See `PROJECT_PLAN.md` for the full roadmap and status.
