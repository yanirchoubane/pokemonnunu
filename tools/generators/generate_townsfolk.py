#!/usr/bin/env python3
"""Townsfolk generator — many more branching NPC conversations, one crowd per region.

Places four flavor NPCs on every region Crossroads, each with an original, themed
branching dialog (worldbuilding, rumors about the region's landmark and the Hollow
Order, a couple of player choices). Turns the handful of story scripts into a
world that actually talks back. All content original; idempotent.

Run after generate_league.py (needs the Crossroads maps) and generate_places.py
(so the landmark references land). Then run check_chain.
Usage: python3 tools/generators/generate_townsfolk.py
"""
from __future__ import annotations

import json
import os

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA = os.path.join(ROOT, "data")

# Per region: landmark name + four townsfolk, each with lines and (some) a choice.
# Placeholders: {land} = landmark, {region} = region display name.
REGIONS = {
    "verdantia": ("Verdant Glade", "Verdantia", "grassy meadows", [
        ("elder", "Old Perisel", [
            "Old Perisel: I've watched trainers leave this town for forty springs.",
            "Old Perisel: The ones who came back changed always visited the {land} first. Funny, that."]),
        ("kid", "Runner Tavi", [
            "Tavi: Are you gonna be a Champion?! My brother said the League has EIGHT gyms per region now!",
            "Tavi: Eight! That's like... a whole lot of eight!"]),
        ("merchant", "Peddler Onna", [
            "Onna: Fresh orbs, salves, the works. A trainer crossing nine regions needs a full bag.",
            "Onna: Word to the wise — the northern roads aren't as safe as they were."]),
        ("fan", "Scholar Bem", [
            "Bem: You know the {region} meadows hold creatures found nowhere else?",
            "Bem: Every region does. Two thousand species, they reckon, and still counting."],
         [("Two thousand? I'll catch them all.", "adjust_relationship", "bem", 1,
           "Bem: Ha! Spoken like a true field naturalist. I'll be watching your Pokédex."),
          ("I only need six good ones.", None, None, 0,
           "Bem: A purist. The old masters would approve.")]),
    ]),
    "aquilon": ("Frostwatch Lighthouse", "Aquilon", "cold coast", [
        ("elder", "Keeper's Widow Sella", [
            "Sella: My husband tended the {land} till the sea took him. The little light-creature still keeps it lit.",
            "Sella: Loyalty outlasts us. Remember that when you bond with yours."]),
        ("kid", "Dockrat Pim", [
            "Pim: The gym leaders here are TOUGH. Tidecaller nearly swept my whole team!",
            "Pim: You gotta beat all eight to even reach the League corridor, y'know."]),
        ("sailor", "Bosun Krael", [
            "Krael: Gray coats came through on the last ferry. Didn't like the look of 'em.",
            "Krael: 'The Hollow Order,' they called themselves. Collectin' debts nobody owed."]),
        ("fan", "Cartographer Ives", [
            "Ives: Nine regions, one road. I'm mapping every port between them.",
            "Ives: Beat a region's Champion and its northern ferry opens. That's the whole spine of the world."],
         [("Where does the road end?", None, None, 0,
           "Ives: Zephyra. The sky steppes. After that... you carry the map yourself."),
          ("I'll map it with my feet.", "adjust_relationship", "ives", 1,
           "Ives: A walker! Send word from the far north, would you?")]),
    ]),
    "cindral": ("Ashfall Caldera", "Cindral", "volcanic slopes", [
        ("elder", "Ashwarden Tolz", [
            "Tolz: The {land} breathes, traveler. Cinders fall upward on the hottest nights.",
            "Tolz: Fire that endures beats fire that rages. Ask any old ember-creature."]),
        ("kid", "Sparky Wen", [
            "Wen: A lady in a gray coat asked me to 'lend' her my creature. I said NO WAY!",
            "Wen: She had the coldest eyes. Be careful out in the wilds."]),
        ("miner", "Delver Hob", [
            "Hob: The ore veins here hum. The creatures that live in 'em hum back.",
            "Hob: Dig long enough and you learn to listen. Same with a good team."]),
        ("fan", "Historian Cael", [
            "Cael: They say a defector named Sable is warning trainers about the Hollow Order.",
            "Cael: If you meet them at the gate — listen. They know things the rest of us don't."]),
    ]),
    "solane": ("Mirage Oasis", "Solane", "sun-baked dunes", [
        ("elder", "Dune-mother Riss", [
            "Riss: Two oases shimmer at the {land}. Only one holds water. Choose with your eyes closed.",
            "Riss: The desert rewards the sure, not the swift."]),
        ("kid", "Sandpiper Lu", [
            "Lu: I saw a Hollow agent get chased off by a wild pack! Even the creatures don't like 'em!"]),
        ("nomad", "Wayfarer Ode", [
            "Ode: I've crossed four regions with the same team. We keep our real levels; the regions just... balance us.",
            "Ode: A soft cap, they call it. Keeps a strong traveler from trampling a new land."]),
        ("fan", "Rumormonger Sett", [
            "Sett: Heard the Order has a Lieutenant now. Mourn. Waits somewhere in Umbra's grove.",
            "Sett: Tragic figure, by all accounts. Doesn't make him easy."],
         [("Where in Umbra exactly?", None, None, 0,
           "Sett: The Duskbell Grove. Where the bells ring with no hand. You'll feel it."),
          ("I'll find him myself.", None, None, 0,
           "Sett: Course you will, hero.")]),
    ]),
    "umbra": ("Duskbell Grove", "Umbra", "twilight woods", [
        ("elder", "Bellkeeper Vane", [
            "Vane: Stay for the dusk bell at the {land}. It rings once, for everyone.",
            "Vane: The Order's Lieutenant lingers there now. He never stays for the bell either."]),
        ("kid", "Glowbug Nix", [
            "Nix: The creatures here glow at night! Umbra's the prettiest scary place ever."]),
        ("watcher", "Nightwatch Oru", [
            "Oru: Mourn passed through. Said he joined the Order to stop feeling hollow.",
            "Oru: It only spread, he said. Sad man. Strong team, though — mind yourself."]),
        ("fan", "Dreamreader Sile", [
            "Sile: They say your choices ripple, trainer. How you treat a rival. Whether you show mercy.",
            "Sile: The world remembers. I've seen a dozen different endings walk out of these woods."],
         [("My choices are my own.", "adjust_relationship", "sile", 1,
           "Sile: As they should be. That's rather the point."),
          ("Endings? Tell me more.", None, None, 0,
           "Sile: No, no. You write yours by living it. Go on.")]),
    ]),
    "ferrock": ("The Old Foundry", "Ferrock", "iron hills", [
        ("elder", "Foundry-elder Gann", [
            "Gann: Every anvil in {region} was struck first at the {land}. The creatures who worked it never left.",
            "Gann: Partnership, not ownership. The ones who forgot always left with less."]),
        ("kid", "Bolt-kid Reya", [
            "Reya: I wanna be the Stormsmith someday and run the electric gym! Zap zap!"]),
        ("smith", "Ironhand Dex", [
            "Dex: Strong things are simple things, kept. A team. A promise. A hammer.",
            "Dex: The Order forgot 'kept.' They only ever took."]),
        ("fan", "Ledger-clerk Ims", [
            "Ims: Two of the Order's agents already fell to some traveler. Vole, then Cinder.",
            "Ims: If that's you — the third, Wisp, hides in Lumen's crystal deeps."]),
    ]),
    "brume": ("The Sunken Chapel", "Brume", "misty fens", [
        ("elder", "Fen-elder Morrow", [
            "Morrow: The {land} drowned with a whole town kneeling in it. The bell still tolls under the reeds.",
            "Morrow: In {region}, nothing's lost. It only goes quiet a while."]),
        ("kid", "Reed-child Ply", [
            "Ply: The fog talks if you listen! ...Okay, maybe it's just the creatures. But maybe not!"]),
        ("priest", "Acolyte Sen", [
            "Sen: Grief and mist look alike from far off. Up close, both can be walked through.",
            "Sen: Whatever weighs on you, traveler — the fen has carried heavier."]),
        ("fan", "Chronicler Vell", [
            "Vell: The Archon waits past Zephyra now. Done sending others.",
            "Vell: When you face them, remember: they were a trainer once. Like you. Like Mourn."],
         [("I'll end the Order for good.", "set_var", "order_stance", "justice",
           "Vell: Clean and final. The roads would thank you."),
          ("Maybe it can be mended.", "set_var", "order_stance", "mercy",
           "Vell: ...Maybe you're the one who can. Few would try.")]),
    ]),
    "lumen": ("Prism Cavern", "Lumen", "crystal vale", [
        ("elder", "Seer-elder Lux", [
            "Lux: Look into the {land}'s crystals and you'll see a day the valley kept for you.",
            "Lux: The kind trainers shine longer in the stone. I've watched thousands pass."]),
        ("kid", "Prism-tot Ami", [
            "Ami: The rocks glow rainbow! I wanna catch one that glows just like them!"]),
        ("guide", "Lightwarden Oss", [
            "Oss: The last Hollow agent, Wisp, is here in the deeps. End the cell, traveler.",
            "Oss: After Wisp, only the Lieutenant and the Archon remain."]),
        ("fan", "Lens-grinder Pia", [
            "Pia: They say a sky-spirit — Aetherion — visits Zephyra's shrine once a generation.",
            "Pia: Ultra rare. Most trainers only ever see it in a story. Will you?"],
         [("I'll be the one who catches it.", "adjust_relationship", "pia", 1,
           "Pia: Then climb high and watch the quiet skies. I believe you."),
          ("Some things should stay legends.", None, None, 0,
           "Pia: ...A rare kind of wisdom. The shrine would like you.")]),
    ]),
    "zephyra": ("Skyreach Shrine", "Zephyra", "sky steppes", [
        ("elder", "Windspoken Elah", [
            "Elah: You climbed nine regions to reach this wind. Breathe it. You earned the height.",
            "Elah: The {land} is the last floor a trainer stands on and is still called grounded."]),
        ("kid", "Cloud-hopper Bit", [
            "Bit: The Champion's up top and she's got FIVE creatures! Five! You beat all four Elites first though."]),
        ("skywatch", "Galewatch Corr", [
            "Corr: The Archon's out in our wilds. Whatever you decide up there — decide it clear-eyed.",
            "Corr: Mercy or justice, the steppe will carry the story either way."]),
        ("fan", "Star-charter Nel", [
            "Nel: Nine crests. One unbroken road. If you've carried a team the whole way...",
            "Nel: ...then you're not far from a legend they'll tell at every gate you passed."]),
    ]),
}

# crossroads floor tiles that never block a gym-door approach or the heal/Corin tiles
SLOTS = [(4, 2), (11, 2), (4, 6), (11, 6)]
NPC_SPRITE = {"elder": "npc_villager", "kid": "npc_kid", "merchant": "npc_clerk",
              "fan": "npc_villager", "sailor": "npc_villager", "miner": "npc_villager",
              "nomad": "npc_watcher", "watcher": "npc_watcher", "smith": "npc_clerk",
              "priest": "npc_watcher", "guide": "npc_watcher", "skywatch": "npc_watcher"}


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(p, d):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
        f.write("\n")


def build_dialog(did, land, region, entry):
    """entry = (role, name, [lines], optional [choices]). Choice tuple:
       (text, action_kind|None, key, value, reply_line)."""
    role, name, lines = entry[0], entry[1], entry[2]
    lines = [ln.replace("{land}", land).replace("{region}", region) for ln in lines]
    node = {"id": "start", "portrait": role, "lines": lines}
    nodes = [node]
    if len(entry) > 3 and entry[3]:
        choices = []
        for i, (text, kind, key, val, reply) in enumerate(entry[3]):
            actions = []
            if kind == "adjust_relationship":
                actions.append({"kind": "adjust_relationship", "npc": key, "delta": int(val)})
            elif kind == "set_var":
                actions.append({"kind": "set_var", "var": key, "value": val})
            reply_id = f"reply_{i}"
            nodes.append({"id": reply_id, "entry": False, "portrait": role, "lines": [reply], "next": ""})
            choices.append({"text": text, "actions": actions, "next": reply_id})
        node["choices"] = choices
    else:
        node["next"] = ""
    return {"id": did, "nodes": nodes}


def main():
    doc = {"$schema_version": 1,
           "description": "Townsfolk conversations placed on each region's Crossroads.",
           "dialogs": []}
    placed = 0
    for rid, (land, region, _theme, folk) in REGIONS.items():
        cp = os.path.join(DATA, "regions", "maps", f"{rid}_crossroads.json")
        cross = load(cp)
        for i, entry in enumerate(folk[:len(SLOTS)]):
            did = f"town_{rid}_{entry[0]}"
            doc["dialogs"].append(build_dialog(did, land, region, entry))
            x, y = SLOTS[i]
            npc_id = f"{rid}_folk_{i}"
            if not any(o.get("type") == "npc" and o.get("npc_id") == npc_id for o in cross["objects"]):
                cross["objects"].append({
                    "type": "npc", "x": x, "y": y, "npc_id": npc_id,
                    "sprite": NPC_SPRITE.get(entry[0], "npc_villager"), "dialog_id": did})
                placed += 1
        save(cp, cross)
    save(os.path.join(DATA, "dialogs", "townsfolk.json"), doc)
    print(f"Townsfolk: {len(doc['dialogs'])} new NPC dialogs, {placed} NPCs placed across 9 Crossroads.")


if __name__ == "__main__":
    main()
