import asyncio
import random
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import json
from typing import Dict, Any

from DB import crud, models, schemas
from DB.database import engine, Base, SessionLocal,get_db
from routers import data

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(data.router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Memory Stores
matches_memory: Dict[int, dict] = {}            # whole match structures (control + public)
device_connections: Dict[str, WebSocket] = {}   # ESP32 sockets (backend <-> device)
devices_state: Dict[str, dict] = {}             # latest telemetry per device (for live UI)

# WebSocket client registries (frontend)
clients_matches = []  # control & public subscribers of matches
clients_live = []     # control & public subscribers of live device data

device_registry = {
    "ESP-001": {"mac": "84:1F:E8:16:89:08"},
    "ESP-002": {"mac": "84:1F:E8:17:2E:44"},
    "ESP-003": {"mac": "84:1F:E8:1A:B2:F8"},
    "ESP-004": {"mac": "84:1F:E8:16:82:A8"},
    "ESP-005": {"mac": "84:1F:E8:1B:3B:68"},
    "ESP-006": {"mac": "6C:C8:40:5D:4E:8C"},
    "ESP-007": {"mac": "44:1D:64:E3:34:E0"},
    "ESP-008": {"mac": "6C:C8:40:5C:67:18"},
    "ESP-009": {"mac": "6C:C8:40:5D:1A:00"},
    "ESP-010": {"mac": "44:1D:64:E3:C9:40"},
    # ... all your 10 devices
}




@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/matches/memory")
def debug_matches_memory():
    return matches_memory

@app.get("/devices")
def debug_devices_connections():
    return device_connections

# ========================
# WS: MATCHES (snapshots + updates)
# ========================
@app.websocket("/ws/matches")
async def websocket_matches(websocket: WebSocket):
    await websocket.accept()
    clients_matches.append(websocket)

    # Send current snapshot immediately
    await _safe_send(websocket, {
        "type": "matches_snapshot",
        "data": matches_memory
    })

    try:
        # keep-alive (ignore incoming)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        _safe_remove(clients_matches, websocket)


async def broadcast_matches():
    """Broadcast the whole matches_memory to all /ws/matches clients."""
    await _broadcast(clients_matches, {
        "type": "matches_update",
        "data": matches_memory
    })

# ========================
# WS: LIVE DEVICES (snapshots + updates)
# ========================
@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    await websocket.accept()
    clients_live.append(websocket)

    # Send devices snapshot immediately
    await _safe_send(websocket, {
        "type": "devices_snapshot",
        "devices": devices_state
    })

    try:
        # keep-alive (ignore incoming)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        _safe_remove(clients_live, websocket)


async def broadcast_live_event(event: dict):
    """Broadcast a single live event (status/result) to all /ws/live clients."""
    await _broadcast(clients_live, event)    


# ========================
# Utility: safe broadcast helpers
# ========================
async def _broadcast(client_list, payload: dict):
    """Send the same JSON to all sockets, removing any dead ones."""
    data = json.dumps(payload)
    to_remove = []
    for ws in list(client_list):
        try:
            await ws.send_text(data)
        except Exception:
            to_remove.append(ws)
    for ws in to_remove:
        _safe_remove(client_list, ws)


async def _safe_send(ws: WebSocket, payload: dict):
    try:
        await ws.send_text(json.dumps(payload))
    except Exception:
        pass  # caller handles removal if needed


def _safe_remove(client_list, ws: WebSocket):
    try:
        client_list.remove(ws)
    except ValueError:
        pass


# ========================
# WS: DEVICE connections
# ========================
import traceback

@app.websocket("/ws/device/{device_id}")
async def websocket_device(websocket: WebSocket, device_id: str):
    # 1. Force close old connection to prevent ghosts
    if device_id in device_connections:
        try:
            await device_connections[device_id].close()
        except:
            pass
        device_connections.pop(device_id, None)

    await websocket.accept()
    device_connections[device_id] = websocket
    print(f"Device {device_id} connected via WS")

    # 2. Restore Config & State
    device_restored = False
    
    for match_id, match in matches_memory.items():
        # Optional: Skip finished matches to prevent rejoining old ones
        if match.get("status") == "finished":
            continue

        for team_index, team in enumerate(match["teams"]):
            for relay_pos, player in enumerate(team["players"]):
                if player["device_id"] == device_id:
                    
                    # A. Send Configuration
                    players = team["players"]
                    next_device_mac = None
                    if relay_pos < len(players) - 1:
                        next_device_id = players[relay_pos + 1]["device_id"]
                        next_device_mac = device_registry.get(next_device_id, {}).get("mac")

                    await _safe_send(websocket, {
                        "type": "config",
                        "match_id": match_id,
                        "match_type": match["match_type"],
                        "team": team_index,
                        "position": relay_pos,
                        "next_device": next_device_mac
                    })

                    match_status = match.get("status", "waiting")
                    
                    # B. Restore Previous Results (if device finished before disconnect)
                    if player.get("time_seconds") is not None:
                        await _safe_send(websocket, {
                            "type": "restore_results",
                            "start_weight": player.get("start_weight", 0),
                            "end_weight": player.get("end_weight", 0),
                            "time_seconds": player.get("time_seconds", 0),
                            "reaction_time_seconds": player.get("reaction_time_seconds", 0),
                            "foul": player.get("foul", False)
                        })

                    # C. Restore Active Game State
                    elif match_status == "running":
                        print(f"Restoring {device_id} to RUNNING match {match_id}")
                        if player.get("start_weight"):
                            await _safe_send(websocket, {
                                "type": "restore_weight",
                                "start_weight": player["start_weight"]
                            })

                        # Force Lock AND Start
                        # We send both to ensure device transitions READY -> LOCKED -> START
                        await _safe_send(websocket, {"type": "game_ready", "match_id": match_id})
                        await _safe_send(websocket, {"type": "start"})
                    
                    # D. Restore Waiting State (Device was ready, now reconnects)
                    elif match_status == "waiting":
                        # If the match was already flagged as ready (all players were present), re-send lock
                        if match.get("game_ready", False):
                             await _safe_send(websocket, {"type": "game_ready", "match_id": match_id})

                    device_restored = True
                    break
            if device_restored: break
        if device_restored: break

    try:
        while True:
            # ... (keep existing message handling loop) ...
            try:
                text = await websocket.receive_text()
                await handle_device_message(device_id, text)
            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"Error handling message from {device_id}: {e}")
                break
    finally:
        print(f"[DISCONNECT] Cleaning up {device_id}")
        device_connections.pop(device_id, None)
        devices_state.pop(device_id, None)
        
        # Mark as disconnected in memory
        for match_id, match_data in matches_memory.items():
            for team in match_data["teams"]:
                for player in team["players"]:
                    if player["device_id"] == device_id:
                        player["status"] = "disconnected"
        
        asyncio.create_task(broadcast_live_event({
            "type": "status",
            "device_id": device_id,
            "status": "disconnected"
        }))
        asyncio.create_task(broadcast_matches())










# ========================
# REST: matches
# ========================
@app.post("/devices/reset")
async def reset_all_devices():
    """Send {"type": "reset"} to all connected devices, regardless of match."""
    if not device_connections:
        return {"status": "no_devices_connected"}

    for dev_id, ws in device_connections.items():
        asyncio.create_task(_safe_send(ws, {"type": "reset"}))
        print(f"[RESET] Sent reset to {dev_id}")

    return {"status": "reset_sent", "device_count": len(device_connections)}

@app.post("/matches/reset")
async def reset_all_matches():
    """Delete all matches from memory and notify devices."""
    for match in matches_memory.values():
        for team in match["teams"]:
            for player in team["players"]:
                dev_id = player["device_id"]
                if dev_id in device_connections:
                    await _safe_send(device_connections[dev_id], {"type": "reset"})
    
    matches_memory.clear()  # <-- This deletes everything in memory
    devices_state.clear()   # Clear live device states too
    asyncio.create_task(broadcast_matches())  # Notify frontend
    
    return {"status": "all_matches_deleted"}

# -----------------
# Delete a single match
# -----------------
@app.delete("/matches/{match_id}")
async def delete_match(match_id: int):
    match = matches_memory.get(match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found in memory")

    # Notify devices in this match to reset
    for team in match["teams"]:
        for player in team["players"]:
            dev_id = player["device_id"]
            if dev_id in device_connections:
                await _safe_send(device_connections[dev_id], {"type": "reset"})

    # Remove match from memory
    matches_memory.pop(match_id, None)

    # Notify frontend
    asyncio.create_task(broadcast_matches())
    return {"status": "deleted", "match_id": match_id}


# -----------------
# Resend match config to devices
# -----------------
@app.post("/matches/{match_id}/resend")
async def resend_match(match_id: int):
    match = matches_memory.get(match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found in memory")

    # Resend config to each device in the match
    for team_index, team in enumerate(match["teams"]):
        for player_index, player in enumerate(team["players"]):
            dev_id = player["device_id"]
            if dev_id in device_connections:
                next_device_mac = None
                if match["match_type"] == "relay" and player_index < len(team["players"]) - 1:
                    next_device_id = team["players"][player_index + 1]["device_id"]
                    next_device_mac = device_registry.get(next_device_id, {}).get("mac")

                payload = {
                    "type": "config",
                    "match_id": match_id,
                    "match_type": match["match_type"],
                    "team": team_index,
                    "position": player_index,
                    "next_device": next_device_mac
                }
                await _safe_send(device_connections[dev_id], payload)

    return {"status": "resent", "match_id": match_id}


@app.post("/matches/", response_model=schemas.MatchInResponse)
async def create_match(match: schemas.MatchInMemory, db: Session = Depends(get_db)):
    db_match = crud.create_match(db, match.match_type)

    matches_memory[db_match.id] = match.dict(by_alias=True, exclude_unset=False)
    matches_memory[db_match.id]["id"] = db_match.id
    matches_memory[db_match.id]["status"] = "waiting"

    # Send config to connected devices
    for team_index, team in enumerate(match.teams):
        for player_index, player in enumerate(team.players):
            dev_id = player.device_id

            # 🔹 Get the next device MAC if relay and not last player
            next_device_mac = None
            if match.match_type in ["relay", "solo_relay"] and player_index < len(team.players) - 1:
                next_device_id = team.players[player_index + 1].device_id
                # 🔹 Look up its MAC address
                next_device_mac = device_registry.get(next_device_id, {}).get("mac")

            payload = {
                "type": "config",
                "match_id": db_match.id,
                "match_type": db_match.match_type,
                "team": team_index,
                "position": player_index,
                "next_device": next_device_mac  # <-- MAC instead of string ID
            }

            if dev_id in device_connections:
                await _safe_send(device_connections[dev_id], payload)
                print(f"Sent config to {dev_id}: {payload}")

    # Notify UI
    asyncio.create_task(broadcast_matches())
    return matches_memory[db_match.id]




@app.post("/matches/{match_id}/start")
async def start_match(match_id: int):
    if match_id not in matches_memory:
        raise HTTPException(status_code=404, detail="Match not found in memory")

    match = matches_memory[match_id]
    if match["status"] != "waiting":
        raise HTTPException(status_code=400, detail="Match already started or finished")

    # Ensure all players are READY
    not_ready = [
        p["device_id"]
        for team in match["teams"]
        for p in team["players"]
        if p.get("status") != "locked"
    ]
    if not_ready:
        raise HTTPException(status_code=400, detail=f"Not all devices are ready: {not_ready}")

    match_type = match["match_type"]
    if match_type == "solo":
        await _start_solo(match_id)
    elif match_type == "1v1":
        await _start_1v1(match_id)
    elif match_type == "relay":
        await _start_relay(match_id)
    elif match_type == "solo_relay":
        await _start_solo_relay(match_id)

    else:
        raise HTTPException(status_code=400, detail="Unknown match type")

    match["status"] = "running"
    asyncio.create_task(broadcast_matches())
    return {"status": "started", "match_id": match_id, "match_type": match_type}


# -----------------
# Start helpers
# -----------------

async def _start_solo(match_id: int):
    player = matches_memory[match_id]["teams"][0]["players"][0]
    dev_id = player["device_id"]
    if dev_id in device_connections:
        await _safe_send(device_connections[dev_id], {"type": "start"})


async def _start_1v1(match_id: int):
    for team in matches_memory[match_id]["teams"]:
        for player in team["players"]:
            dev_id = player["device_id"]
            if dev_id in device_connections:
                await _safe_send(device_connections[dev_id], {"type": "start"})


async def _start_relay(match_id: int):
    match = matches_memory[match_id]

    for team_index, team in enumerate(match["teams"]):
        players = team["players"]
        if not players:
            continue

        for relay_pos, player in enumerate(players):
            dev_id = player["device_id"]
            if dev_id not in device_connections:
                continue

            if relay_pos == 0:
                # 🔹 First player starts
                await _safe_send(device_connections[dev_id], {
                    "type": "start",
                    "relay_pos": relay_pos,
                    "team": team_index,
                    "match_id": match_id
                })
            else:
                # 🔹 Other players know relay already running
                await _safe_send(device_connections[dev_id], {
                    "type": "in_relay",
                    "relay_pos": relay_pos,
                    "team": team_index,
                    "match_id": match_id
                })

    print(f"[Relay] Match {match_id} started, all players notified")

async def _start_solo_relay(match_id: int):
    match = matches_memory[match_id]
    team = match["teams"][0]
    players = team["players"]

    for relay_pos, player in enumerate(players):
        dev_id = player["device_id"]
        if dev_id not in device_connections:
            continue

        if relay_pos == 0:
            # First device starts
            await _safe_send(device_connections[dev_id], {
                "type": "start",
                "relay_pos": relay_pos,
                "team": 0,
                "match_id": match_id
            })
        else:
            # Others wait in relay chain
            await _safe_send(device_connections[dev_id], {
                "type": "in_relay",
                "relay_pos": relay_pos,
                "team": 0,
                "match_id": match_id
            })

    print(f"[SoloRelay] Match {match_id} started with {len(players)} devices")





@app.patch("/matches/{match_id}/update")
async def update_match_memory(match_id: int, match: schemas.MatchInMemory):
    if match_id not in matches_memory:
        return {"error": "Match not found in memory"}

    matches_memory[match_id]["match_type"] = match.match_type
    matches_memory[match_id]["teams"] = [team.dict() for team in match.teams]

    asyncio.create_task(broadcast_matches())
    return matches_memory[match_id]


@app.patch("/matches/{match_id}/update_player_time")
async def update_player_time(match_id: int, device_id: str, time_seconds: float):
    if match_id not in matches_memory:
        return {"error": "Match not found in memory"}

    for team in matches_memory[match_id]["teams"]:
        for player in team["players"]:
            if player["device_id"] == device_id:
                player["time_seconds"] = time_seconds
                asyncio.create_task(broadcast_matches())
                return {"status": "updated", "match_id": match_id}

    return {"error": "Device not found in match"}



@app.post("/matches/{match_id}/finalize")
async def finalize_match(match_id: int, db: Session = Depends(get_db)):
    if match_id not in matches_memory:
        return {"error": "Match not found in memory"}

    match_data = matches_memory[match_id]
    result = crud.finalize_match(db, match_data, match_id)

    # 🔹 Broadcast reset to all devices in this match
    for team in match_data["teams"]:
        for player in team["players"]:
            dev_id = player["device_id"]
            if dev_id in device_connections:
                asyncio.create_task(_safe_send(
                    device_connections[dev_id],
                    {"type": "reset"}
                ))

    matches_memory.pop(match_id, None)
    asyncio.create_task(broadcast_matches())
    return {"status": "finalized", "match_id": match_id, "saved": bool(result)}



# -----------------
# Handlers
# -----------------

# ========================
# Device message handlers
# ========================
async def handle_device_message(device_id: str, message: str):
    try:
        data = json.loads(message)
    except Exception:
        print(f"Invalid JSON from {device_id}: {message}")
        return

    msg_type = data.get("type")
    if msg_type == "status":
        await handle_device_status(device_id, data)
    elif msg_type == "results":
        await handle_device_results(device_id, data)
    elif msg_type == "weight":
        value = data.get("weight")
        if value is not None:
            await handle_device_weight(device_id, float(value))    
    elif msg_type == "relay_done":
        await handle_match_relay(
            match_id=data.get("match_id"),
            team_index=data.get("team"),
            relay_pos=data.get("position")
        )
    else:
        print(f"Unknown message type from {device_id}: {data}")
    asyncio.create_task(broadcast_matches())



STANDARD_WEIGHT = 1000  # example, adjust to your rule

def _calculate_team_results(team: dict) -> dict:
    time_sum = sum((p.get("time_seconds") or 0) for p in team["players"] if not p.get("foul"))
    weight_sum = sum((p.get("end_weight") or 0) for p in team["players"] if not p.get("foul"))
    return {"time": time_sum, "weight": weight_sum}



async def handle_match_relay(match_id: int, team_index: int, relay_pos: int):
    match = matches_memory.get(match_id)
    if not match:
        print(f"[Relay] Match {match_id} not found")
        return
    
    match_type = match["match_type"]
    if match_type not in ["relay", "solo_relay"]:
        print(f"[Relay] Ignored relay_done for non-relay type {match_type}")
        return

    team = match["teams"][team_index]
    players = team["players"]

    # 🔹 Validate position
    if relay_pos < 0 or relay_pos >= len(players):
        print(f"[Relay] Invalid relay_pos {relay_pos} for team {team_index}")
        return

    # 🔹 Last player finished → team done
    if relay_pos == len(players) - 1:
        team["finished"] = True
        print(f"[Relay] Team {team_index} finished relay in match {match_id}")

        # 🎉 Victory animation for the finishing team
        for player in team["players"]:
            did = player["device_id"]
            if did in device_connections:
                asyncio.create_task(_safe_send(
                    device_connections[did],
                    {"type": "victory", "team": team_index}
                ))

        if all(t.get("finished") for t in match["teams"]):
            results = [_calculate_team_results(t) for t in match["teams"]]

            if match_type == "solo_relay":
                # Just mark finished, no competition between teams
                match["status"] = "finished"
                match["winner_team"] = 0
                print(f"[SoloRelay] Match {match_id} finished (one-team relay)")
            else:
                # Normal relay winner logic
                winners = [i for i, r in enumerate(results) if r["weight"] >= STANDARD_WEIGHT]
                if not winners:
                    match["status"] = "finished"
                    match["winner_team"] = None
                    print(f"[Relay] Match {match_id} finished → no winners")
                elif len(winners) == 1:
                    match["status"] = "finished"
                    match["winner_team"] = winners[0]
                    print(f"[Relay] Match {match_id} finished → winner team {winners[0]} (only team above weight)")
                else:
                    winner_index = min(winners, key=lambda i: results[i]["time"])
                    match["status"] = "finished"
                    match["winner_team"] = winner_index
                    print(f"[Relay] Match {match_id} finished → winner team {winner_index} (fastest valid team)")


            # 📢 Notify all devices about match end
            for t_index, t in enumerate(match["teams"]):
                for player in t["players"]:
                    did = player["device_id"]
                    if did in device_connections:
                        asyncio.create_task(_safe_send(
                            device_connections[did],
                            {
                                "type": "match_end",
                                "winner_team": match["winner_team"],
                                "your_team": t_index,
                                "match_id": match_id
                            }
                        ))





async def handle_match_1v1_finish(match_id: int):
    match = matches_memory.get(match_id)
    if not match:
        print(f"[1v1] Match {match_id} not found")
        return

    if match["status"] == "finished":
        return  # already handled

    teams = match["teams"]
    if len(teams) != 2:
        print(f"[1v1] Match {match_id} invalid team count: {len(teams)}")
        return

    # Collect results
    results = []
    for team in teams:
        player = team["players"][0]  # 1 player per team in 1v1
        time_val = player.get("time_seconds")
        foul = player.get("foul", False)
        results.append({
            "device_id": player["device_id"],
            "time": time_val,
            "foul": foul,
        })

    # Ensure both players have submitted results
    if any(r["time"] is None for r in results):
        return

    # Winner logic
    if results[0]["foul"] and results[1]["foul"]:
        winner = None
    elif results[0]["foul"]:
        winner = 1
    elif results[1]["foul"]:
        winner = 0
    else:
        winner = 0 if results[0]["time"] < results[1]["time"] else 1

    match["status"] = "finished"
    match["winner_team"] = winner

    # Notify devices
    for t_index, team in enumerate(teams):
        for player in team["players"]:
            dev_id = player["device_id"]
            if dev_id in device_connections:
                await _safe_send(device_connections[dev_id], {
                    "type": "match_end",
                    "match_id": match_id,
                    "your_team": t_index,
                    "winner_team": winner
                })

    asyncio.create_task(broadcast_matches())
    print(f"[1v1] Match {match_id} finished → winner {winner}")


async def handle_match_solo_finish(match_id: int):
    match = matches_memory.get(match_id)
    if not match:
        print(f"[SOLO] Match {match_id} not found")
        return

    if match["status"] == "finished":
        return  # already handled

    team = match["teams"][0]
    player = team["players"][0]

    # Ensure we have result data
    if player.get("time_seconds") is None:
        print(f"[SOLO] Player for match {match_id} has no result yet")
        return

    # Mark match finished
    match["status"] = "finished"
    match["winner_team"] = 0  # Only one team, always "winner"

    if player.get("foul"):
        device_winning=1
    else:
        device_winning=0
    # Notify the single device
    dev_id = player["device_id"]
    if dev_id in device_connections:
        await _safe_send(device_connections[dev_id], {
            "type": "match_end",
            "match_id": match_id,
            "your_team": device_winning,
            "winner_team": 0
        })

    asyncio.create_task(broadcast_matches())
    print(f"[SOLO] Match {match_id} finished → device {dev_id}")


async def handle_device_weight(device_id: str, weight: float):
    """Update player's start_weight from a device and broadcast change."""
    updated = False
    for match_id, match_data in matches_memory.items():
        for team in match_data["teams"]:
            for player in team["players"]:
                if player["device_id"] == device_id:
                    player["start_weight"] = weight
                    updated = True
                    print(f"[WEIGHT] {device_id} start_weight updated to {weight} in match {match_id}")

    # also mirror in device_state
    devices_state.setdefault(device_id, {})
    devices_state[device_id]["start_weight"] = weight

    if updated:
        asyncio.create_task(broadcast_matches())
        await broadcast_live_event({
            "type": "weight",
            "device_id": device_id,
            "start_weight": weight
        })

def _check_all_devices_ready(match_id: int) -> bool:
    """Return True if all devices are 'ready' OR already 'locked'."""
    match = matches_memory.get(match_id)
    if not match:
        return False

    for team in match["teams"]:
        for player in team["players"]:
            # Allow 'locked' because other devices might already be waiting
            if player.get("status") not in ["ready", "locked"]:
                return False
    return True

async def handle_device_status(device_id: str, data: dict):
    # normalize incoming fields
    status = data.get("state")
    match_id=data.get("match_id")
    mode = data.get("mode")
    team = data.get("team")
    relay_pos = data.get("relay_pos")
    battery = data.get("battery")

    #print(f"[LIVE] status {status} from {device_id}")

    # Update device cache with full info
    devices_state.setdefault(device_id, {})
    devices_state[device_id].update({
        "status": status,
        "match_id":match_id,
        "mode": mode,
        "team": team,
        "relay_pos": relay_pos,
        "battery": battery,
    })

    # Mirror status into matches_memory players if present
    for _match_id, match_data in matches_memory.items():
        for t in match_data["teams"]:
            for p in t["players"]:
                if p["device_id"] == device_id:
                    p["status"] = status

# ✅ Check if all players in this match are ready
    if status == "ready" and match_id in matches_memory:
        if _check_all_devices_ready(match_id):
            matches_memory[match_id]["game_ready"] = True
            print(f"Match {match_id} is now READY (all devices).")

            # Optionally notify all devices in the match
            for team in matches_memory[match_id]["teams"]:
                for player in team["players"]:
                    dev_id = player["device_id"]
                    if dev_id in device_connections:
                        await _safe_send(device_connections[dev_id], {
                            "type": "game_ready",
                            "match_id": match_id
                        })

    # Broadcast to live channel
    await broadcast_live_event({
        "type": "status",
        "device_id": device_id,
        "status": status,
        "match_id":match_id,
        "mode": mode,
        "team": team,
        "relay_pos": relay_pos,
        "battery": battery,
    })


async def handle_device_results(device_id: str, data: dict):
    start_weight = data.get("start_weight")
    time_seconds = data.get("time_seconds")
    reaction_time_seconds = data.get("reaction_time_seconds")
    end_weight = data.get("end_weight")
    foul = data.get("foul", False)
    updated = False
    match_id = None

    for _match_id, match_data in matches_memory.items():
        for team in match_data["teams"]:
            for player in team["players"]:
                if player["device_id"] == device_id:
                    player["reaction_time_seconds"] = reaction_time_seconds
                    player["time_seconds"] = time_seconds
                    player["start_weight"] = start_weight
                    player["end_weight"] = end_weight
                    player["foul"] = foul
                    updated = True
                    match_id = _match_id

    if not updated:
        print(f"Device {device_id} not found in any active match (storing in devices_state)")

    # Store latest results in live cache too
    devices_state.setdefault(device_id, {})
    devices_state[device_id].update({
        "reaction_time_seconds": reaction_time_seconds,
        "time_seconds": time_seconds,
        "start_weight": start_weight,
        "end_weight": end_weight
    })

    # Broadcast to live channel (public animations can react)
    await broadcast_live_event({
        "type": "result",
        "device_id": device_id,
        "reaction_time_seconds": reaction_time_seconds,
        "time_seconds": time_seconds,
        "start_weight": start_weight,
        "end_weight": end_weight
    })

    if updated:
        asyncio.create_task(broadcast_matches())

                # 🔹 Call handler depending on match type
        match = matches_memory.get(match_id)
        if not match:
            return

        if match["match_type"] == "1v1":
            await handle_match_1v1_finish(match_id)
        elif match["match_type"] == "solo":
            await handle_match_solo_finish(match_id)
        elif match["match_type"] in ["relay", "solo_relay"]:
            # (Relay finishes are handled separately by relay_done messages)
            pass



# ========================
# Dev helper: Fake live feed
# ========================
async def fake_status_broadcaster():
    """Send fake status messages every 2 seconds for testing frontend."""
    device_ids = ["ESP32-1", "ESP32-2", "ESP32-3","ESP32-4", "ESP32-5", "ESP32-6","ESP32-7", "ESP32-8", "ESP32-9", "ESP32-10"]
    statuses = ["standby", "ready", "start", "drinking", "finish"]
    modes=["relay","solo","1v1"]

    while True:
        if clients_live:  # only send if someone is listening
            device_id = random.choice(device_ids)
            payload = {
                "type": "status",
                "device_id": device_id,
                "state": random.choice(statuses),   # note: incoming uses 'state'
                "match_id": random.randint(1, 800),
                "mode": random.choice(modes),
                "team": random.choice(["red", "blue"]),
                "relay_pos": random.randint(1, 4),
                "battery": round(random.uniform(3.5, 4.2), 2)
            }
            # Reuse real handler to keep one code path
            await handle_device_status(device_id, payload)
        await asyncio.sleep(2)


import asyncio
import json

# Example pool of device IDs
FAKE_DEVICES = [f"ESP-{i:03d}" for i in range(1, 11)]

# Fixed config for testing
DEVICE_CONFIG = {
    "ESP-001": {"mode": "relay", "team": 0, "relay_pos": 0},
    "ESP-002": {"mode": "relay", "team": 0, "relay_pos": 1},
    "ESP-003": {"mode": "relay", "team": 1, "relay_pos": 0},
    "ESP-004": {"mode": "relay", "team": 1, "relay_pos": 1},
    "ESP-005": {"mode": "1v1",   "team": 0, "relay_pos": None},
    "ESP-006": {"mode": "1v1",   "team": 1, "relay_pos": None},
    "ESP-007": {"mode": "solo",  "team": 0, "relay_pos": None},
    "ESP-008": {"mode": "solo",  "team": 0, "relay_pos": None},
    "ESP-009": {"mode": "solo",  "team": 0, "relay_pos": None},
    "ESP-010": {"mode": "solo",  "team": 0, "relay_pos": None},
}

# Fixed values for repeatable test
FIXED_STATUS = "ready"
FIXED_BATTERY = 3.95
FIXED_START_WEIGHT = 980
FIXED_END_WEIGHT = 1010
FIXED_TIME = 6.50
FIXED_REACTION = 0.30
FIXED_FOUL = False

async def simulate_devices():
    """
    Simulate 10 ESP devices with fixed values, also filling matches_memory.
    """
    from main import devices_state, matches_memory, handle_device_status, handle_device_message

    match_id = 1
    # Build one fake match with teams & players
    matches_memory[match_id] = {
  "match_type": "relay",
  "teams": [
    {
      "team_name": "",
      "finished":False,
      "players": [
        {
          "device_id": "ESP-001",
          "status": "none",
          "player_name": "",
          "time_seconds": "",
          "start_weight": "",
          "end_weight": "",
          "foul": False
        },        
        {
          "device_id": "ESP-002",
          "status": "none",
          "player_name": "",
          "time_seconds": "",
          "start_weight": "",
          "end_weight": "",
          "foul": False
        }
      ]
    },{
      "team_name": "",
      "finished":False,
      "players": [
        {
          "device_id": "ESP-003",
          "status": "none",
          "player_name": "",
          "time_seconds": "",
          "start_weight": "",
          "end_weight": "",
          "foul": False
        },        
        {
          "device_id": "ESP-004",
          "status": "none",
          "player_name": "",
          "time_seconds": "",
          "start_weight": "",
          "end_weight": "",
          "foul": False
        }
      ]
    }
  ]
}


    while True:
        for dev, cfg in DEVICE_CONFIG.items():
            # 🔹 1) Status update
            status_payload = {
                "type": "status",
                "state": FIXED_STATUS,
                "match_id": match_id,
                "mode": cfg["mode"],
                "team": cfg["team"],
                "relay_pos": cfg["relay_pos"],
                "battery": FIXED_BATTERY,
            }
            await handle_device_status(dev, status_payload)

            # 🔹 2) Fake weight
            weight_payload = {"type": "weight", "value": FIXED_START_WEIGHT}
            await handle_device_message(dev, json.dumps(weight_payload))

            # 🔹 3) Fake result
            result_payload = {
                "type": "results",
                "start_weight": FIXED_START_WEIGHT,
                "end_weight": FIXED_END_WEIGHT,
                "time_seconds": FIXED_TIME,
                "reaction_time_seconds": FIXED_REACTION,
                "foul": FIXED_FOUL,
            }
            await handle_device_message(dev, json.dumps(result_payload))

            # 🔹 Keep devices_state aligned
            devices_state[dev] = {
                "status": FIXED_STATUS,
                "match_id": match_id,
                "mode": cfg["mode"],
                "team": cfg["team"],
                "relay_pos": cfg["relay_pos"],
                "battery": FIXED_BATTERY,
                "start_weight": FIXED_START_WEIGHT,
                "end_weight": FIXED_END_WEIGHT,
                "time_seconds": FIXED_TIME,
                "reaction_time_seconds": FIXED_REACTION,
                "foul": FIXED_FOUL,
            }

        await asyncio.sleep(5)  # update every 5s



@app.get("/data/{table_name}")
def get_table_data(table_name: str, db: Session = Depends(get_db)):
    mapping = {
        "matches": models.Match,
        "teams": models.Team,
        "players": models.Player,
        "results": models.Result,
    }
    model = mapping.get(table_name)
    if not model:
        raise HTTPException(status_code=404, detail="Table not found")
    
    rows = db.query(model).all()
    # Convert ORM objects to dicts
    return [serialize(r) for r in rows]


def serialize(obj):
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


# ========================
# Run
# ========================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)





