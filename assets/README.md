# assets/

All demo visuals and audio are generated **procedurally at runtime** — there are no
bundled third-party images or sounds. See:

- `scripts/core/placeholder_gfx.gd` — draws creatures/tiles/characters from geometric
  shapes and deterministic colors.
- `scripts/autoload/audio_manager.gd` — synthesizes short original tones for music/SFX.

These folders exist so you can drop in your **own legally-obtained** assets later:

| Folder | Intended contents |
|---|---|
| `placeholder_characters/` | Player / NPC sprite sheets |
| `placeholder_creatures/`  | Creature battle sprites + overworld icons |
| `placeholder_tiles/`      | Tileset images |
| `placeholder_ui/`         | UI frames, icons (`icon.svg` is the app icon) |
| `placeholder_audio/`      | Music / SFX |

To use real assets, reference them by id from the data files and load them in the
relevant scene script. The engine never hard-codes an asset path for content.

**Do not add any Nintendo / Game Freak / The Pokémon Company material.** See
`LICENSE_NOTES.md`.
