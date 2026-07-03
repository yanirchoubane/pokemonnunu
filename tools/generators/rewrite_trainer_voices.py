#!/usr/bin/env python3
"""Rewrite boss-trainer voices — give the 72 gym leaders, Elites and Champions
mature, characterful pre/post-battle lines instead of the generated templates.

Keyed by element (gyms), by seat (Elites) and by region (Champions), rotated so
neighbouring fights don't read identically. Adult register — conviction, cost,
weariness — not cheerful filler. Only edits dialogue_* strings; teams, levels,
badges and ids are untouched. All content original. Idempotent.

Usage: python3 tools/generators/rewrite_trainer_voices.py
"""
from __future__ import annotations

import json
import os

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA = os.path.join(ROOT, "data")
TYPES = ["normal", "fire", "water", "grass", "electric", "earth", "wind", "mystic"]
REGION_ORDER = ["verdantia", "aquilon", "cindral", "solane", "umbra",
                "ferrock", "brume", "lumen", "zephyra"]

# element -> (intro, defeat, victory) in a mature register
GYM_VOICE = {
    "normal": ("Nothing flashy in my hall. Just fundamentals, and the discipline to trust them when it matters.",
               "Clean. Unhurried. You earned the badge the honest way — remember how that felt.",
               "Fundamentals beat flourish today. Come back when your basics are quieter."),
    "fire": ("Everyone thinks fire is rage. Fire is patience that finally ran out. Show me yours.",
             "You banked your heat and spent it at the right breath. That's the whole art. Take the badge.",
             "You burned too early and had nothing left for the end. Fire keeps. Learn that."),
    "water": ("Tide doesn't argue with the shore. It just keeps coming until the shore agrees. Begin.",
              "You wore me down like weather. Slow, certain, inevitable. The badge is yours.",
              "You crashed all at once. The sea knows better than to spend itself in one wave."),
    "grass": ("Growth is slow, unglamorous, and it outlives everything that mocked it. So will my team.",
              "You had the patience to let the match ripen. Rare, these days. Well earned.",
              "You rushed the harvest. Nothing grown in a hurry ever held. Try again."),
    "electric": ("One clean decision, delivered before the other side finishes theirs. That's all lightning is.",
                 "Faster than me where it counted. I felt that decision land. The badge fits you.",
                 "You hesitated on the turn that mattered. Against charge, hesitation is the loss."),
    "earth": ("I don't move first and I don't move much. I simply do not fall. Try to make me.",
              "You found the one seam in the stone and worked it until I broke. Skilled. Take it.",
              "You threw yourself at the wall until you were the one that cracked. Patience, challenger."),
    "wind": ("You'll never quite see where my team is. That's not a trick. That's the discipline of the open sky.",
             "You read the wind when you couldn't see it. That's mastery. Wear the badge lightly.",
             "You swung at where I'd been. The sky is always already somewhere else."),
    "mystic": ("I won't claim to read minds. I read patterns — and yours has been loud since you walked in.",
               "You changed your pattern the moment I named it. That's the only counter there is. Deserved.",
               "You fought the way I predicted, exactly. Surprise me next time, or don't return."),
}

ELITE_VOICE = [
    ("First of the four. I weed out the confident. Show me you're something sturdier.",
     "Sturdier than confident. Good. The next seat is crueller — go warm.",
     "Confidence isn't a strategy. Come back when you've traded it for something that holds."),
    ("Second seat. The tired ones stop here — the ones who spent everything proving the first point.",
     "Still standing, still thinking. Pass. The third won't let you think at all.",
     "You left your best in the last hall. Bring it whole next time, not in pieces."),
    ("Third. By now the badges have made you certain. I am here to make you doubt, precisely.",
     "You doubted at the right depth and kept moving. That's poise. Go on to the last.",
     "Doubt swallowed you. It does that to the certain. Steady yourself and return."),
    ("Last of the four. Everything gentle is behind you. What's left is only whether you meant it.",
     "You meant it. All the way down. The Champion is waiting — and so, now, is your name.",
     "You didn't mean it enough. The corridor keeps its honest count. Come back meaning it."),
]

# Each of the nine Champions gets a name and a region-textured, adult voice.
CHAMP_NAME = {
    "verdantia": "Sovereign Laurel", "aquilon": "Marshal Eirwen", "cindral": "Magnate Vulcaine",
    "solane": "Consul Adnan", "umbra": "Arbiter Nocturne", "ferrock": "Ironmonger Casque",
    "brume": "Abbess Threnody", "lumen": "Oracle Calla", "zephyra": "Skylord Peregrine",
}
CHAMP_VOICE = {
    "verdantia": ("Eight badges say you can win. I'm here to ask the harder question — can you keep going once no one's clapping?",
                  "You can. Verdantia has its answer, and its new Champion. Go north; the road only gets truer and lonelier.",
                  "Not yet. Winning is loud. Enduring is quiet. Come back when you've learned the difference."),
    "aquilon": ("The north doesn't crown the strongest. It crowns whoever's still upright at the end. Let's find out which you are.",
                "Upright, and clear-eyed. Aquilon is yours to carry. Mind what the weight does to a person — I've watched it hollow better ones.",
                "The cold took the steam out of you. There's no shame in it. Rest, and climb back."),
    "cindral": ("I bought this mountain's mines and I answer for every lung they cost. A crest doesn't absolve that. Neither will beating me.",
                "You fought like the debt was personal. Good. Cindral's crest is heavier than it looks — carry it honestly.",
                "You spent everything early, like the miners do. The mountain teaches patience the slow way. Return."),
    "solane": ("Out here, water is law and I am its consul. I've turned away the Order and the desperate alike. Show me which you are.",
               "Neither, it turns out — just certain. Solane's crest is yours. Ration your certainty; the dunes punish waste.",
               "The heat found the crack in your resolve. It always does. Drink, wait for dusk, come back sure."),
    "umbra": ("I judge disputes no gym could settle — debts, betrayals, the Order's quiet cruelties. Consider this hearing your last appeal.",
              "The ruling favours you. Umbra's crest, and my respect — spend both carefully, they don't refund.",
              "You argued your case with force and forgot the mercy. The grove remembers both. Adjourned."),
    "ferrock": ("I kept the last forge lit when the town went dark. Everything I love, I've had to outlast. Try to outlast me.",
                "You did. Barely, honestly, completely. Ferrock's crest was struck for hands like yours. Keep it useful.",
                "The forge outlasted you today. Cold iron, warm heart — bring both next time, not just the one."),
    "brume": ("I buried this town under the fen to keep it whole, and I've grieved it every day since. Grief makes a patient opponent.",
              "You walked through the mist instead of around it. So few do. Brume's crest, and a prayer for your road.",
              "You mistook my sorrow for softness. The drowned are the most stubborn of all. Come back when you understand."),
    "lumen": ("I've watched a thousand challengers in the crystals before they ever reached me. I already know how you lose. Prove the vision wrong.",
              "You broke the pattern I foresaw — the only victory the cavern honours. Lumen's crest reflects a bright day. Earn more of them.",
              "You lost exactly as the light showed. Change, or the vision will keep being right."),
    "zephyra": ("You climbed nine regions to breathe this wind. Most people leave something behind to get this high. I intend to find out what you kept.",
                "You kept the part that matters. Zephyra's crest, and the whole sky, are yours. The Archon kept nothing — remember that up there.",
                "The height took your breath before I did. No shame in the sky winning. Climb again."),
}


def champ_generic(region):
    return (f"You came a long way to stand here. Let's see what the road left in you.",
            f"It left plenty. {region} bows — carry its crest without letting it carry you.",
            f"The summit keeps its count. Come back heavier.")


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(p, d):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
        f.write("\n")


def main():
    tp = os.path.join(DATA, "trainers", "trainers.json")
    doc = load(tp)
    by = {t["id"]: t for t in doc["trainers"]}
    gyms = elites = champs = 0

    for rid in REGION_ORDER:
        region = rid.capitalize()
        for t in TYPES:
            tid = f"{rid}_gym_{t}"
            if tid in by:
                intro, defeat, victory = GYM_VOICE[t]
                name = by[tid]["display_name"]
                by[tid]["dialogue_intro"] = f"{name}: {intro}"
                by[tid]["dialogue_defeat"] = f"{name}: {defeat}"
                by[tid]["dialogue_victory"] = f"{name}: {victory}"
                gyms += 1
        for i in range(1, 5):
            tid = f"{rid}_elite_{i}"
            if tid in by:
                intro, defeat, victory = ELITE_VOICE[i - 1]
                name = by[tid]["display_name"]
                by[tid]["dialogue_intro"] = f"{name}: {intro}"
                by[tid]["dialogue_defeat"] = f"{name}: {defeat}"
                by[tid]["dialogue_victory"] = f"{name}: {victory}"
                elites += 1
        # champion: give it a name and a region-textured, adult voice
        champ_id = {"verdantia": "verdantia_sovereign", "aquilon": "aquilon_marshal"}.get(rid, f"{rid}_champion")
        if champ_id in by:
            name = CHAMP_NAME.get(rid, by[champ_id].get("display_name", f"Champion of {region}"))
            by[champ_id]["display_name"] = name
            lines = CHAMP_VOICE.get(rid) or champ_generic(region)
            intro, defeat, victory = lines
            by[champ_id]["dialogue_intro"] = f"{name}: {intro}"
            by[champ_id]["dialogue_defeat"] = f"{name}: {defeat}"
            by[champ_id]["dialogue_victory"] = f"{name}: {victory}"
            champs += 1

    save(tp, doc)

    # Keep quest texts coherent with the champion names (generate_regions writes
    # the generic "Champion of X" — this pass, run after it, fixes them up).
    qp = os.path.join(DATA, "quests", "quests.json")
    qdoc = load(qp)
    synced = 0
    for quest in qdoc["quests"]:
        for rid in REGION_ORDER:
            if quest["id"] == f"main_{rid}" and rid in CHAMP_NAME:
                for obj in quest.get("objectives", []):
                    if obj.get("id") == "obj_champion":
                        obj["text"] = ("Defeat %s, Champion of %s, in the League hall."
                                       % (CHAMP_NAME[rid], rid.capitalize()))
                        synced += 1
    save(qp, qdoc)
    print(f"Rewrote voices: {gyms} gym leaders, {elites} Elites, {champs} Champions; "
          f"synced {synced} quest texts.")


if __name__ == "__main__":
    main()
