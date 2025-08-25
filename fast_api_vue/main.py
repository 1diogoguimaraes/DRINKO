import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session
import json
from typing import Dict, Any

from DB import crud, models, schemas
from DB.database import engine, Base, SessionLocal

Base.metadata.create_all(bind=engine)

app = FastAPI()

# Memory Stores
matches_memory: Dict[int, dict] = {}
clients_status = []  # frontend live viewers
clients_matches= []
clients_live= []

device_connections: Dict[str, WebSocket] = {}  # ESP32 connections
devices_state: Dict[str, dict] = {}


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/matches/memory")
def debug_matches_memory():
    """
    Debug endpoint: return raw in-memory matches dict.
    """
    return matches_memory

# ------------------------
# WebSocket endpoints
# ------------------------

@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    """Frontend clients subscribe here to receive live updates."""
    await websocket.accept()
    clients_status.append(websocket)
    try:
        while True:
            await websocket.receive_text()  # keep alive
    except WebSocketDisconnect:
        clients_status.remove(websocket)

@app.websocket("/ws/matches")
async def websocket_matches(websocket: WebSocket):
    await websocket.accept()
    clients_matches.append(websocket)

    # send current state immediately
    await websocket.send_text(json.dumps({
        "type": "matches_snapshot",
        "data": matches_memory
    }))

    try:
        while True:
            await websocket.receive_text()  # keep connection alive
    except WebSocketDisconnect:
        clients_matches.remove(websocket)

async def broadcast_matches():
    data = json.dumps({
        "type": "matches_update",
        "data": matches_memory
    })
    for ws in clients_matches:
        await ws.send_text(data)

async def broadcast_matches():
    data = json.dumps({
        "type": "matches_update",
        "data": matches_memory
    })
    to_remove = []
    for ws in clients_matches:
        try:
            await ws.send_text(data)
        except:
            to_remove.append(ws)
    for ws in to_remove:
        clients_matches.remove(ws)

@app.websocket("/ws/live_results")
async def websocket_live_results(websocket: WebSocket):
    await websocket.accept()
    clients_live.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        clients_live.remove(websocket)

async def broadcast_result_update():
    data = json.dumps({
        "type": "live_snapshot",
        "devices": devices_state
    })
    to_remove=[]
    for ws in clients_live:
        try:
            await ws.send_text(data)
        except:
            to_remove.append(ws)
    for ws in to_remove:
        clients_live.remove(ws)        



@app.websocket("/ws/device/{device_id}")
async def websocket_device(websocket: WebSocket, device_id: str):
    """ESP32 connects here with its device_id."""
    await websocket.accept()
    device_connections[device_id] = websocket
    print(f"Device {device_id} connected via WS")

    try:
        while True:
            message = await websocket.receive_text()
            await handle_device_message(device_id, message)
    except WebSocketDisconnect:
        print(f"Device {device_id} disconnected")
        device_connections.pop(device_id, None)

# -----------------
# API DB Endpoints
# ---------------
@app.post("/matches/", response_model=schemas.MatchInResponse)
async def create_match(match: schemas.MatchInMemory, db: Session = Depends(get_db)):
    db_match = crud.create_match(db, match.match_type)

    matches_memory[db_match.id] = match.dict(by_alias=True, exclude_unset=False)
    matches_memory[db_match.id]["id"] = db_match.id
    matches_memory[db_match.id]["status"] = "waiting"

    # Send config to ESPs (via WS)
    for team_index, team in enumerate(match.teams):
        for player_index, player in enumerate(team.players):
            device_id = player.device_id
            payload = json.dumps({
                "type": "config",
                "match_id": db_match.id,
                "match_type": db_match.match_type,
                "team": team_index,
                "position": player_index
            })
            if device_id in device_connections:
                await device_connections[device_id].send_text(payload)
                print(f"Sent config to {device_id}: {payload}")

    asyncio.create_task(broadcast_matches())

    return matches_memory[db_match.id]



@app.post("/matches/{match_id}/start")
async def start_match(match_id: int):
    if match_id not in matches_memory:
        raise HTTPException(status_code=404, detail="Match not found in memory")

    match = matches_memory[match_id]
    if match["status"] != "waiting":
        raise HTTPException(status_code=400, detail="Match already started or finished")

    # ✅ Ensure all players are READY
    not_ready = [
        p["device_id"]
        for team in match["teams"]
        for p in team["players"]
        if p.get("status") != "ready"
    ]
    if not_ready:
        raise HTTPException(
            status_code=400,
            detail=f"Not all devices are ready: {not_ready}"
        )

    match_type = match["match_type"]

    if match_type == "solo":
        await _start_solo(match_id)
    elif match_type == "1v1":
        await _start_1v1(match_id)
    elif match_type == "relay":
        await _start_relay(match_id)
    else:
        raise HTTPException(status_code=400, detail="Unknown match type")

    match["status"] = "running"
    return {"status": "started", "match_id": match_id, "match_type": match_type}


# -----------------
# Start helpers
# -----------------

async def _start_solo(match_id: int):
    player = matches_memory[match_id]["teams"][0]["players"][0]
    device_id = player["device_id"]
    if device_id in device_connections:
        await device_connections[device_id].send_text(json.dumps({"type": "start"}))


async def _start_1v1(match_id: int):
    for team in matches_memory[match_id]["teams"]:
        for player in team["players"]:
            device_id = player["device_id"]
            if device_id in device_connections:
                await device_connections[device_id].send_text(json.dumps({"type": "start"}))


async def _start_relay(match_id: int):
    for team in matches_memory[match_id]["teams"]:
        if len(team["players"]) > 0:
            first_player = team["players"][0]
            device_id = first_player["device_id"]
            if device_id in device_connections:
                await device_connections[device_id].send_text(json.dumps({
                    "type": "start",
                    "relay_pos": 0
                }))





@app.patch("/matches/{match_id}/update")
async def update_match_memory(match_id: int, match: schemas.MatchInMemory):
    if match_id not in matches_memory:
        return {"error": "Match not found in memory"}

    # Keep match_type and team/player structure updated
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
                return {"status": "updated", "match_id": match_id}

    return {"error": "Device not found in match"}



@app.post("/matches/{match_id}/finalize")
async def finalize_match(match_id: int, db: Session = Depends(get_db)):
    if match_id not in matches_memory:
        return {"error": "Match not found in memory"}

    match_data = matches_memory[match_id]
    result = crud.finalize_match(db, match_data, match_id)

    matches_memory.pop(match_id, None)
    return {"status": "finalized", "match_id": match_id, "saved": bool(result)}


# -----------------
# Handlers
# -----------------

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
        handle_device_results(device_id, data)
    elif msg_type == "relay":
        handle_match_relay(
            match_id=data.get("match"),
            team_index=data.get("team"),
            device_id=device_id
        )
    else:
        print(f"Unknown message type from {device_id}: {data}")



def handle_match_relay(match_id: int, team_index: int, device_id: str):
    match = matches_memory.get(match_id)
    if not match:
        print(f"Match {match_id} not found")
        return

    team = match["teams"][team_index]
    players = team["players"]

    current_pos = next((i for i, p in enumerate(players) if p["device_id"] == device_id), None)
    if current_pos is None:
        print(f"Device {device_id} not found in team {team_index}")
        return

    if current_pos < len(players) - 1:
        next_device_id = players[current_pos + 1]["device_id"]
        if next_device_id in device_connections:
            asyncio.create_task(device_connections[next_device_id].send_text(
                json.dumps({"type": "start", "relay_pos": current_pos + 1})
            ))
        print(f"Relay: started next device {next_device_id}")
    else:
        team["finished"] = True
        print(f"Team {team_index} finished relay in match {match_id}")

        if all(t.get("finished") for t in match["teams"]):
            match["status"] = "finished"
            team_times = [
                sum(p.get("time_seconds") or 0 for p in t["players"])
                for t in match["teams"]
            ]
            winner_index = min(range(len(team_times)), key=lambda i: team_times[i])
            match["winner_team"] = winner_index
            print(f"Match {match_id} finished! Winner: Team {winner_index}")
    

async def handle_device_status(device_id: str, data: dict):
    status = data.get("state")
    mode = data.get("mode")
    team = data.get("team")
    relay_pos = data.get("relay_pos")
    battery = data.get("battery")

    print(f"Status {status} from {device_id}")
    
    # update memory
    if device_id not in devices_state:
        devices_state[device_id] = {}
    devices_state[device_id].update({
        "status": status
    })
    await broadcast_result_update()

    # Update matches_memory with latest state
    for match_id, match_data in matches_memory.items():
        for team in match_data["teams"]:
            for player in team["players"]:
                if player["device_id"] == device_id:
                    player["status"] = status  # ✅ store status in memory
                    break

    # Broadcast to live clients
    for ws in clients_status:
        await ws.send_text(json.dumps({
            "type": "status",
            "device_id": device_id,
            "status": status,
            "mode": mode,
            "team": team,
            "relay_pos": relay_pos,
            "battery": battery
        }))



async def handle_device_results(device_id: str, data: dict):
    start_weight = data.get("start_weight")
    time_seconds = data.get("time_seconds")
    reaction_time_seconds=data.get("reaction_time_seconds")
    end_weight = data.get("end_weight")

    for match_id, match_data in matches_memory.items():
        for team in match_data["teams"]:
            for player in team["players"]:
                if player["device_id"] == device_id:
                    player["reaction_time_seconds"] = reaction_time_seconds
                    player["time_seconds"] = time_seconds
                    player["start_weight"] = start_weight
                    player["end_weight"] = end_weight
                    print(f"Updated {device_id} in match {match_id}")
                    return
    print(f"Device {device_id} not found in any active match")

    if device_id not in devices_state:
        devices_state[device_id] = {}
    devices_state[device_id].update({
        "reaction_time_seconds": reaction_time_seconds,
        "time_seconds": time_seconds,
        "start_weight": start_weight,
        "end_weight": end_weight
    })
    await broadcast_result_update()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)