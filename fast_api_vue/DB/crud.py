# crud.py (or wherever finalize_match is defined)
from sqlalchemy.orm import Session
from datetime import datetime
from . import models


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
        # Only create teams for team-based matches
        if match_data["match_type"] not in ["solo", "1v1"]:
            team_name = team_info.get("team_name")
            if not team_name:
                team_name = f"Team {team_info.get('id', 0)}"

            # Relay matches require team names
            if match_data["match_type"] == "relay" and not team_name:
                raise ValueError("Relay teams must have a name")

            # Check if team exists
            team = (
                db.query(models.Team)
                .filter(models.Team.match_id == match_id, models.Team.name == team_name)
                .first()
            )
            if not team:
                team = models.Team(match_id=match_id, name=team_name)
                db.add(team)
                db.flush()
        else:
            # For solo/1v1 matches, no team
            team = None

        # --- PLAYER HANDLING ---
        for idx, player_info in enumerate(team_info["players"], start=1):
            player_name = player_info.get("player_name") or player_info["device_id"]

            # Find or create player
            player = db.query(models.Player).filter(models.Player.name == player_name).first()
            if not player:
                player = models.Player(name=player_name)
                db.add(player)
                db.flush()

            # Link to team only if team exists
            if team:
                existing_link = (
                    db.query(models.PlayerTeamAssociation)
                    .filter_by(player_id=player.id, team_id=team.id, match_id=match_id)
                    .first()
                )
                if not existing_link:
                    link = models.PlayerTeamAssociation(
                        player_id=player.id,
                        team_id=team.id,
                        match_id=match_id,
                        position=idx,
                    )
                    db.add(link)

            # --- RESULT HANDLING ---
            if player_info.get("time_seconds") is not None:
                result = models.Result(
                    match_id=match_id,
                    team_id=team.id if team else None,
                    player_id=player.id,
                    reaction_time_seconds=player_info.get("reaction_time_seconds", 0.0),
                    time_seconds=player_info.get("time_seconds", 0.0),
                    start_weight=player_info.get("start_weight"),
                    end_weight=player_info.get("end_weight"),
                    foul=player_info.get("foul", False),
                    date=datetime.now().strftime("%d-%m-%Y"),
                )
                db.add(result)

    db.commit()
    db.refresh(match)
    return match


