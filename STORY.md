# STORY.md — The branching narrative

All characters and events here are **original** to this project. The story is fully
data-driven (dialog scripts, story variables, relationship scores, composable
conditions and multiple endings) — see `DATA_FORMAT.md` for the schemas and
`data/dialogs/`, `data/endings/` for the content. Nothing is hard-coded in the engine.

## The spine

You begin in **Verdantia** under Professor **Maple**, pick a starter, and set out to
earn each region's crest by clearing its **eight gyms** (one per type), its **Elite
Four**, and its **Champion** — from Verdantia and Aquilon north through Cindral, Solane,
Umbra, Ferrock, Brume, Lumen and Zephyra.

## The rival: Corin

**Corin** started their journey a season before you and reappears at **every region's
Crossroads**. Each conversation offers choices that raise or lower your **relationship
score** with them (`relationship: corin`). The dialog reacts to that score and to your
progress, so Corin feels different in Aquilon than in Zephyra.

The fork happens in **Umbra**: the Hollow Order has been courting Corin, and he asks
whether the journey has meant anything with him in it.

- Answer warmly (and if your relationship is already high) → Corin **stays true**
  (`corin_arc = "true"`), and can share the best ending with you.
- Brush him off → Corin **falls** to the Order (`corin_fallen`), and later meetings turn
  cold.

## The antagonist: the Hollow Order

A gray-coated order that "collects debts" from trainers on the northern roads. In
**Cindral** you meet **Sable**, a **defector**, who explains that the Order isn't strong —
it's *empty*, hollowing people until taking feels like winning. Talking to Sable starts
the quest **"Shadows of the Hollow Order"** and lets you set your stance
(`order_stance`: justice or mercy).

You track down three named **Hollow agents** — **Vole** (Cindral), **Cinder** (Ferrock)
and **Wisp** (Lumen), a single cell that reacts to how far you've unravelled them — then
the **Hollow Lieutenant, Mourn**, who waits in Umbra's **Duskbell Grove** and is the
arc's emotional turn: someone who joined the Order to stop feeling hollow and watched it
spread. Finally the **Hollow Archon** in the Zephyra wilds. After the battle, a choice
decides the arc:

- **Mercy** — offer the Archon a road back. (`order_end = "mercy"`)
- **Justice** — burn the Order's ledgers and free the roads. (`order_end = "justice"`)

Either way the quest completes (`hollow_resolved` → `quest_hollow_done`).

## The eight endings (first matching condition wins)

| Ending | Triggered when |
|---|---|
| **Legend of the Nine Crests** | you beat the Champion/boss of all nine regions |
| **Rivals to the End** | Order resolved **and** relationship with Corin ≥ 4 |
| **The Hand You Didn't Raise** | you chose **mercy** at the Archon |
| **Ledgers to Ash** | you chose **justice** at the Archon |
| **The Hollow, Undone** | Aquilon story done + Order resolved (fallback) |
| **Champion of the North** | Aquilon story + Champion Isolde beaten |
| **Bonds Across Regions** | Aquilon story done + Corin relationship ≥ 2 |
| **The Lone Pioneer** | Aquilon story done (baseline) |

An ending fires from a `trigger_ending` action (the Archon finale, or Professor Maple's
epilogue), plays its text, autosaves, and returns to the title — the save stays playable
as post-game.

## Places worth visiting

Each region hangs a **unique landmark** off its Crossroads — a hand-written place with its
own lore signs, a keeper who remembers something, a first-visit reward, and an exploration
side quest (`Wonders of <region>`):

| Region | Landmark | Keeper |
|---|---|---|
| Verdantia | **Verdant Glade** — the first bond between human and creature | Elder Root |
| Aquilon | **Frostwatch Lighthouse** — a beam kept lit by a creature that never sleeps | Keeper Halden |
| Cindral | **Ashfall Caldera** — the mountain's heartbeat | Emberwarden Sol |
| Solane | **Mirage Oasis** — the real water beside the false one | Wanderer Sima |
| Umbra | **Duskbell Grove** — where day and night hold a conversation (and Mourn waits) | Nightwarden Vesper |
| Ferrock | **The Old Foundry** — where creatures forged a region | Foreman Dross |
| Brume | **The Sunken Chapel** — a town the fen rose to keep | Fenpriest Maren |
| Lumen | **Prism Cavern** — crystals that hold the valley's memories | Lumar the Seer |
| Zephyra | **Skyreach Shrine** — where a sky-spirit alights once a generation | Windspeaker Aquila |

## Extending it

Add NPCs with a `"dialog_id"`, write dialog scripts (condition-gated nodes, choices,
`actions`), and add endings with composable conditions. The validators check every node
jump, action kind and reference at boot and via
`python3 tools/validators/validate_data.py`. See `USER_CONTENT_GUIDE.md` to ship your own
story as a pack.
