from sqlalchemy import Column, Integer, String, Float, ForeignKey, UniqueConstraint,Boolean
from sqlalchemy.orm import relationship
from datetime import date
from .database import Base


class Match(Base):
    __tablename__ = "matches"
    id = Column(Integer, primary_key=True)
    match_type = Column(String, nullable=False)  # "solo", "1v1", "relay"

    winner_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    winner_player_id = Column(Integer, ForeignKey("players.id"), nullable=True)

    teams = relationship("Team", back_populates="match", foreign_keys="[Team.match_id]")
    results = relationship("Result", back_populates="match", cascade="all, delete-orphan")


class Team(Base):
    __tablename__ = "teams"
    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    name = Column(String, nullable=True, unique=True)  # ✅ Make name unique

    match = relationship("Match", back_populates="teams", foreign_keys=[match_id])
    players = relationship("Player", back_populates="team", cascade="all, delete-orphan")
    results = relationship("Result", back_populates="team", cascade="all, delete-orphan")


class Player(Base):
    __tablename__ = "players"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)  # ✅ Make name unique
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)

    team = relationship("Team", back_populates="players")
    results = relationship("Result", back_populates="player", cascade="all, delete-orphan")


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
    foul=Column(Boolean,nullable=False)
    date = Column(String, nullable=False)  # ✅ New field

    match = relationship("Match", back_populates="results")
    team = relationship("Team", back_populates="results")
    player = relationship("Player", back_populates="results")
