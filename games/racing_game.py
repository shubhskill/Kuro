"""Game logic for KURO Racing. Telegram UI lives in main.py."""

import random

TRACK_LENGTH = 100
MAX_STAGE = 4


def _new_driver(player_id, name, is_ai=False):
    return {
        "id": player_id,
        "name": name,
        "progress": 0,
        "moves": 0,
        "finished": False,
        "is_ai": is_ai,
        "last_event": "Ready at the starting line!",
    }


def create_solo_race(player_id, name):
    """Create a solo race against KURO's AI rival."""
    return {
        "mode": "solo",
        "track_length": TRACK_LENGTH,
        "finished": False,
        "winner_id": None,
        "winner_name": None,
        "stage": 1,
        "drivers": {
            player_id: _new_driver(player_id, name),
            "kuro_ai": _new_driver("kuro_ai", "KURO AI", is_ai=True),
        },
    }


def create_multiplayer_race(players):
    """Create a group race from lobby player records."""
    drivers = {}
    order = []
    for player in players:
        player_id = player["id"]
        drivers[player_id] = _new_driver(player_id, player["name"])
        order.append(player_id)
    return {
        "mode": "multi",
        "track_length": TRACK_LENGTH,
        "finished": False,
        "winner_id": None,
        "winner_name": None,
        "stage": 1,
        "drivers": drivers,
        "player_order": order,
    }


def _stage_for_progress(progress):
    # Every 25% of the track introduces more hazards and less predictable speed.
    return min(MAX_STAGE, max(1, progress // 25 + 1))


def _move_driver(driver, stage, is_ai=False):
    """Move a driver one time; later stages have more frequent hazards."""
    hazard_chance = min(0.42, 0.08 + (stage - 1) * 0.09)
    driver["moves"] += 1
    if random.random() < hazard_chance:
        gain = random.randint(3, 6) if not is_ai else random.randint(4, 7)
        driver["progress"] = min(TRACK_LENGTH, driver["progress"] + gain)
        driver["last_event"] = f"⚠️ A track hazard slowed the car! +{gain} m"
    else:
        gain = random.randint(9, 15) if not is_ai else random.randint(9, 13)
        driver["progress"] = min(TRACK_LENGTH, driver["progress"] + gain)
        driver["last_event"] = f"💨 Clean acceleration! +{gain} m"
    if driver["progress"] >= TRACK_LENGTH:
        driver["finished"] = True
    return gain


def advance_solo_race(race, player_id):
    """Advance the player's car, then the AI if the player hasn't won."""
    if race.get("finished"):
        return {"accepted": False, "finished": True, "event": "This race has already finished."}
    driver = race["drivers"].get(player_id)
    if not driver or driver.get("is_ai"):
        return {"accepted": False, "finished": False, "event": "This is not your race."}

    stage = _stage_for_progress(max(driver["progress"], race["drivers"]["kuro_ai"]["progress"]))
    race["stage"] = stage
    _move_driver(driver, stage)
    player_event = driver["last_event"]
    if driver["finished"]:
        race["finished"] = True
        race["winner_id"] = player_id
        race["winner_name"] = driver["name"]
        return {"accepted": True, "finished": True, "winner": driver["name"], "event": player_event}

    ai = race["drivers"]["kuro_ai"]
    ai_stage = _stage_for_progress(max(driver["progress"], ai["progress"]))
    race["stage"] = ai_stage
    _move_driver(ai, ai_stage, is_ai=True)
    if ai["finished"]:
        race["finished"] = True
        race["winner_id"] = "kuro_ai"
        race["winner_name"] = ai["name"]
        return {"accepted": True, "finished": True, "winner": ai["name"], "event": f"{player_event}\nKURO AI crossed the finish line!"}
    return {"accepted": True, "finished": False, "event": f"{player_event}\n🏎️ KURO AI moved {ai['progress']} m total."}


def advance_multiplayer_race(race, player_id):
    """Advance one multiplayer player's car by one drive action."""
    if race.get("finished"):
        return {"accepted": False, "finished": True, "event": "This race has already finished."}
    driver = race["drivers"].get(player_id)
    if not driver:
        return {"accepted": False, "finished": False, "event": "You have not joined this race."}
    if driver.get("finished"):
        return {"accepted": False, "finished": False, "event": "Your car has already crossed the finish line."}

    race["stage"] = _stage_for_progress(max(d["progress"] for d in race["drivers"].values()))
    _move_driver(driver, race["stage"])
    if driver["finished"]:
        race["finished"] = True
        race["winner_id"] = player_id
        race["winner_name"] = driver["name"]
        return {"accepted": True, "finished": True, "winner": driver["name"], "event": driver["last_event"]}
    return {"accepted": True, "finished": False, "event": driver["last_event"]}


def render_race(race, event=None):
    """Build a compact text status board for Telegram."""
    lines = [f"🏎️ KURO RACING — STAGE {race.get('stage', 1)}/{MAX_STAGE}", ""]
    for player_id, driver in race["drivers"].items():
        progress = min(TRACK_LENGTH, driver["progress"])
        filled = min(10, progress // 10)
        track = "🟩" * filled + "⬜" * (10 - filled) + " 🏁"
        lines.append(f"{driver['name']}: {progress}/{TRACK_LENGTH} m")
        lines.append(track)
        if driver.get("finished"):
            lines.append("🏁 Finished!")
        lines.append("")
    lines.append("⚙️ Progressive difficulty: hazards become more frequent as the race advances.")
    if event:
        lines.extend(["", event])
    return "\n".join(lines).strip()
