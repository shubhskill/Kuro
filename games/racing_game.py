"""KURO Street Rush: turn-based strategy racing engine (Telegram UI in main.py)."""
import random

FINISH_LINE = 1000
RACE_ACTIONS = ("accelerate", "nitro", "drift", "defend", "repair")
DIFFICULTY = {
    "easy": {"ai_skill": 0.25, "hazard": 0.10},
    "medium": {"ai_skill": 0.45, "hazard": 0.16},
    "hard": {"ai_skill": 0.68, "hazard": 0.22},
    "expert": {"ai_skill": 0.86, "hazard": 0.28},
}
TRACK = ["straight", "turn", "speed", "rough", "shortcut", "turn", "straight", "obstacle"]
TRACK_LABELS = {
    "straight": "🛣️ STRAIGHT ROAD — Acceleration gets a reliable gain.",
    "turn": "↪️ SHARP TURN — Drift is the safest high-value move.",
    "speed": "⚡ SPEED ZONE — Nitro receives a bonus.",
    "rough": "🪨 ROUGH ROAD — Defend or repair to protect your car.",
    "shortcut": "🛤️ SHORTCUT — Drift can win extra distance, but it is risky.",
    "obstacle": "🚧 OBSTACLE ZONE — Defend avoids most damage.",
}


def _driver(player, is_ai=False):
    return {"id": player["id"], "name": player["name"], "progress": 0,
            "condition": 100, "nitro": 3, "finished": False,
            "is_ai": is_ai, "defending": False, "last_move": "Ready at the start"}


def create_race(players, difficulty="medium", mode="multi"):
    if difficulty not in DIFFICULTY:
        raise ValueError("Unknown racing difficulty")
    drivers = {p["id"]: _driver(p) for p in players}
    order = [p["id"] for p in players]
    if mode == "solo":
        ai_id = "kuro_ai"
        drivers[ai_id] = _driver({"id": ai_id, "name": "KURO AI"}, True)
        order.append(ai_id)
    return {"mode": mode, "difficulty": difficulty, "drivers": drivers,
            "player_order": order, "turn_index": 0, "round": 1,
            "track_index": 0, "finished": False, "winner_id": None,
            "winner_name": None, "finish_line": FINISH_LINE,
            "last_event": "The race is ready!"}


def current_turn_id(race):
    order = race["player_order"]
    for offset in range(len(order)):
        idx = (race["turn_index"] + offset) % len(order)
        driver = race["drivers"][order[idx]]
        if not driver["finished"]:
            race["turn_index"] = idx
            return order[idx]
    return None


def _advance_turn(race):
    order = race["player_order"]
    start = race["turn_index"]
    for offset in range(1, len(order) + 1):
        idx = (start + offset) % len(order)
        if not race["drivers"][order[idx]]["finished"]:
            race["turn_index"] = idx
            if idx == 0:
                race["round"] += 1
                race["track_index"] = (race["track_index"] + 1) % len(TRACK)
            return


def _hazard(race, driver):
    base = DIFFICULTY[race["difficulty"]]["hazard"]
    return random.random() < base + (0.08 if driver["condition"] < 40 else 0)


def apply_move(race, player_id, action):
    if race.get("finished"):
        return {"accepted": False, "message": "This race has already finished."}
    if action not in RACE_ACTIONS:
        return {"accepted": False, "message": "Unknown racing move."}
    if race["mode"] == "multi" and current_turn_id(race) != player_id:
        return {"accepted": False, "message": "It is not your turn."}
    driver = race["drivers"].get(player_id)
    if not driver or driver["finished"]:
        return {"accepted": False, "message": "You are not an active racer."}
    if action == "nitro" and driver["nitro"] <= 0:
        return {"accepted": False, "message": "No nitro left. Choose another move."}
    section = TRACK[race["track_index"]]
    gain, message = 0, ""
    driver["defending"] = False
    if action == "accelerate":
        gain = random.randint(85, 115)
        if section == "straight": gain += 20
        message = f"🏎️ {driver['name']} accelerated and gained {gain}m."
    elif action == "nitro":
        driver["nitro"] -= 1
        gain = random.randint(145, 185) + (35 if section == "speed" else 0)
        message = f"⚡ {driver['name']} fired Nitro and gained {gain}m! ({driver['nitro']} nitro left)"
    elif action == "drift":
        if section in ("turn", "shortcut"):
            gain = random.randint(105, 145)
            message = f"↪️ Perfect drift! {driver['name']} gained {gain}m."
        else:
            gain = random.randint(65, 95)
            message = f"↪️ Controlled drift. {driver['name']} gained {gain}m."
        if _hazard(race, driver):
            driver["condition"] = max(0, driver["condition"] - 8)
            message += " Car condition -8."
    elif action == "defend":
        driver["defending"] = True
        gain = random.randint(45, 70)
        message = f"🛡️ {driver['name']} took a defensive line and gained {gain}m."
        if section in ("rough", "obstacle"):
            driver["condition"] = min(100, driver["condition"] + 3)
            message += " Protected from the track hazard."
    elif action == "repair":
        driver["condition"] = min(100, driver["condition"] + 25)
        gain = 0
        message = f"🔧 {driver['name']} repaired the car. Condition is now {driver['condition']}%. No distance gained this turn."
    if action != "repair" and _hazard(race, driver) and section in ("rough", "obstacle") and not driver["defending"]:
        driver["condition"] = max(0, driver["condition"] - 15)
        gain = max(20, gain - 35)
        message += "\n🚧 Track incident! -15 condition and 35m lost."
    if driver["condition"] < 30 and action not in ("repair", "defend"):
        gain = int(gain * 0.75)
        message += "\n⚠️ Damaged car: movement reduced."
    driver["progress"] = min(FINISH_LINE, driver["progress"] + gain)
    driver["last_move"] = action
    if driver["progress"] >= FINISH_LINE:
        driver["finished"] = True
        race["finished"] = True
        race["winner_id"] = player_id
        race["winner_name"] = driver["name"]
        message += f"\n🏁 {driver['name']} crossed the finish line!"
    race["last_event"] = message
    if not race["finished"]:
        _advance_turn(race)
    return {"accepted": True, "message": message, "finished": race["finished"]}


def choose_ai_move(race, ai_id):
    ai = race["drivers"][ai_id]
    section = TRACK[race["track_index"]]
    skill = DIFFICULTY[race["difficulty"]]["ai_skill"]
    if ai["condition"] < 48 and random.random() < skill:
        return "repair"
    if section == "turn" and random.random() < (0.35 + skill * 0.5):
        return "drift"
    if section == "speed" and ai["nitro"] and random.random() < (0.35 + skill * 0.5):
        return "nitro"
    if ai["nitro"] and ai["progress"] < 700 and random.random() < skill * 0.45:
        return "nitro"
    return random.choice(["accelerate", "accelerate", "defend" if section in ("rough", "obstacle") else "accelerate"])


def track_hint(race):
    return "🔎 UPCOMING TRACK\n" + TRACK_LABELS[TRACK[race['track_index']]]


def race_board(race):
    lines = [f"🏎️ KURO STREET RUSH — {race['difficulty'].upper()} | ROUND {race['round']}",
             f"Finish line: {FINISH_LINE}m", ""]
    ranked = sorted(race["drivers"].values(), key=lambda d: d["progress"], reverse=True)
    for i, d in enumerate(ranked, 1):
        filled = min(10, int(d["progress"] / FINISH_LINE * 10))
        bar = "🟩" * filled + "⬜" * (10-filled)
        lines.append(f"{i}. {d['name']} — {d['progress']}/{FINISH_LINE}m")
        lines.append(f"{bar} 🏁")
        lines.append(f"   ❤️ Car: {d['condition']}%  |  ⚡ Nitro: {d['nitro']}/3")
    if race.get("finished"):
        lines += ["", f"🏆 WINNER: {race['winner_name']}"]
    return "\n".join(lines)
