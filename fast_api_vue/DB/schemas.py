#schemas.py
from pydantic import BaseModel
from typing import List, Optional

# ---------- In-memory schemas ----------

class PlayerInMemory(BaseModel):
    device_id: str
    status: Optional[str] = "standby"
    player_name: Optional[str] = None
    reaction_time_seconds: Optional[float] = None
    time_seconds: Optional[float] = None
    start_weight: Optional[float] = None
    end_weight: Optional[float] = None
    foul:Optional[bool]=False

class TeamInMemory(BaseModel):
    team_name: Optional[str] = None
    finished: bool
    players: List[PlayerInMemory]

class MatchInMemory(BaseModel):
    match_type: str
    teams: List[TeamInMemory]


class MatchInResponse(MatchInMemory):
    id: int
    match_type: str
    teams: List[TeamInMemory]

    class Config:
        from_attributes = True


# ---------- Create / DB Save schemas ----------

class PlayerCreate(BaseModel):
    player_name: Optional[str] = None
    reaction_time_seconds: Optional[float] = None
    time_seconds: Optional[float] = None
    start_weight: Optional[float] = None
    end_weight: Optional[float] = None

class TeamCreate(BaseModel):
    team_name: Optional[str] = None
    players: List[PlayerCreate]

class MatchCreate(BaseModel):
    match_type: str
    teams: List[TeamCreate]

class MatchResponse(BaseModel):
    id: int
    match_type: str
    teams: List[TeamCreate]

    class Config:
        from_attributes = True
