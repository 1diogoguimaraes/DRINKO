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
clients = []  # frontend live viewers
device_connections: Dict[str, WebSocket] = {}  # ESP32 connections

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


# ------------------------
# WebSocket endpoints
# ------------------------

@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    """Frontend clients subscribe here to receive live updates."""
    await websocket.accept()
    clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()  # keep alive
    except WebSocketDisconnect:
        clients.remove(websocket)


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
# -----------------

@app.post("/matches/", response_model=schemas.MatchInResponse)
def create_match(match: schemas.MatchInMemory, db: Session = Depends(get_db)):
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
                asyncio.create_task(device_connections[device_id].send_text(payload))
                print(f"Sent config to {device_id}: {payload}")

    return matches_memory[db_match.id]


@app.post("/matches/{match_id}/start")
async def start_match(match_id: int):
    if match_id not in matches_memory:
        raise HTTPException(status_code=404, detail="Match not found in memory")

    match = matches_memory[match_id]
    if match["status"] != "waiting":
        raise HTTPException(status_code=400, detail="Match already started or finished")

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


async def handle_device_status(device_id: str, data: dict):
    status = data.get("state")
    mode = data.get("mode")
    team = data.get("team")
    relay_pos = data.get("relay_pos")

    print(f"Status {status} from {device_id}")

    for ws in clients:
        await ws.send_text(json.dumps({
            "type": "status",
            "device_id": device_id,
            "status": status,
            "mode": mode,
            "team": team,
            "relay_pos": relay_pos
        }))


def handle_device_results(device_id: str, data: dict):
    start_weight = data.get("start_weight")
    drink_time = data.get("drink_time")
    end_weight = data.get("end_weight")

    for match_id, match_data in matches_memory.items():
        for team in match_data["teams"]:
            for player in team["players"]:
                if player["device_id"] == device_id:
                    player["time_seconds"] = drink_time
                    player["start_weight"] = start_weight
                    player["end_weight"] = end_weight
                    print(f"Updated {device_id} in match {match_id}")
                    return
    print(f"Device {device_id} not found in any active match")


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
