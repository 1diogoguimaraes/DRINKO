from sqlalchemy.orm import Session
from datetime import datetime
from . import models, schemas


def create_match(db: Session, match_type: str) -> models.Match:
    match = models.Match(match_type=match_type)
    db.add(match)
    db.commit()
    db.refresh(match)
    return match


def finalize_match(db: Session, match_data: dict, match_id: int):
    match = db.query(models.Match).filter(models.Match.id == match_id).first()
    if not match:
        return None

    for team_info in match_data["teams"]:
        team = None

        # --- TEAM HANDLING ---
        team_name = team_info.get("team_name")

        # Relay teams must have a name
        if match_data["match_type"] == "relay" and not team_name:
            raise ValueError("Relay teams must have a name")

        if team_name:
            team = db.query(models.Team).filter(models.Team.name == team_name).first()

        # Create team if not found
        if not team:
            team = models.Team(
                match_id=match_id,
                name=team_name
            )
            db.add(team)
            db.flush()  # ✅ safer than multiple commits

        # --- PLAYER HANDLING ---
        for player_info in team_info["players"]:
            player_name = player_info.get("player_name") or player_info["device_id"]

            # Try to find existing player by name
            player = db.query(models.Player).filter(models.Player.name == player_name).first()

            if not player:
                player = models.Player(
                    name=player_name,
                    team_id=team.id if team.name else None
                )
                db.add(player)
                db.flush()

            # --- RESULT HANDLING ---
            if player_info.get("time_seconds") is not None:
                result = models.Result(
                    match_id=match_id,
                    team_id=team.id if team.name else None,
                    player_id=player.id,
                    reaction_time_seconds=player_info["reaction_time_seconds"],
                    time_seconds=player_info["time_seconds"],
                    start_weight=player_info.get("start_weight"),
                    end_weight=player_info.get("end_weight"),
                    foul=player_info.get("foul"),
                    date=datetime.now().strftime("%d-%m-%Y")  # ✅ auto date
                )
                db.add(result)

    # ✅ Commit once at the end
    db.commit()
    db.refresh(match)
    return match