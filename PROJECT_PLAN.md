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
- 2026-07-03 — Completeness pass:
  - **Storage UI** in the pause menu: deposit team members to the box / withdraw to the
    team (never below 1 team member, never above the max team size).
  - **Interactive move learning**: when a level-up offers a 5th move, the player picks a
    move to forget or skips (engine emits `learn_move_full` with the team index; the
    battle scene resolves it in dialog).
  - **Language selector** in Settings (built from the loaded string tables) + full French
    string table (`data/localization/fr.json`); title, pause-menu and battle command
    labels now resolve through `tr_key`.
  - **Aquilon league arc**: Champion Isolde (boss, advanced AI, `aquilon_crest` badge) in
    the new Summit Hall map, gated behind defeating Tactician Wrenn
    (`requires_flag` door); quest "The Summit Challenge"; third ending
    "Champion of the North" (takes precedence over the Corin-relationship endings).
  - **2 new original creatures**: Mistcalf → Mistelk (water/wind, level-20 evolution),
    added to the Aquilon encounter table (Mistelk as a rare high-level spawn).
  - Validators pass: 12 creatures, 16 moves, 5 trainers, 9 maps, 4 quests, 3 endings.
- 2026-07-03 — **Nine-region campaign** (all original content):
  - New reusable generator `tools/generators/generate_regions.py` scaffolds complete
    regions from specs (manifest, gate town with heal/shop, wilds with encounters + scout,
    Summit Hall with boss champion + crest badge, encounter table, two trainers, main
    quest, port wiring). Idempotent — records upsert by id; documented for user regions.
  - Seven new regions chained after Aquilon: Cindral (volcanic), Solane (dunes),
    Umbra (twilight woods), Ferrock (iron hills), Brume (fens), Lumen (crystal vale),
    Zephyra (sky steppes) — level bands 14-24 up to 50-60, obedience caps scaled,
    ports gated by each region's crest, full return trips.
  - 14 new original native species (2 per region) wired into encounters and trainer teams.
  - Grand ending "Legend of the Nine Crests" (all nine champion flags), first in priority.
  - Whole-chain BFS reachability simulation passes (gate→wilds→hall→next region and back);
    validators green: 26 creatures, 19 trainers, 9 regions, 30 maps, 11 quests, 4 endings.
- 2026-07-03 — **Content expansion** (`tools/generators/generate_expansion.py`, all original):
  - +15 moves (every type now has an early/mid/late kit incl. strong 85-95 power finishers).
  - +37 species → **63 total**: 2-3 stage evolution lines per region (early-route bird and
    rodent archetypes, region singles, a 3-stage fire line, a 3-stage wind pseudo line, and
    the apex rarity Aetherion — ultra-rare wild spawn), 14 new evolution rules → 18 total.
  - +29 trainers → **48 total**: 3 route trainers per generated region (Rambler / Angler /
    Miner classes), 4 hand-placed trainers in Verdantia/Aquilon, and an original antagonist
    arc — the **Hollow Order**: agents in Cindral/Ferrock/Lumen wilds and the Archon boss
    (team of 54-57) in the Zephyra wilds.
  - New story quest "Shadows of the Hollow Order" (4 objectives across regions) and a fifth
    ending "The Hollow, Undone" (priority between Nine Crests and Champion).
  - Encounter tables now include all new stage-1 natives and singles; whole-chain BFS
    reachability still passes with the new trainer obstacles; validators green:
    63 creatures, 31 moves, 48 trainers, 12 quests, 5 endings; 30/30 math tests.
- 2026-07-03 — **Full league structure** (`tools/generators/generate_league.py`, original):
  - Every region now has a **Crossroads** city map with **eight type-themed gyms** (one per
    elemental type — all types represented in every region), each led by a boss gym leader
    with its own badge (72 gym leaders / 72 badges).
  - A **gym-circuit quest** per region: all 8 badges set `league_open_<region>`, which
    unlocks the **League corridor** — four Elite trainers on 1-tile chokepoints that must
    be beaten in sequence, then the region **Champion** (5-creature team, region crest).
    New champions for Verdantia (Sovereign Laurel) and Aquilon (Marshal Eirwen); Isolde
    remains Aquilon's summit story boss gating the inter-region ferry.
  - Dex generator with **guaranteed type coverage**: one evolution line per type per
    region (+ dual-type flavor lines; `EXTRA_LINES` scales the dex further). Region-scaled
    stats, unique procedural names, learnsets from type move pools, evolutions wired.
  - Totals: **297 creatures, 158 trainers (81 bosses), 113 maps, 21 quests, 81 badges**.
  - New permanent validator `tools/validators/check_chain.py`: static map integrity plus a
    progression walk of all nine regions (entries → gyms → elite sequence → champion →
    ports → returns). Passes; data validators green; 30/30 math tests.
- 2026-07-03 — **Bulk scale-up** (`tools/generators/generate_bulk.py`, all original):
  - **+540 species → 837 total**: 60 per region across all 8 types (about a third in
    2-stage evolution lines), unique procedurally-generated names, region-scaled stats,
    all added to the wild encounter tables so grass is far more varied (and XP-rich).
  - **+648 trainers → 806 total**: **3 "Battle Court" training halls per region (27 maps,
    24 trainers each)** — optional grind battles at the region's level band, on isolated
    non-blocking tiles, wired into each Crossroads via new doors. Purpose-built so players
    can farm experience anywhere in the world.
  - Three tunable constants (SPECIES_PER_REGION, COURTS_PER_REGION, TRAINERS_PER_COURT)
    scale the world up or down in one place.
  - `check_chain.py` extended to verify every Battle Court (door round-trip + all trainers
    reachable). All checks pass: 837 creatures, 806 trainers, 140 maps; 30/30 math tests.
- 2026-07-03 — **More trainers + branching story**:
  - Battle Courts raised to 48 trainers each → **1,454 trainers total**. `generate_bulk.py`
    made fully idempotent: deterministic region-prefixed species ids + self-pruning of its
    own previous output, so knob changes re-generate cleanly (species stayed at 837, no
    orphans).
  - DataRegistry (+ Python validator) now merge **all** `data/dialogs/*.json`, so story
    content can live in its own file. New `data/dialogs/story_arc.json`.
  - **Branching narrative** (`STORY.md`): recurring rival Corin at every Crossroads with a
    relationship-driven fork (stays true / falls to the Order in Umbra); a Hollow Order
    defector (Sable) who starts the arc and sets your stance; the Archon finale with a
    mercy/justice choice. Quest `main_hollow_order` now completes on the finale decision
    (`hollow_resolved`), not the raw battle. Three new endings (Rivals to the End, The Hand
    You Didn't Raise, Ledgers to Ash) → **8 endings**, priority-ordered.
  - Corin NPCs placed on all 9 Crossroads; defector in Cindral Gate; finale NPC in the
    Zephyra wilds. check_chain + validators + 30/30 math tests all pass.
- 2026-07-03 — **Breadth + scale-up** (`generate_extras.py`, bulk knobs raised):
  - New `generate_extras.py` adds only engine-supported (functional) content:
    **+7 items** (Master/Dusk orbs, Hyper/Max potions, status salves, Max Revive — added
    to shop stock and quest rewards so they enter play), **+8 abilities** (type souls,
    Iron Wall / Spectral Veil damage cuts, stat-drop guards — now carried by generated
    species), **+25 moves** (per-type finishers, priority hits, buffs/debuffs, heals,
    recoil — now in the species learn pools), and **+14 side quests** (a 5-tier
    creatures-caught collector chain + a per-region Battle Court sparring quest).
  - Bulk knobs raised: SPECIES_PER_REGION 60→100, TRAINERS_PER_COURT 48→60 (court maps
    auto-size to fit). Totals: **1,197 creatures, 1,778 trainers, 56 moves, 15 abilities,
    14 items, 35 quests**. Idempotent; validators + check_chain + 30/30 tests all pass.
- 2026-07-03 — **Scale-up to 2,000+**: bulk knobs raised again (SPECIES_PER_REGION →200,
  COURTS_PER_REGION →4, TRAINERS_PER_COURT →72). Totals now **2,097 creatures, 2,750
  trainers, 149 maps (36 Battle Courts)**. Generation stays ~1 s and fully idempotent
  (deterministic ids); data validators, check_chain (world walk + all 36 courts), and
  30/30 math tests all pass.
- 2026-07-03 — **Story & places focus**:
  - New `generate_places.py`: one hand-flavored **landmark per region** (Verdant Glade,
    Frostwatch Lighthouse, Ashfall Caldera, Mirage Oasis, Duskbell Grove, Old Foundry,
    Sunken Chapel, Prism Cavern, Skyreach Shrine) — each with worldbuilding lore signs, a
    keeper NPC (branching dialog in `data/dialogs/regions_lore.json`), a first-visit
    reward, and a `Wonders of <region>` exploration side quest. Wired to each Crossroads.
  - **Story deepened**: the three Hollow agents are now a named cell (Vole/Cinder/Wisp)
    that reacts to your progress; a new mid-arc boss, **Lieutenant Mourn**, waits in
    Duskbell Grove and is folded into the `main_hollow_order` quest before the Archon.
  - Totals: **158 maps, 44 quests, 14 dialogs**. check_chain extended to verify every
    landmark (door round-trip + keeper reachable); all validators + 30/30 tests pass.
- 2026-07-03 — **Population, mature voices & signposts**:
  - `generate_townsfolk.py` rewritten in an **adult register** (debt, loss, compromise,
    disillusion — not childish), expanded to **62 townsfolk** across Crossroads, gate
    towns and landmarks, with region-specific voices and branching choices.
  - `rewrite_trainer_voices.py`: characterful mature pre/post-battle lines for all
    **72 gym leaders** (a philosophy per element), **36 Elites** (escalating gravitas by
    seat) and **9 Champions**. Teams/badges/ids untouched.
  - `generate_signs.py`: **+32 signposts** — a directory + League rules sign on every
    Crossroads, a gate milepost, and a weathered wilds warning per region (many tied to
    the Order arc). Total signs: 209.
  - Totals: **76 dialog scripts, 97 map NPCs, 209 signs, 50→76 dialogs**. Validators,
    check_chain and 30/30 tests all pass; WORLD.md regenerated.
- 2026-07-03 — **Coherence hardening + rival battles**:
  - Fixed a name collision: the Hollow defector is now **Verel** (was "Sable", clashing
    with Warden Sable, Verdantia's gym boss) — renamed across dialogs, generators, docs.
  - The 7 generated-region quest texts now name the actual Champions (synced by
    `rewrite_trainer_voices.py`, so re-runs keep them coherent).
  - **New canonical pipeline `tools/generators/run_all.py`** — runs every generator in
    the one valid order, then all verifiers. Proved convergent end-to-end (twice).
  - **`generate_story_placements.py` now OWNS the story**: cast placements (Corin ×9,
    Verel, Mourn, Archon + mask), the named agent cell, the Lieutenant record, the
    Hollow quest shape (Lieutenant step, finale-choice completion) and the canonical
    ending order — previously one-off edits that a pipeline re-run silently erased
    (endings mis-ordered, agents renamed back, quest step lost). All restored and pinned.
  - Gate shops now stock the extras items on regeneration; gate townsfolk no longer
    overlap the gate sign tile.
  - **NEW: 3 rival battles vs Corin** (`generate_rival_battles.py`) — Verdantia route,
    Solane wilds, Brume wilds — his team grows coherently across the game (Chirpit/Nibbit
    → evolved forms + a Sunwisp caught in Solane → + a Brume Murkfin), with fork-neutral
    mature dialogue, plus the side quest "The Count Between Us" (+2 Corin relationship on
    completion, feeding the Rivals-to-the-End ending).
  - Full pipeline + all verifiers green: data validation, world walk (incl. the new
    Corin trainer tiles), structural gaps, 30/30 math tests.
- 2026-07-03 — **Ferry network (free inter-region travel)**:
  - Two small engine extensions: dialog **choices can carry a `condition`** (the runner
    filters them via GameState.condition_met) and a new **`warp` action** that sets
    GameState.pending_warp, consumed by the overworld's _process (same re-entrancy-safe
    pattern as endings). Both validated at boot (GDScript + Python: warp target map and
    spawn must exist).
  - New `generate_ferry.py` (in run_all after story placements): one shared Harbormaster
    dialog + 9 Harbormaster NPCs (one per region). Destinations are gated by
    `region_visited`, so only regions you have set foot in are offered — sequential story
    progression through the flag-gated ports is untouched, and return trips become
    one conversation instead of a long walk. Fulfils the original spec's "travel freely
    between unlocked regions".
  - Full pipeline re-run: all verifiers green (validators, world walk, courts, landmarks,
    structural gaps, 30/30 math tests).
- 2026-07-03 — **Gameplay-logic lint + team legality fixes**:
  - New verifier `tools/validators/lint_gameplay.py` (added to run_all): every trainer
    member must know a damaging move, only learnset moves, use a level-legal form
    (no evolved form below its evolution level), levels in [2,100]; every wild entry
    must have a damaging move at level_min. First run: **2,661 errors** — overwhelmingly
    under-leveled evolved forms in Battle Courts and route-trainer teams.
  - Fixes: a shared "form demoter" (walk down the evolution chain until level-legal) in
    generate_expansion (route trainers, Hollow agents) and generate_bulk (court teams);
    hand-authored fixes for Warden Sable (bloomcat → L16) and Isolde (mistelk → L20,
    gustling's unlearnable guard_up swapped). Lint now clean (6 tolerated above-level
    "tutored" moves).
  - generate_league now **prunes its own demo_g3 output** before regenerating — each
    re-run had been silently accumulating orphaned species via the numeric name
    fallback (dex had bloated to 2,743; back to the canonical 2,097). The fallback
    itself now composes two roots ("cinderbrine…") instead of digits: **0 digit-named
    species** remain.
  - Full pipeline + all six verifiers green.
