from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship
from datetime import date
from .database import Base


# ───────────────────────────────
# MATCH
# ───────────────────────────────
class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True)
    match_type = Column(String, nullable=False)  # "solo", "1v1", "relay"
    winner_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    winner_player_id = Column(Integer, ForeignKey("players.id"), nullable=True)

    # Relationships
    teams = relationship("Team", back_populates="match", cascade="all, delete-orphan")
    results = relationship("Result", back_populates="match", cascade="all, delete-orphan")
    player_team_links = relationship("PlayerTeamAssociation", back_populates="match", cascade="all, delete-orphan")


# ───────────────────────────────
# TEAM
# ───────────────────────────────
class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    name = Column(String, nullable=False)

    # Each match can have its own team names
    __table_args__ = (UniqueConstraint("match_id", "name", name="uix_team_match_name"),)

    match = relationship("Match", back_populates="teams")
    player_links = relationship("PlayerTeamAssociation", back_populates="team", cascade="all, delete-orphan")
    results = relationship("Result", back_populates="team", cascade="all, delete-orphan")


# ───────────────────────────────
# PLAYER
# ───────────────────────────────
class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)

    team_links = relationship("PlayerTeamAssociation", back_populates="player", cascade="all, delete-orphan")
    results = relationship("Result", back_populates="player", cascade="all, delete-orphan")


# ───────────────────────────────
# ASSOCIATION: Player ↔ Team ↔ Match
# ───────────────────────────────
class PlayerTeamAssociation(Base):
    __tablename__ = "player_team_associations"

    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)

    position = Column(Integer, nullable=True)  # e.g. "1", "2", "3"

    __table_args__ = (
    UniqueConstraint("match_id", "team_id", "player_id", name="uix_match_team_player"),)


    player = relationship("Player", back_populates="team_links")
    team = relationship("Team", back_populates="player_links")
    match = relationship("Match", back_populates="player_team_links")


# ───────────────────────────────
# RESULT
# ───────────────────────────────
class Result(Base):
    __tablename__ = "results"

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=True)

    reaction_time_seconds = Column(Float, nullable=False)
    time_seconds = Column(Float, nullable=False)
    start_weight = Column(Float, nullable=True)
    end_weight = Column(Float, nullable=True)
    foul = Column(Boolean, nullable=False, default=False)
    date = Column(String, nullable=False, default=lambda: str(date.today()))

    match = relationship("Match", back_populates="results")
    team = relationship("Team", back_populates="results")
    player = relationship("Player", back_populates="results")
