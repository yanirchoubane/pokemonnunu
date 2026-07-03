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

CHAMP_VOICE = {
    "verdantia": ("Sovereign Laurel: Eight badges say you can win. I'm here to ask a harder question — can you keep going?",
                  "Sovereign Laurel: You can. Verdantia has its answer, and its new Champion. Go north; the road only gets truer.",
                  "Sovereign Laurel: Not yet. Winning is loud. Enduring is quiet. Come back quiet."),
    "aquilon": ("Marshal Eirwen: The north doesn't crown the strongest. It crowns whoever's still upright at the end. Begin.",
                "Marshal Eirwen: Upright, and clear-eyed. Aquilon is yours to carry. Mind what you do with the weight.",
                "Marshal Eirwen: The cold took the steam out of you. Rest, then climb back."),
}


def champ_generic(region):
    return (f"Champion of {region}: You came a long way to stand here. Let's see what the road left in you.",
            f"Champion of {region}: It left plenty. {region} bows — carry its crest without letting it carry you.",
            f"Champion of {region}: The summit keeps its count. Come back heavier.")


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
        # champion (region-specific voice if present, else generic mature)
        champ_id = {"verdantia": "verdantia_sovereign", "aquilon": "aquilon_marshal"}.get(rid, f"{rid}_champion")
        if champ_id in by:
            if rid in CHAMP_VOICE:
                intro, defeat, victory = CHAMP_VOICE[rid]
            else:
                intro, defeat, victory = champ_generic(region)
            by[champ_id]["dialogue_intro"] = intro
            by[champ_id]["dialogue_defeat"] = defeat
            by[champ_id]["dialogue_victory"] = victory
            champs += 1

    save(tp, doc)
    print(f"Rewrote voices: {gyms} gym leaders, {elites} Elites, {champs} Champions.")


if __name__ == "__main__":
    main()
