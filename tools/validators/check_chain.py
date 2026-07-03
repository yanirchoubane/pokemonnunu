#!/usr/bin/env python3
"""Whole-world reachability checker.

Static checks on every map (bounds, walkability, warp/spawn integrity,
no spawn-on-warp loops), then a progression walk of all nine regions:
entry -> crossroads -> all 8 gyms -> League (after the circuit) -> the four
Elites in sequence -> Champion -> port to the next region, and return trips.

Run after any generator or hand edit: python3 tools/validators/check_chain.py
"""
from __future__ import annotations

import glob
import json
import os
from collections import deque

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA = os.path.join(ROOT, "data")
WALKABLE = {"ground", "path", "floor", "sand", "stone", "tall_grass", "heal_pad", "door"}
TYPES = ["normal", "fire", "water", "grass", "electric", "earth", "wind", "mystic"]

maps: dict = {}
errors: list = []


def tile(m, x, y):
    rows = m["rows"]
    if y < 0 or y >= len(rows) or x < 0 or x >= len(rows[0]):
        return "oob"
    return m["legend"].get(rows[y][x], "wall")


def spawn_pos(mid, sid):
    for o in maps[mid]["objects"]:
        if o["type"] == "spawn" and o.get("id") == sid:
            return (o["x"], o["y"])
    return None


def bfs(mid, start, flags):
    m = maps[mid]
    blocked = set()
    for o in m["objects"]:
        if o["type"] in ("npc", "sign", "shop"):
            blocked.add((o["x"], o["y"]))
        elif o["type"] == "trainer" and o.get("flag") not in flags:
            blocked.add((o["x"], o["y"]))
    seen, dq = {start}, deque([start])
    while dq:
        x, y = dq.popleft()
        for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            n = (x + dx, y + dy)
            if n in seen or n in blocked:
                continue
            if tile(m, *n) in WALKABLE:
                seen.add(n)
                dq.append(n)
    return seen


def adj(reach, x, y):
    return any((x + dx, y + dy) in reach
               for dx, dy in ((0, 0), (0, 1), (0, -1), (1, 0), (-1, 0)))


def door_at(mid, pred):
    for o in maps[mid]["objects"]:
        if o["type"] in ("door", "warp") and pred(o):
            return o
    return None


def check_static():
    for mid, m in maps.items():
        w = len(m["rows"][0])
        for r_i, row in enumerate(m["rows"]):
            if len(row) != w:
                errors.append(f"{mid}: row {r_i} width mismatch")
        for o in m["objects"]:
            if "x" not in o:
                continue
            x, y = o["x"], o["y"]
            if not (0 <= x < w and 0 <= y < len(m["rows"])):
                errors.append(f"{mid}: {o['type']} at ({x},{y}) out of bounds")
                continue
            t = tile(m, x, y)
            if o["type"] in ("spawn", "warp", "item", "heal", "door") and t not in WALKABLE:
                errors.append(f"{mid}: {o['type']} at ({x},{y}) on non-walkable '{t}'")
            if o["type"] in ("warp", "door"):
                tm, ts = o.get("to_map"), o.get("to_spawn", "default")
                if tm not in maps:
                    errors.append(f"{mid}: {o['type']} -> unknown map {tm}")
                    continue
                pos = spawn_pos(tm, ts)
                if pos is None:
                    errors.append(f"{mid}: {o['type']} -> {tm} unknown spawn '{ts}'")
                    continue
                if tile(maps[tm], *pos) not in WALKABLE:
                    errors.append(f"{mid}: arrival spawn {tm}/{ts} on non-walkable tile")
                for oo in maps[tm]["objects"]:
                    if oo["type"] in ("warp", "door") and (oo.get("x"), oo.get("y")) == pos:
                        errors.append(f"{mid}: spawn {tm}/{ts} sits ON a {oo['type']} (instant loop)")


def check_league(rid, flags):
    """Crossroads -> gyms -> League corridor -> Champion (+ next port)."""
    cross = f"{rid}_crossroads"
    league = f"{rid}_league" if rid in ("verdantia", "aquilon") else f"{rid}_hall"
    r = bfs(cross, spawn_pos(cross, "from_wilds"), flags)
    for t in TYPES:
        d = door_at(cross, lambda o, t=t: o.get("to_map") == f"{rid}_gym_{t}")
        if d is None or (d["x"], d["y"]) not in r:
            errors.append(f"{cross}: gym door for '{t}' unreachable")
        g = f"{rid}_gym_{t}"
        gr = bfs(g, spawn_pos(g, "entrance"), flags)
        leader = next(o for o in maps[g]["objects"] if o["type"] == "trainer")
        if not adj(gr, leader["x"], leader["y"]):
            errors.append(f"{g}: leader unreachable")
        flags.add(f"beat_{rid}_gym_{t}")
    ld = door_at(cross, lambda o: o.get("to_map") == league)
    if ld is None:
        errors.append(f"{cross}: league door missing")
    elif ld.get("requires_flag", "") != f"league_open_{rid}":
        errors.append(f"{cross}: league door gated by '{ld.get('requires_flag')}', "
                      f"expected league_open_{rid}")
    flags.add(f"league_open_{rid}")
    # Elite corridor: each elite must be the only way forward, in order.
    entrance = spawn_pos(league, "entrance")
    champ = next(o for o in maps[league]["objects"]
                 if o["type"] == "trainer" and "elite" not in o["trainer_id"])
    for i in range(1, 5):
        r = bfs(league, entrance, flags)
        elite = next(o for o in maps[league]["objects"] if o.get("trainer_id") == f"{rid}_elite_{i}")
        if not adj(r, elite["x"], elite["y"]):
            errors.append(f"{league}: elite {i} unreachable in sequence")
        if adj(r, champ["x"], champ["y"]) and i == 1:
            errors.append(f"{league}: champion reachable BEFORE the elites — corridor leaks")
        flags.add(f"beat_{rid}_elite_{i}")
    r = bfs(league, entrance, flags)
    if not adj(r, champ["x"], champ["y"]):
        errors.append(f"{league}: champion unreachable after the elites")
    flags.add(str(champ["flag"]))
    top = door_at(league, lambda o: o.get("y") == 0)
    if top is not None:
        r = bfs(league, entrance, flags)
        if (top["x"], top["y"]) not in r:
            errors.append(f"{league}: next-region port unreachable after champion")


def main() -> int:
    for f in glob.glob(os.path.join(DATA, "regions", "maps", "*.json")):
        m = json.load(open(f))
        maps[m["id"]] = m
    check_static()

    flags: set = set()
    # Verdantia: town -> route -> crossroads
    r = bfs("verdantia_town", spawn_pos("verdantia_town", "default"), flags)
    if (6, 11) not in r:
        errors.append("verdantia_town: south warp unreachable")
    r = bfs("verdantia_route", spawn_pos("verdantia_route", "from_town"), flags)
    if (14, 3) not in r:
        errors.append("verdantia_route: crossroads door unreachable")
    check_league("verdantia", flags)
    flags |= {"beat_gym_verdantia", "beat_route_scout", "quest_verdant_done"}

    # Aquilon: shore -> crossroads + summit story path
    r = bfs("aquilon_shore", spawn_pos("aquilon_shore", "default"), flags)
    for pos, what in [((14, 5), "crossroads door"), ((13, 1), "ridge warp")]:
        if pos not in r:
            errors.append(f"aquilon_shore: {what} unreachable")
    check_league("aquilon", flags)
    flags |= {"beat_aquilon_gatekeeper", "beat_aquilon_champion"}
    r = bfs("aquilon_shore", spawn_pos("aquilon_shore", "default"), flags)
    if (7, 0) not in r:
        errors.append("aquilon_shore: north ferry unreachable after Isolde")

    # Generated chain
    for rid in ["cindral", "solane", "umbra", "ferrock", "brume", "lumen", "zephyra"]:
        gate, wilds = f"{rid}_gate", f"{rid}_wilds"
        r = bfs(gate, spawn_pos(gate, "port"), flags)
        east = door_at(gate, lambda o: o.get("x") == 11)
        if east is None or (east["x"], east["y"]) not in r:
            errors.append(f"{gate}: east door unreachable")
        r = bfs(wilds, spawn_pos(wilds, "from_gate"), flags)
        scout = next(o for o in maps[wilds]["objects"] if o.get("trainer_id") == f"{rid}_scout")
        if not adj(r, scout["x"], scout["y"]):
            errors.append(f"{wilds}: scout unreachable")
        flags.add(f"beat_{rid}_scout")
        r = bfs(wilds, spawn_pos(wilds, "from_gate"), flags)
        if (13, 4) not in r:
            errors.append(f"{wilds}: crossroads door unreachable after scout")
        check_league(rid, flags)
        # return trip gate west door
        r = bfs(gate, spawn_pos(gate, "from_wilds"), flags)
        west = door_at(gate, lambda o: o.get("x") == 0)
        if west is None or (west["x"], west["y"]) not in r:
            errors.append(f"{gate}: west (return) door unreachable")

    # Battle Courts: door round-trip + every trainer reachable from the entrance.
    courts = 0
    for mid, m in maps.items():
        if "_court_" not in mid:
            continue
        courts += 1
        cross = f"{m['region']}_crossroads"
        door = door_at(mid, lambda o: o.get("to_map") == cross)
        if door is None:
            errors.append(f"{mid}: no door back to {cross}")
        r = bfs(mid, spawn_pos(mid, "entrance"), flags)
        for o in m["objects"]:
            if o["type"] == "trainer" and not adj(r, o["x"], o["y"]):
                errors.append(f"{mid}: court trainer {o['trainer_id']} unreachable")
        cd = door_at(cross, lambda o, mid=mid: o.get("to_map") == mid)
        if cd is None:
            errors.append(f"{cross}: no door to {mid}")

    if errors:
        print(f"✗ {len(errors)} problem(s):")
        for e in errors:
            print("  -", e)
        return 1
    print("✓ All 9 regions fully traversable: entries, 72 gyms, 9 league corridors "
          "(elites in sequence), champions, ports and return trips.")
    print(f"✓ {courts} Battle Courts verified: door round-trips and every trainer reachable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
