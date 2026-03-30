from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import redis
import json
import uuid
from datetime import datetime, timezone, timedelta
import os

# FastAPI app setup
app = FastAPI(title="Governance Backend API", description="API for Robert's Rules motions and voting")
security = HTTPBearer()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis setup
redis_host = os.environ.get("GOVERNANCE_REDIS_HOST", "localhost")
redis_port = int(os.environ.get("GOVERNANCE_REDIS_PORT", 6379))
redis_client = redis.Redis(host=redis_host, port=redis_port, db=0, decode_responses=True)


# --- Pydantic Models ---

class MotionCreate(BaseModel):
    title: str
    body: str
    quorum_required: int = 5

class AmendmentCreate(BaseModel):
    title: str
    body: str
    proposed_body_diff: str

class VoteRequest(BaseModel):
    choice: str  # "yea", "nay", "abstain"

class CommentCreate(BaseModel):
    body: str

class CommentResponse(BaseModel):
    id: str
    motion_id: str
    author_id: str
    author_name: str
    body: str
    created_at: str

class Motion(BaseModel):
    id: str
    type: str  # "main" or "amendment"
    parent_motion_id: Optional[str] = None
    title: str
    body: str
    proposed_body_diff: Optional[str] = None
    status: str  # proposed, seconded, discussion, voting, passed, failed, tabled, withdrawn
    proposer_id: str
    proposer_name: str
    seconder_id: Optional[str] = None
    seconder_name: Optional[str] = None
    created_at: str
    updated_at: str
    discussion_deadline: Optional[str] = None
    voting_deadline: Optional[str] = None
    quorum_required: int
    votes: list = []
    result: Optional[dict] = None
    score: int = 0


# --- Redis Key Helpers ---

def motion_key(motion_id: str) -> str:
    return f"governance:motion:{motion_id}"

def motions_sorted_set_key() -> str:
    return "governance:motions"

def amendments_key(motion_id: str) -> str:
    return f"governance:motion:{motion_id}:amendments"

def upvoters_key(motion_id: str) -> str:
    return f"governance:motion:{motion_id}:upvoters"

def downvoters_key(motion_id: str) -> str:
    return f"governance:motion:{motion_id}:downvoters"

def comments_key(motion_id: str) -> str:
    return f"governance:motion:{motion_id}:comments"


# --- Helper Functions ---

def save_motion(motion: dict) -> None:
    """Save a motion to Redis (JSON string) and add to sorted set."""
    mid = motion["id"]
    redis_client.set(motion_key(mid), json.dumps(motion))
    # Score is the created_at timestamp for ordering
    created_ts = datetime.fromisoformat(motion["created_at"]).timestamp()
    redis_client.zadd(motions_sorted_set_key(), {mid: created_ts})

def load_motion(motion_id: str) -> Optional[dict]:
    """Load a motion from Redis by ID."""
    raw = redis_client.get(motion_key(motion_id))
    if raw is None:
        return None
    return json.loads(raw)

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def compute_engagement_score(motion_id: str) -> int:
    ups = redis_client.scard(upvoters_key(motion_id))
    downs = redis_client.scard(downvoters_key(motion_id))
    return ups - downs

def motion_with_score(motion: dict) -> dict:
    """Attach the engagement score to a motion dict before returning."""
    motion["score"] = compute_engagement_score(motion["id"])
    return motion


# --- Authentication ---

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    # Try to decode with PIdP. Fallback to demo user.
    try:
        import httpx
        resp = httpx.get(
            "http://localhost:8000/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                "sub": str(data.get("id", token)),
                "name": data.get("full_name") or data.get("identity_data", {}).get("display_name", "User"),
            }
    except Exception:
        pass
    return {"sub": f"user-{token[:8]}", "name": "Demo User"}


# --- Seed Data ---

@app.on_event("startup")
async def startup_event():
    """Seed sample motions if the sorted set is empty."""
    if redis_client.zcard(motions_sorted_set_key()) > 0:
        return

    now = datetime.now(timezone.utc)

    # Motion 1: discussion
    m1 = {
        "id": "mot-ranked-choice",
        "type": "main",
        "parent_motion_id": None,
        "title": "Adopt Ranked-Choice Voting for Board Elections",
        "body": (
            "Proposal to implement ranked-choice voting (RCV) for all future board elections. "
            "Under RCV, voters rank candidates in order of preference, and votes are redistributed "
            "in rounds until a candidate achieves a majority. This system promotes consensus candidates "
            "and reduces strategic voting."
        ),
        "proposed_body_diff": None,
        "status": "discussion",
        "proposer_id": "user-alice",
        "proposer_name": "Alice Johnson",
        "seconder_id": "user-bob",
        "seconder_name": "Bob Smith",
        "created_at": (now - timedelta(days=3)).isoformat(),
        "updated_at": (now - timedelta(days=2)).isoformat(),
        "discussion_deadline": (now + timedelta(days=4)).isoformat(),
        "voting_deadline": None,
        "quorum_required": 5,
        "votes": [],
        "result": None,
    }

    # Motion 2: proposed
    m2 = {
        "id": "mot-park-fund",
        "type": "main",
        "parent_motion_id": None,
        "title": "Allocate Community Fund for Park Restoration",
        "body": (
            "Motion to allocate $50,000 from the community development fund toward the restoration "
            "of Riverside Park, including new playground equipment, walking trails, and native plantings."
        ),
        "proposed_body_diff": None,
        "status": "proposed",
        "proposer_id": "user-carlos",
        "proposer_name": "Carlos Rivera",
        "seconder_id": None,
        "seconder_name": None,
        "created_at": (now - timedelta(days=1)).isoformat(),
        "updated_at": (now - timedelta(days=1)).isoformat(),
        "discussion_deadline": None,
        "voting_deadline": None,
        "quorum_required": 5,
        "votes": [],
        "result": None,
    }

    # Motion 3: passed (with votes and result)
    m3 = {
        "id": "mot-annual-budget",
        "type": "main",
        "parent_motion_id": None,
        "title": "Approve Annual Budget Report for Fiscal Year 2025",
        "body": (
            "Motion to approve the annual budget report for fiscal year 2025 as presented by the "
            "treasurer. The report details revenues of $2.4M and expenditures of $2.1M, leaving "
            "a surplus of $300K to be allocated to the reserve fund."
        ),
        "proposed_body_diff": None,
        "status": "passed",
        "proposer_id": "user-diana",
        "proposer_name": "Diana Park",
        "seconder_id": "user-eli",
        "seconder_name": "Eli Washington",
        "created_at": (now - timedelta(days=14)).isoformat(),
        "updated_at": (now - timedelta(days=7)).isoformat(),
        "discussion_deadline": (now - timedelta(days=10)).isoformat(),
        "voting_deadline": (now - timedelta(days=7)).isoformat(),
        "quorum_required": 5,
        "votes": [
            {"user_id": "user-alice", "user_name": "Alice Johnson", "choice": "yea", "cast_at": (now - timedelta(days=8)).isoformat()},
            {"user_id": "user-bob", "user_name": "Bob Smith", "choice": "yea", "cast_at": (now - timedelta(days=8)).isoformat()},
            {"user_id": "user-carlos", "user_name": "Carlos Rivera", "choice": "yea", "cast_at": (now - timedelta(days=8)).isoformat()},
            {"user_id": "user-diana", "user_name": "Diana Park", "choice": "yea", "cast_at": (now - timedelta(days=8)).isoformat()},
            {"user_id": "user-eli", "user_name": "Eli Washington", "choice": "yea", "cast_at": (now - timedelta(days=7)).isoformat()},
            {"user_id": "user-frank", "user_name": "Frank Lee", "choice": "nay", "cast_at": (now - timedelta(days=7)).isoformat()},
            {"user_id": "user-grace", "user_name": "Grace Chen", "choice": "abstain", "cast_at": (now - timedelta(days=7)).isoformat()},
        ],
        "result": {
            "yea": 5,
            "nay": 1,
            "abstain": 1,
            "total_votes": 7,
            "quorum_met": True,
            "passed": True,
        },
    }

    for motion in [m1, m2, m3]:
        save_motion(motion)


# --- API Endpoints ---

@app.get("/api/governance/motions", response_model=List[Motion])
async def list_motions(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
):
    """List all motions, optionally filtered by search, status, or type."""
    motion_ids = redis_client.zrevrange(motions_sorted_set_key(), 0, -1)
    motions = []
    for mid in motion_ids:
        motion = load_motion(mid)
        if motion is None:
            continue
        # Apply filters
        if status and motion["status"] != status:
            continue
        if type and motion["type"] != type:
            continue
        if search:
            search_lower = search.lower()
            if (search_lower not in motion["title"].lower()
                    and search_lower not in motion["body"].lower()):
                continue
        motions.append(Motion(**motion_with_score(motion)))
    return motions


@app.post("/api/governance/motions", response_model=Motion)
async def propose_motion(
    motion_create: MotionCreate,
    current_user: dict = Depends(get_current_user),
):
    """Propose a new motion."""
    motion_id = f"mot-{uuid.uuid4().hex[:12]}"
    ts = now_iso()
    motion = {
        "id": motion_id,
        "type": "main",
        "parent_motion_id": None,
        "title": motion_create.title,
        "body": motion_create.body,
        "proposed_body_diff": None,
        "status": "proposed",
        "proposer_id": current_user["sub"],
        "proposer_name": current_user["name"],
        "seconder_id": None,
        "seconder_name": None,
        "created_at": ts,
        "updated_at": ts,
        "discussion_deadline": None,
        "voting_deadline": None,
        "quorum_required": motion_create.quorum_required,
        "votes": [],
        "result": None,
    }
    save_motion(motion)
    return Motion(**motion_with_score(motion))


@app.get("/api/governance/motions/{motion_id}", response_model=Motion)
async def get_motion(motion_id: str):
    """Get a single motion by ID."""
    motion = load_motion(motion_id)
    if motion is None:
        raise HTTPException(status_code=404, detail="Motion not found")
    return Motion(**motion_with_score(motion))


@app.post("/api/governance/motions/{motion_id}/second", response_model=Motion)
async def second_motion(
    motion_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Second a motion. Only allowed if status is 'proposed' and user is not the proposer."""
    motion = load_motion(motion_id)
    if motion is None:
        raise HTTPException(status_code=404, detail="Motion not found")
    if motion["status"] != "proposed":
        raise HTTPException(status_code=400, detail="Motion can only be seconded when in 'proposed' status")
    if motion["proposer_id"] == current_user["sub"]:
        raise HTTPException(status_code=400, detail="Proposer cannot second their own motion")

    motion["seconder_id"] = current_user["sub"]
    motion["seconder_name"] = current_user["name"]
    # Auto-advance past 'seconded' to 'discussion'
    motion["status"] = "discussion"
    motion["updated_at"] = now_iso()
    motion["discussion_deadline"] = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    save_motion(motion)
    return Motion(**motion_with_score(motion))


@app.post("/api/governance/motions/{motion_id}/vote", response_model=Motion)
async def cast_vote(
    motion_id: str,
    vote_request: VoteRequest,
    current_user: dict = Depends(get_current_user),
):
    """Cast a vote on a motion. Only allowed if status is 'voting' and user hasn't voted."""
    if vote_request.choice not in ("yea", "nay", "abstain"):
        raise HTTPException(status_code=400, detail="Choice must be 'yea', 'nay', or 'abstain'")

    motion = load_motion(motion_id)
    if motion is None:
        raise HTTPException(status_code=404, detail="Motion not found")
    if motion["status"] != "voting":
        raise HTTPException(status_code=400, detail="Voting is not open for this motion")

    # Check if user already voted
    for v in motion["votes"]:
        if v["user_id"] == current_user["sub"]:
            raise HTTPException(status_code=400, detail="User has already voted on this motion")

    motion["votes"].append({
        "user_id": current_user["sub"],
        "user_name": current_user["name"],
        "choice": vote_request.choice,
        "cast_at": now_iso(),
    })
    motion["updated_at"] = now_iso()
    save_motion(motion)
    return Motion(**motion_with_score(motion))


@app.post("/api/governance/motions/{motion_id}/table", response_model=Motion)
async def table_motion(
    motion_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Table a motion. Only allowed if status is 'discussion'."""
    motion = load_motion(motion_id)
    if motion is None:
        raise HTTPException(status_code=404, detail="Motion not found")
    if motion["status"] != "discussion":
        raise HTTPException(status_code=400, detail="Motion can only be tabled during discussion")

    motion["status"] = "tabled"
    motion["updated_at"] = now_iso()
    save_motion(motion)
    return Motion(**motion_with_score(motion))


@app.post("/api/governance/motions/{motion_id}/withdraw", response_model=Motion)
async def withdraw_motion(
    motion_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Withdraw a motion. Only allowed if status is 'proposed' and user is the proposer."""
    motion = load_motion(motion_id)
    if motion is None:
        raise HTTPException(status_code=404, detail="Motion not found")
    if motion["status"] != "proposed":
        raise HTTPException(status_code=400, detail="Motion can only be withdrawn when in 'proposed' status")
    if motion["proposer_id"] != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Only the proposer can withdraw the motion")

    motion["status"] = "withdrawn"
    motion["updated_at"] = now_iso()
    save_motion(motion)
    return Motion(**motion_with_score(motion))


@app.post("/api/governance/motions/{motion_id}/amend", response_model=Motion)
async def amend_motion(
    motion_id: str,
    amendment: AmendmentCreate,
    current_user: dict = Depends(get_current_user),
):
    """Propose an amendment to a motion. Creates a new motion of type 'amendment'."""
    parent = load_motion(motion_id)
    if parent is None:
        raise HTTPException(status_code=404, detail="Parent motion not found")

    amendment_id = f"mot-{uuid.uuid4().hex[:12]}"
    ts = now_iso()
    amendment_motion = {
        "id": amendment_id,
        "type": "amendment",
        "parent_motion_id": motion_id,
        "title": amendment.title,
        "body": amendment.body,
        "proposed_body_diff": amendment.proposed_body_diff,
        "status": "proposed",
        "proposer_id": current_user["sub"],
        "proposer_name": current_user["name"],
        "seconder_id": None,
        "seconder_name": None,
        "created_at": ts,
        "updated_at": ts,
        "discussion_deadline": None,
        "voting_deadline": None,
        "quorum_required": parent["quorum_required"],
        "votes": [],
        "result": None,
    }
    save_motion(amendment_motion)
    # Track amendment in parent's amendment set
    redis_client.sadd(amendments_key(motion_id), amendment_id)

    return Motion(**motion_with_score(amendment_motion))


@app.post("/api/governance/motions/{motion_id}/open-voting", response_model=Motion)
async def open_voting(
    motion_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Open the voting period. Only allowed if status is 'discussion'."""
    motion = load_motion(motion_id)
    if motion is None:
        raise HTTPException(status_code=404, detail="Motion not found")
    if motion["status"] != "discussion":
        raise HTTPException(status_code=400, detail="Voting can only be opened during discussion")

    motion["status"] = "voting"
    motion["voting_deadline"] = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    motion["updated_at"] = now_iso()
    save_motion(motion)
    return Motion(**motion_with_score(motion))


@app.post("/api/governance/motions/{motion_id}/resolve", response_model=Motion)
async def resolve_motion(
    motion_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Resolve voting on a motion. Counts votes and determines pass/fail."""
    motion = load_motion(motion_id)
    if motion is None:
        raise HTTPException(status_code=404, detail="Motion not found")
    if motion["status"] != "voting":
        raise HTTPException(status_code=400, detail="Motion must be in 'voting' status to resolve")

    yea = sum(1 for v in motion["votes"] if v["choice"] == "yea")
    nay = sum(1 for v in motion["votes"] if v["choice"] == "nay")
    abstain = sum(1 for v in motion["votes"] if v["choice"] == "abstain")
    total = len(motion["votes"])
    quorum_met = total >= motion["quorum_required"]
    passed = quorum_met and yea > nay

    motion["result"] = {
        "yea": yea,
        "nay": nay,
        "abstain": abstain,
        "total_votes": total,
        "quorum_met": quorum_met,
        "passed": passed,
    }
    motion["status"] = "passed" if passed else "failed"
    motion["updated_at"] = now_iso()
    save_motion(motion)
    return Motion(**motion_with_score(motion))


# --- Engagement Endpoints (upvote/downvote/comments) ---

@app.post("/api/governance/motions/{motion_id}/upvote")
async def upvote_motion(
    motion_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Toggle upvote on a motion."""
    motion = load_motion(motion_id)
    if motion is None:
        raise HTTPException(status_code=404, detail="Motion not found")

    user_id = current_user["sub"]
    up_key = upvoters_key(motion_id)
    down_key = downvoters_key(motion_id)

    if redis_client.sismember(up_key, user_id):
        redis_client.srem(up_key, user_id)
        user_vote = None
    else:
        redis_client.srem(down_key, user_id)
        redis_client.sadd(up_key, user_id)
        user_vote = "up"

    score = compute_engagement_score(motion_id)
    return {"score": score, "user_vote": user_vote}


@app.post("/api/governance/motions/{motion_id}/downvote")
async def downvote_motion(
    motion_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Toggle downvote on a motion."""
    motion = load_motion(motion_id)
    if motion is None:
        raise HTTPException(status_code=404, detail="Motion not found")

    user_id = current_user["sub"]
    up_key = upvoters_key(motion_id)
    down_key = downvoters_key(motion_id)

    if redis_client.sismember(down_key, user_id):
        redis_client.srem(down_key, user_id)
        user_vote = None
    else:
        redis_client.srem(up_key, user_id)
        redis_client.sadd(down_key, user_id)
        user_vote = "down"

    score = compute_engagement_score(motion_id)
    return {"score": score, "user_vote": user_vote}


@app.get("/api/governance/motions/{motion_id}/user-vote")
async def get_user_vote(
    motion_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Return the current user's vote direction on a motion."""
    user_id = current_user["sub"]
    if redis_client.sismember(upvoters_key(motion_id), user_id):
        return {"user_vote": "up"}
    if redis_client.sismember(downvoters_key(motion_id), user_id):
        return {"user_vote": "down"}
    return {"user_vote": None}


@app.get("/api/governance/motions/{motion_id}/comments", response_model=List[CommentResponse])
async def list_comments(motion_id: str):
    """List comments for a motion, sorted by creation time ascending."""
    raw_list = redis_client.lrange(comments_key(motion_id), 0, -1)
    result = []
    for raw in raw_list:
        comment = json.loads(raw)
        result.append(CommentResponse(**comment))
    result.sort(key=lambda c: c.created_at)
    return result


@app.post("/api/governance/motions/{motion_id}/comments", response_model=CommentResponse)
async def add_comment(
    motion_id: str,
    comment_create: CommentCreate,
    current_user: dict = Depends(get_current_user),
):
    """Add a comment to a motion."""
    motion = load_motion(motion_id)
    if motion is None:
        raise HTTPException(status_code=404, detail="Motion not found")

    comment = {
        "id": f"comment-{uuid.uuid4().hex[:12]}",
        "motion_id": motion_id,
        "author_id": current_user["sub"],
        "author_name": current_user["name"],
        "body": comment_create.body,
        "created_at": now_iso(),
    }
    redis_client.rpush(comments_key(motion_id), json.dumps(comment))
    return CommentResponse(**comment)


# --- Health Check ---

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        redis_client.ping()
        return {"status": "healthy", "redis": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis connection failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8002,
        reload=True,
        reload_dirs=[os.path.dirname(__file__)],
    )
