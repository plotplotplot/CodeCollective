"""
Governance Backend API

API for Robert's Rules motions and voting with engagement features.
"""

from fastapi import FastAPI, HTTPException, Depends, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
import uuid
from datetime import datetime, timezone, timedelta
import os
import logging

from database import get_db, create_tables
from models import (
    Motion as MotionModel,
    Comment as CommentModel,
    Vote as VoteModel,
    UserProfile as UserProfileModel,
)
from config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

PIDP_BASE_URL = os.getenv("PIDP_BASE_URL", "http://localhost:8000").rstrip("/")
PIDP_AUTH_ME_URL = os.getenv("PIDP_AUTH_ME_URL", f"{PIDP_BASE_URL}/auth/me")

# FastAPI app setup
app = FastAPI(
    title="Governance Backend API",
    description="API for Robert's Rules motions and voting with engagement features",
    version="1.0.0"
)
security = HTTPBearer()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Pydantic Models (Request/Response)
# =============================================================================

class MotionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    body: str = Field(..., min_length=1)
    quorum_required: int = Field(default=5, ge=1)


class AmendmentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    body: str = Field(..., min_length=1)
    proposed_body_diff: str


class VoteRequest(BaseModel):
    choice: str = Field(..., pattern="^(yea|nay|abstain)$")


class CommentCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=10000)


class CommentResponse(BaseModel):
    id: str
    motion_id: str
    author_id: str
    author_name: str
    body: str
    created_at: str


class VoteResponse(BaseModel):
    score: int
    user_vote: Optional[str] = Field(None, pattern="^(up|down)$")


class VoteCountsResponse(BaseModel):
    up: int
    down: int
    score: int


class UserVoteResponse(BaseModel):
    user_vote: Optional[str] = Field(None, pattern="^(up|down)$")


class MotionVote(BaseModel):
    user_id: str
    user_name: str
    choice: str
    cast_at: str


class Motion(BaseModel):
    id: str
    type: str = Field(..., pattern="^(main|amendment)$")
    parent_motion_id: Optional[str] = None
    title: str
    body: str
    proposed_body_diff: Optional[str] = None
    status: str = Field(..., pattern="^(proposed|seconded|discussion|voting|passed|failed|tabled|withdrawn)$")
    proposer_id: str
    proposer_name: str
    seconder_id: Optional[str] = None
    seconder_name: Optional[str] = None
    created_at: str
    updated_at: str
    discussion_deadline: Optional[str] = None
    voting_deadline: Optional[str] = None
    quorum_required: int
    votes: List[MotionVote] = []
    result: Optional[Dict[str, Any]] = None
    score: int = 0


# =============================================================================
# Helper Functions
# =============================================================================

def now_iso() -> str:
    """Get current UTC time in ISO format."""
    return datetime.now(timezone.utc).isoformat()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, str]:
    """
    Authenticate user via PIdP token.
    Falls back to demo user if PIdP is unavailable.
    """
    token = credentials.credentials
    
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                PIDP_AUTH_ME_URL,
                headers={"Authorization": f"Bearer {token}"},
            )
        if resp.status_code == 200:
            data = resp.json()
            return {
                "sub": str(data.get("id", token)),
                "name": data.get("full_name") 
                    or data.get("identity_data", {}).get("display_name", "User"),
            }
    except Exception as e:
        logger.warning(f"PIdP authentication failed, using demo user: {e}")
    
    return {"sub": f"user-{token[:8]}", "name": "Demo User"}


async def motion_to_response(motion: MotionModel, db: AsyncSession) -> Motion:
    """Convert a Motion database model to a Pydantic response model."""
    # Ensure votes are loaded
    if not motion.votes:
        await db.refresh(motion, ['votes'])
    
    return Motion(
        id=motion.id,
        type=motion.type,
        parent_motion_id=motion.parent_motion_id,
        title=motion.title,
        body=motion.body,
        proposed_body_diff=motion.proposed_body_diff,
        status=motion.status,
        proposer_id=motion.proposer_id,
        proposer_name=motion.proposer_name,
        seconder_id=motion.seconder_id,
        seconder_name=motion.seconder_name,
        created_at=motion.created_at.isoformat(),
        updated_at=motion.updated_at.isoformat(),
        discussion_deadline=motion.discussion_deadline.isoformat() 
            if motion.discussion_deadline else None,
        voting_deadline=motion.voting_deadline.isoformat() 
            if motion.voting_deadline else None,
        quorum_required=motion.quorum_required,
        votes=[
            MotionVote(
                user_id=v.user_id,
                user_name=v.user_name,
                choice=v.choice,
                cast_at=v.cast_at.isoformat(),
            )
            for v in motion.votes
        ],
        result=motion.result,
        score=0,
    )


async def compute_engagement_score(motion_id: str, db: AsyncSession) -> int:
    """Compute engagement score for a motion (upvotes - downvotes)."""
    result = await db.execute(select(UserProfileModel))
    profiles = result.scalars().all()
    
    score = 0
    for profile in profiles:
        if profile.engagement_votes and motion_id in profile.engagement_votes:
            vote = profile.engagement_votes[motion_id]
            if vote == "up":
                score += 1
            elif vote == "down":
                score -= 1
    
    return score


# =============================================================================
# Seed Data
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Create database tables and seed sample data if empty."""
    from database import engine
    await create_tables()
    
    async with AsyncSession(engine) as session:
        # Check if we need to seed data
        result = await session.execute(
            select(func.count()).select_from(MotionModel)
        )
        count = result.scalar()
        
        if count > 0:
            logger.info("Database already seeded, skipping")
            return
        
        logger.info("Seeding database with sample data")
        now = datetime.now(timezone.utc)
        
        # Motion 1: discussion
        m1 = MotionModel(
            id="mot-ranked-choice",
            type="main",
            parent_motion_id=None,
            title="Adopt Ranked-Choice Voting for Board Elections",
            body=(
                "Proposal to implement ranked-choice voting (RCV) for all future board elections. "
                "Under RCV, voters rank candidates in order of preference, and votes are redistributed "
                "in rounds until a candidate achieves a majority."
            ),
            proposed_body_diff=None,
            status="discussion",
            proposer_id="user-alice",
            proposer_name="Alice Johnson",
            seconder_id="user-bob",
            seconder_name="Bob Smith",
            created_at=(now - timedelta(days=3)),
            updated_at=(now - timedelta(days=2)),
            discussion_deadline=(now + timedelta(days=4)),
            voting_deadline=None,
            quorum_required=5,
            result=None,
        )
        
        # Motion 2: proposed
        m2 = MotionModel(
            id="mot-park-fund",
            type="main",
            parent_motion_id=None,
            title="Allocate Community Fund for Park Restoration",
            body="Motion to allocate $50,000 from the community development fund toward park restoration.",
            proposed_body_diff=None,
            status="proposed",
            proposer_id="user-carlos",
            proposer_name="Carlos Rivera",
            seconder_id=None,
            seconder_name=None,
            created_at=(now - timedelta(days=1)),
            updated_at=(now - timedelta(days=1)),
            discussion_deadline=None,
            voting_deadline=None,
            quorum_required=5,
            result=None,
        )
        
        # Motion 3: passed
        m3 = MotionModel(
            id="mot-annual-budget",
            type="main",
            parent_motion_id=None,
            title="Approve Annual Budget Report for Fiscal Year 2025",
            body="Motion to approve the annual budget report for fiscal year 2025.",
            proposed_body_diff=None,
            status="passed",
            proposer_id="user-diana",
            proposer_name="Diana Park",
            seconder_id="user-eli",
            seconder_name="Eli Washington",
            created_at=(now - timedelta(days=14)),
            updated_at=(now - timedelta(days=7)),
            discussion_deadline=(now - timedelta(days=10)),
            voting_deadline=(now - timedelta(days=7)),
            quorum_required=5,
            result={"yea": 5, "nay": 1, "abstain": 1, "total_votes": 7},
        )
        
        session.add_all([m1, m2, m3])
        
        # Add sample votes for motion 3
        votes = [
            VoteModel(motion_id="mot-annual-budget", user_id="user-alice", 
                   user_name="Alice Johnson", choice="yea", cast_at=(now - timedelta(days=8))),
            VoteModel(motion_id="mot-annual-budget", user_id="user-bob",
                   user_name="Bob Smith", choice="yea", cast_at=(now - timedelta(days=8))),
            VoteModel(motion_id="mot-annual-budget", user_id="user-carlos",
                   user_name="Carlos Rivera", choice="yea", cast_at=(now - timedelta(days=8))),
            VoteModel(motion_id="mot-annual-budget", user_id="user-frank",
                   user_name="Frank Lee", choice="nay", cast_at=(now - timedelta(days=7))),
            VoteModel(motion_id="mot-annual-budget", user_id="user-grace",
                   user_name="Grace Chen", choice="abstain", cast_at=(now - timedelta(days=7))),
        ]
        
        session.add_all(votes)
        await session.commit()
        logger.info("Database seeded successfully")


# =============================================================================
# Motion Endpoints
# =============================================================================

@app.get("/api/governance/motions", response_model=List[Motion])
async def list_motions(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List all motions, optionally filtered by search, status, or type."""
    query = select(MotionModel).options(
        selectinload(MotionModel.votes),
        selectinload(MotionModel.comments)
    )
    
    # Apply filters
    if status:
        query = query.where(MotionModel.status == status)
    if type:
        query = query.where(MotionModel.type == type)
    if search:
        search_lower = f"%{search.lower()}%"
        query = query.where(
            (func.lower(MotionModel.title).like(search_lower)) |
            (func.lower(MotionModel.body).like(search_lower))
        )
    
    query = query.order_by(MotionModel.created_at.desc())
    
    result = await db.execute(query)
    motions = result.scalars().all()
    
    return [await motion_to_response(motion, db) for motion in motions]


@app.post("/api/governance/motions", response_model=Motion, status_code=status.HTTP_201_CREATED)
async def propose_motion(
    motion_create: MotionCreate,
    current_user: Dict[str, str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Propose a new motion."""
    motion_id = f"mot-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    motion = MotionModel(
        id=motion_id,
        type="main",
        parent_motion_id=None,
        title=motion_create.title,
        body=motion_create.body,
        proposed_body_diff=None,
        status="proposed",
        proposer_id=current_user["sub"],
        proposer_name=current_user["name"],
        seconder_id=None,
        seconder_name=None,
        created_at=now,
        updated_at=now,
        discussion_deadline=None,
        voting_deadline=None,
        quorum_required=motion_create.quorum_required,
        result=None,
    )
    
    db.add(motion)
    await db.commit()
    await db.refresh(motion)
    
    logger.info(f"Motion created: {motion_id} by {current_user['sub']}")
    return await motion_to_response(motion, db)


@app.get("/api/governance/motions/{motion_id}", response_model=Motion)
async def get_motion(motion_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single motion by ID."""
    query = select(MotionModel).options(
        selectinload(MotionModel.votes),
        selectinload(MotionModel.comments)
    ).where(MotionModel.id == motion_id)
    
    result = await db.execute(query)
    motion = result.scalar_one_or_none()
    
    if motion is None:
        raise HTTPException(status_code=404, detail="Motion not found")
    
    return await motion_to_response(motion, db)


@app.post("/api/governance/motions/{motion_id}/second", response_model=Motion)
async def second_motion(
    motion_id: str,
    current_user: Dict[str, str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Second a motion. Only allowed if status is 'proposed' and user is not the proposer."""
    query = select(MotionModel).where(MotionModel.id == motion_id)
    result = await db.execute(query)
    motion = result.scalar_one_or_none()
    
    if motion is None:
        raise HTTPException(status_code=404, detail="Motion not found")
    if motion.status != "proposed":
        raise HTTPException(
            status_code=400,
            detail="Motion can only be seconded when in 'proposed' status"
        )
    if motion.proposer_id == current_user["sub"]:
        raise HTTPException(
            status_code=400,
            detail="Proposer cannot second their own motion"
        )
    
    motion.seconder_id = current_user["sub"]
    motion.seconder_name = current_user["name"]
    motion.status = "discussion"
    motion.updated_at = datetime.now(timezone.utc)
    motion.discussion_deadline = datetime.now(timezone.utc) + timedelta(days=7)
    
    await db.commit()
    await db.refresh(motion)
    
    logger.info(f"Motion seconded: {motion_id} by {current_user['sub']}")
    return await motion_to_response(motion, db)


@app.post("/api/governance/motions/{motion_id}/vote", response_model=Motion)
async def cast_vote(
    motion_id: str,
    vote_request: VoteRequest,
    current_user: Dict[str, str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cast a formal vote on a motion. Only allowed if status is 'voting'."""
    query = select(MotionModel).options(
        selectinload(MotionModel.votes)
    ).where(MotionModel.id == motion_id)
    
    result = await db.execute(query)
    motion = result.scalar_one_or_none()
    
    if motion is None:
        raise HTTPException(status_code=404, detail="Motion not found")
    if motion.status != "voting":
        raise HTTPException(status_code=400, detail="Voting is not open for this motion")
    
    # Check if user already voted
    for v in motion.votes:
        if v.user_id == current_user["sub"]:
            raise HTTPException(status_code=400, detail="User has already voted")
    
    vote = VoteModel(
        motion_id=motion_id,
        user_id=current_user["sub"],
        user_name=current_user["name"],
        choice=vote_request.choice,
        cast_at=datetime.now(timezone.utc),
    )
    db.add(vote)
    
    motion.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(motion)
    
    logger.info(f"Vote cast on motion {motion_id} by {current_user['sub']}: {vote_request.choice}")
    return await motion_to_response(motion, db)


# =============================================================================
# Engagement Endpoints
# =============================================================================

@app.post("/api/governance/motions/{motion_id}/upvote", response_model=VoteResponse)
async def upvote_motion(
    motion_id: str,
    current_user: Dict[str, str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Toggle upvote on a motion."""
    # Check if motion exists
    query = select(MotionModel).where(MotionModel.id == motion_id)
    result = await db.execute(query)
    motion = result.scalar_one_or_none()
    
    if motion is None:
        raise HTTPException(status_code=404, detail="Motion not found")
    
    user_id = current_user["sub"]
    
    # Get or create user profile
    profile_query = select(UserProfileModel).where(
        UserProfileModel.user_id == user_id
    )
    profile_result = await db.execute(profile_query)
    profile = profile_result.scalar_one_or_none()
    
    if profile is None:
        profile = UserProfileModel(
            user_id=user_id,
            name=current_user["name"],
            engagement_votes={},
            interacted_motion_ids=[],
            preferred_statuses={},
            total_interactions=0
        )
        db.add(profile)
    
    if profile.engagement_votes is None:
        profile.engagement_votes = {}
    
    current_vote = profile.engagement_votes.get(motion_id)
    
    if current_vote == "up":
        # Remove upvote (toggle off)
        del profile.engagement_votes[motion_id]
        user_vote = None
    else:
        # Add upvote
        profile.engagement_votes[motion_id] = "up"
        user_vote = "up"
        
        # Track interaction
        if motion_id not in profile.interacted_motion_ids:
            profile.interacted_motion_ids.append(motion_id)
            profile.total_interactions += 1
        
        # Track preferred status for ranking
        if profile.preferred_statuses is None:
            profile.preferred_statuses = {}
        profile.preferred_statuses[motion.status] = (
            profile.preferred_statuses.get(motion.status, 0) + 1
        )
    
    profile.updated_at = datetime.now(timezone.utc)
    await db.commit()
    
    score = await compute_engagement_score(motion_id, db)
    logger.debug(f"Upvote toggled on {motion_id} by {user_id}, new score: {score}")
    
    return VoteResponse(score=score, user_vote=user_vote)


@app.post("/api/governance/motions/{motion_id}/downvote", response_model=VoteResponse)
async def downvote_motion(
    motion_id: str,
    current_user: Dict[str, str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Toggle downvote on a motion."""
    query = select(MotionModel).where(MotionModel.id == motion_id)
    result = await db.execute(query)
    motion = result.scalar_one_or_none()
    
    if motion is None:
        raise HTTPException(status_code=404, detail="Motion not found")
    
    user_id = current_user["sub"]
    
    profile_query = select(UserProfileModel).where(
        UserProfileModel.user_id == user_id
    )
    profile_result = await db.execute(profile_query)
    profile = profile_result.scalar_one_or_none()
    
    if profile is None:
        profile = UserProfileModel(
            user_id=user_id,
            name=current_user["name"],
            engagement_votes={},
            interacted_motion_ids=[],
            preferred_statuses={},
            total_interactions=0
        )
        db.add(profile)
    
    if profile.engagement_votes is None:
        profile.engagement_votes = {}
    
    current_vote = profile.engagement_votes.get(motion_id)
    
    if current_vote == "down":
        del profile.engagement_votes[motion_id]
        user_vote = None
    else:
        profile.engagement_votes[motion_id] = "down"
        user_vote = "down"
        
        if motion_id not in profile.interacted_motion_ids:
            profile.interacted_motion_ids.append(motion_id)
            profile.total_interactions += 1
        
        if profile.preferred_statuses is None:
            profile.preferred_statuses = {}
        profile.preferred_statuses[motion.status] = (
            profile.preferred_statuses.get(motion.status, 0) + 1
        )
    
    profile.updated_at = datetime.now(timezone.utc)
    await db.commit()
    
    score = await compute_engagement_score(motion_id, db)
    logger.debug(f"Downvote toggled on {motion_id} by {user_id}, new score: {score}")
    
    return VoteResponse(score=score, user_vote=user_vote)


@app.get("/api/governance/motions/{motion_id}/user-vote", response_model=UserVoteResponse)
async def get_user_vote(
    motion_id: str,
    current_user: Dict[str, str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's engagement vote on a motion."""
    profile_query = select(UserProfileModel).where(
        UserProfileModel.user_id == current_user["sub"]
    )
    profile_result = await db.execute(profile_query)
    profile = profile_result.scalar_one_or_none()
    
    if profile is None or profile.engagement_votes is None:
        return UserVoteResponse(user_vote=None)
    
    return UserVoteResponse(user_vote=profile.engagement_votes.get(motion_id))


@app.get("/api/governance/motions/{motion_id}/vote-counts", response_model=VoteCountsResponse)
async def get_vote_counts(
    motion_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get upvote/downvote counts for a motion."""
    score = await compute_engagement_score(motion_id, db)
    
    # Count votes by iterating through profiles
    result = await db.execute(select(UserProfileModel))
    profiles = result.scalars().all()
    
    up = 0
    down = 0
    for profile in profiles:
        if profile.engagement_votes and motion_id in profile.engagement_votes:
            if profile.engagement_votes[motion_id] == "up":
                up += 1
            elif profile.engagement_votes[motion_id] == "down":
                down += 1
    
    return VoteCountsResponse(up=up, down=down, score=score)


@app.get("/api/governance/motions/{motion_id}/comments", response_model=List[CommentResponse])
async def list_comments(motion_id: str, db: AsyncSession = Depends(get_db)):
    """List comments for a motion, sorted by creation time ascending."""
    query = select(CommentModel).where(
        CommentModel.motion_id == motion_id
    ).order_by(CommentModel.created_at.asc())
    
    result = await db.execute(query)
    comments = result.scalars().all()
    
    return [
        CommentResponse(
            id=str(comment.id),
            motion_id=comment.motion_id,
            author_id=comment.user_id,
            author_name=comment.user_name,
            body=comment.body,
            created_at=comment.created_at.isoformat(),
        )
        for comment in comments
    ]


@app.post("/api/governance/motions/{motion_id}/comments", 
          response_model=CommentResponse,
          status_code=status.HTTP_201_CREATED)
async def add_comment(
    motion_id: str,
    comment_create: CommentCreate,
    current_user: Dict[str, str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a comment to a motion."""
    # Check if motion exists
    query = select(MotionModel).where(MotionModel.id == motion_id)
    result = await db.execute(query)
    motion = result.scalar_one_or_none()
    
    if motion is None:
        raise HTTPException(status_code=404, detail="Motion not found")
    
    comment = CommentModel(
        motion_id=motion_id,
        user_id=current_user["sub"],
        user_name=current_user["name"],
        body=comment_create.body,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    
    logger.info(f"Comment added to {motion_id} by {current_user['sub']}")
    
    return CommentResponse(
        id=str(comment.id),
        motion_id=comment.motion_id,
        author_id=comment.user_id,
        author_name=comment.user_name,
        body=comment.body,
        created_at=comment.created_at.isoformat(),
    )


# =============================================================================
# Health Check
# =============================================================================

@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint."""
    try:
        await db.execute(select(func.count()).select_from(MotionModel))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Database connection failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8002,
        reload=True,
        reload_dirs=[os.path.dirname(__file__)],
    )
