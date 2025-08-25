#models.py
from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class Match(Base):
    __tablename__ = "matches"
    id = Column(Integer, primary_key=True)
    match_type = Column(String, nullable=False)  # "solo", "1v1", "relay"
    
    winner_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)   # store winner if team-based
    winner_player_id = Column(Integer, ForeignKey("players.id"), nullable=True)  # store winner if solo

    # 👇 Explicitly tell SQLAlchemy which FK to use
    teams = relationship("Team", back_populates="match", foreign_keys="Team.match_id")
    results = relationship("Result", back_populates="match")


class Team(Base):
    __tablename__ = "teams"
    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    name = Column(String, nullable=True)

    # 👇 and here too
    match = relationship("Match", back_populates="teams", foreign_keys=[match_id])
    players = relationship("Player", back_populates="team")
    results = relationship("Result", back_populates="team")



class Player(Base):
    __tablename__ = "players"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)

    team = relationship("Team", back_populates="players")
    results = relationship("Result", back_populates="player")


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

    match = relationship("Match", back_populates="results")
    team = relationship("Team", back_populates="results")
    player = relationship("Player", back_populates="results")

