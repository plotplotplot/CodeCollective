from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

Base = declarative_base()

def utc_now():
    """Return timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)

class Motion(Base):
    __tablename__ = "motions"

    id = Column(String, primary_key=True)
    type = Column(String, nullable=False)  # "main" or "amendment"
    parent_motion_id = Column(String, ForeignKey('motions.id'), nullable=True)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    proposed_body_diff = Column(Text, nullable=True)
    status = Column(String, nullable=False)  # "discussion", "proposed", "voting", "passed", "failed", "withdrawn"
    proposer_id = Column(String, nullable=False)
    proposer_name = Column(String, nullable=False)
    seconder_id = Column(String, nullable=True)
    seconder_name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    discussion_deadline = Column(DateTime(timezone=True), nullable=True)
    voting_deadline = Column(DateTime(timezone=True), nullable=True)
    quorum_required = Column(Integer, nullable=False, default=5)
    result = Column(JSON, nullable=True)  # {"yea": int, "nay": int, "abstain": int, "total_votes": int}

    # Relationships
    comments = relationship("Comment", back_populates="motion", cascade="all, delete-orphan")
    votes = relationship("Vote", back_populates="motion", cascade="all, delete-orphan")
    views = relationship("MotionView", back_populates="motion", cascade="all, delete-orphan")

class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    motion_id = Column(String, ForeignKey('motions.id'), nullable=False)
    user_id = Column(String, nullable=False)
    user_name = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Relationships
    motion = relationship("Motion", back_populates="comments")

class Vote(Base):
    __tablename__ = "votes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    motion_id = Column(String, ForeignKey('motions.id'), nullable=False)
    user_id = Column(String, nullable=False)
    user_name = Column(String, nullable=False)
    choice = Column(String, nullable=False)  # "yea", "nay", "abstain"
    cast_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Relationships
    motion = relationship("Motion", back_populates="votes")

class MotionView(Base):
    __tablename__ = "motion_views"

    id = Column(Integer, primary_key=True, autoincrement=True)
    motion_id = Column(String, ForeignKey('motions.id'), nullable=False)
    user_id = Column(String, nullable=False)
    viewed_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Relationships
    motion = relationship("Motion", back_populates="views")

class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    # Engagement votes: motion_id -> "up"/"down"
    engagement_votes = Column(JSON, nullable=True, default=dict)
    # Motion IDs the user has interacted with
    interacted_motion_ids = Column(JSON, nullable=True, default=list)
    # Total interactions count
    total_interactions = Column(Integer, nullable=False, default=0)
    # Preferred statuses for ranking
    preferred_statuses = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)