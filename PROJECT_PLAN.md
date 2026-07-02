# PROJECT_PLAN.md — Creature RPG 2D Engine

> A data-driven, offline, local creature-capture & turn-based-battle RPG built with
> **Godot 4 (2D, typed GDScript)**. Engine and content are fully separated: the game
> reads everything (creatures, moves, types, items, regions, trainers, quests…) from
> external JSON files validated at boot. All demo content is **100% original** — no
> Nintendo / Game Freak / The Pokémon Company assets, names, or data are used.

---

## 0. Status legend

- ✅ Done and verified (validator or test run)
- 🟩 Implemented (code complete, needs Godot runtime to fully verify)
- 🟨 Minimal version implemented, extension documented
- ⬜ Planned / future

---

## 1. Feature backlog (classified)

### A. Indispensable for the prototype
| Feature | Status |
|---|---|
| Godot project + folder structure | 🟩 |
| Data loading from external JSON | 🟩 |
| Data validators (dup ids, missing refs, circular evolutions, bad stats) | ✅ (Python + GDScript) |
| Type chart + affinity lookup | ✅ |
| Deterministic damage formula (seedable RNG) | ✅ (Python parity test) |
| Capture formula | ✅ |
| Experience / level-up curves | ✅ |
| Turn-based 1v1 battle engine (headless-testable) | 🟩 |
| Move effect system (data-driven `effects[]`) | 🟩 |
| 6+ original creatures, 12+ moves, 5+ items, abilities, types | ✅ |
| Overworld: 4-dir movement, collisions, walk anim | 🟩 |
| Grass random encounters | 🟩 |
| NPC / sign / object interaction, doors, scene changes | 🟩 |
| Starter choice (3), team of 6, simplified storage box | 🟩 |
| Inventory | 🟩 |
| Trainer battle | 🟩 |
| Short main quest | 🟩 |
| Two demo mini-regions + inter-region travel | 🟩 |
| Save / load (3 slots, autosave, atomic write, backup, versioned) | 🟩 |
| Title screen, new game, character creation | 🟩 |
| Heal center + shop | 🟩 |

### B. Necessary for first complete version
| Feature | Status |
|---|---|
| AI tiers: basic / intermediate / advanced | 🟩 |
| AI debug reasoning log (dev mode only) | 🟩 |
| AdaptiveDirector (smoothed skill score, bounded scaling) | 🟩 |
| Difficulty modes: Relaxed / Normal / Hard / Adaptive | 🟩 |
| Inter-region level sync / obedience cap | 🟩 |
| Quest system (data-driven, journal, conditional dialogue) | 🟩 |
| Encyclopedia (regional + global) | 🟨 |
| Full menu set (party, creature sheet, bag, box, map, quests, settings) | 🟩 |
| Settings: rebind, volumes, text speed, fullscreen, UI scale, accessibility | 🟨 |
| Developer menu (map warp, add creature, force save, show collisions…) | 🟩 |
| Save migration between format versions | 🟩 |
| Status conditions, stat stages, criticals, STAB, immunities | ✅ |

### C. Future improvements
Running / bike / surf / fly, caves, weather, day-night cycle, seasons,
environmental puzzles, breeding, forms/mega, online-free trading via file export,
localization to multiple languages, controller-first UX polish, tilemap editor tooling,
music per-zone with original tracks, particle FX, prestige beyond max level.

---

## 2. Architecture (modular, no circular deps)

```
Autoloads (global singletons)
  SettingsManager   – user options, persisted
  DataRegistry      – loads + validates all data/*.json, caches typed records
  GameState         – the live save-able world state (player, team, box, flags…)
  SaveManager       – atomic save/load, 3 slots, autosave, backup, migration
  AudioManager      – bus volumes, per-zone bgm/sfx (placeholder generators)
  SceneRouter       – scene stack, transitions, warp points, spawn markers
  AdaptiveDirector  – performance metrics, smoothed skill score, scaling policy

Core (pure logic, no scene deps — unit-testable)
  RNG               – seedable deterministic PRNG (splitmix64)
  TypeChart         – affinity multipliers
  DamageCalc        – deterministic damage formula
  CaptureCalc       – capture probability + shake checks
  ExperienceCalc    – curves, xp-to-level, level-from-xp
  BattleEngine      – turn resolution, effects, status, win/lose
  MoveEffects       – registry mapping effect "kind" -> handler
  CreatureFactory   – build a live creature instance from species data + level

AI            – ai_basic / ai_intermediate / ai_advanced choose an action + reason
Adaptive      – metrics collection + policy that BattleEngine/encounters consult
Data models   – lightweight typed wrappers over the JSON dicts

Overworld / Battle / UI / Quests / Save scripts drive scenes and call Core.
```

**Rule:** Core never imports Autoloads. Autoloads may call Core. Scenes call both.
This keeps the battle math testable headlessly and avoids cycles.

---

## 3. Implementation order (mirrors the brief's phases)

1. **Foundations** – project, structure, data load, validation, input, scene router, minimal save. 🟩
2. **Exploration** – player, collisions, maps, interaction, scene changes, encounters. 🟩
3. **Creatures & battle** – data models, team, moves, engine, xp, capture, evolution. 🟩
4. **Playable content** – 6 creatures, trainers, quest, heal center, shop, region 1. 🟩
5. **Adaptation** – metrics, smoothed score, trainer scaling, difficulty settings, debug log. 🟩
6. **Inter-region** – region 2, transport, global progression, level sync, return trip. 🟩
7. **Polish** – menus, box, encyclopedia, tests, docs, fixes. 🟨

---

## 4. Verification strategy

Godot is **not installed in the authoring environment**, so scene-level runtime
verification is done by the user in the Godot editor (see README "Run"). To make
verification *real and not merely claimed*, the pure, engine-independent logic is
duplicated as a **runnable Python reference** under `tools/validators/`:

- `validate_data.py` — validates every JSON file: duplicate ids, dangling references,
  unknown types/moves/abilities, circular evolutions, invalid stat ranges,
  encounters pointing at missing creatures. **Run before every launch.**
- `battle_reference.py` — a parity implementation of the damage / capture / xp math
  with the *same seeded RNG*, so the numbers the GDScript engine must produce are
  pinned by `tests/test_reference.py` and checked in CI-style `python3` runs.

In Godot, `tests/` contains a lightweight `TestRunner` (no external addon) covering the
same cases; run it with `godot --headless -s tests/run_tests.gd`.

---

## 5. Data extension model (the whole point)

Everything is a file. To add content you drop a JSON file (or an entry) into the right
`data/<kind>/` folder and it is picked up at boot after passing validation. No engine
edit is required. See `DATA_FORMAT.md` and `REGION_CREATION_GUIDE.md`.

---

## 6. Changelog

- 2026-07-02 — Initial scaffold: plan, structure, data set, core logic, validators,
  autoloads, overworld + battle scenes, save system, docs. Validators pass on the demo data.
- 2026-07-02 — Adversarial review pass (98-agent workflow, 8 dimensions × 3 verifiers per
  finding): 30 confirmed defects fixed, 0 false positives. Highlights: 3 `:=`-inference
  compile errors (overworld/title/pause_menu), dialog-dismiss soft-lock (same-frame input
  re-trigger), menu reopen-on-close, Struggle fallback for full PP exhaustion, replacement
  enemies no longer inherit the fainted creature's queued move, revive item now targets
  fainted members, keybinds re-applied on startup, loss-path autosave ordering + respawn
  position, save-slot backup visibility, F12 dev-menu keycode, defeated trainers no longer
  re-battleable, mouse support in battle choices, typewriter skip, and map data fixes.
  Parity (GDScript↔Python math) and map-completability dimensions reported zero defects.
- 2026-07-02 — User-content pack system + adaptive narrative layer:
  - `user_content/` (git-ignored) overlay: data packs under `canonical_data/` merged by id
    over `data/` (creatures, moves, abilities, items, evolutions, types, encounters,
    trainers, regions, maps, quests, dialogs, endings, balancing, localization), validated
    identically at boot; sprite/portrait/music overlays via `AssetResolver` (placeholder
    fallback). The engine never downloads content — users add only what they legally own.
  - Branching dialog scripts (`data/dialogs/`): condition-gated nodes, choices, actions
    (`set_var`, `adjust_relationship`, `give_item`, `start_quest`, `trigger_ending`…),
    `${player}` interpolation, `@key` localization, optional portraits.
  - Story variables + NPC relationship scores in GameState (saved), composable conditions
    (`all`/`any`/`not`, `var_equals`, `var_at_least`, `relationship_at_least`,
    `region_visited`) shared by quests, dialogs and endings.
  - Data-driven multiple endings (`data/endings/`), quest `on_complete_actions`,
    localization string tables with language fallback.
  - Demo: rival Corin (friendly/cold branch affects the ending), Professor Maple epilogue
    with two endings. Validators (GDScript + Python) extended to the new schemas.
