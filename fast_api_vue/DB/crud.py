#crud.py
from sqlalchemy.orm import Session
from . import models,schemas


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

        # Enforce relay teams must have a name
        if match_data["match_type"] == "relay":
            if not team_info.get("team_name"):
                raise ValueError("Relay teams must have a name")
            team = db.query(models.Team).filter(
                models.Team.name == team_info["team_name"]
            ).first()

        # Create team if not found (or if solo/1v1)
        if not team:
            team = models.Team(
                match_id=match_id,
                name=team_info.get("team_name")  # could be None for solo/1v1
            )
            db.add(team)
            db.commit()
            db.refresh(team)

        for player_info in team_info["players"]:
            player = None

            if player_info.get("player_name"):
                player = db.query(models.Player).filter(
                    models.Player.name == player_info["player_name"]
                ).first()

            if not player:
                player = models.Player(
                    name=player_info.get("player_name") or player_info["device_id"],
                    team_id=team.id if team.name else None  # only link if team has a name
                )
                db.add(player)
                db.commit()
                db.refresh(player)

            # Add result if we already have a time
            if player_info.get("time_seconds") is not None:
                result = models.Result(
                    match_id=match_id,
                    team_id=team.id if team.name else None,
                    player_id=player.id,
                    reaction_time_seconds=player_info["reaction_time_seconds"],
                    time_seconds=player_info["time_seconds"],
                    start_weight=player_info.get("start_weight"),
                    end_weight=player_info.get("end_weight")
                )
                db.add(result)
                db.commit()

    db.refresh(match)
    return match



