import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class FriendRead(BaseModel):
    id: uuid.UUID
    full_name: str
    username: str | None
    programme: str | None
    xp: int = 0


class FriendRequestRead(BaseModel):
    request_id: uuid.UUID
    user: FriendRead


class FriendsOverview(BaseModel):
    friends: list[FriendRead]
    # Requests others sent you, and ones you sent that are still waiting.
    incoming: list[FriendRequestRead]
    outgoing: list[FriendRequestRead]


REPORT_REASONS = ("username", "spam", "harassment", "other")


class ReportCreate(BaseModel):
    # One of REPORT_REASONS.
    reason: str = Field(pattern="^(username|spam|harassment|other)$")
    details: str = Field(default="", max_length=1000)
    # Report and block in one step, as most apps offer.
    block: bool = True


class BlockedRead(BaseModel):
    id: uuid.UUID
    name: str
    username: str | None


class FriendRequestCreate(BaseModel):
    username: str = Field(min_length=1, max_length=31)


class StandingRead(BaseModel):
    rank: int
    student_id: uuid.UUID
    name: str
    username: str | None
    programme: str | None
    xp: int
    is_me: bool


class LeaderboardRead(BaseModel):
    scope: str
    period: str
    programme: str | None
    # Whether the student has opted into the programme board.
    joined: bool
    standings: list[StandingRead]


class ChallengeCreate(BaseModel):
    round_id: uuid.UUID
    friend_ids: list[uuid.UUID] = Field(min_length=1, max_length=20)


class ChallengeRead(BaseModel):
    id: uuid.UUID
    game: str
    game_name: str
    title: str
    # "sent" or "received".
    direction: str
    other: FriendRead | None
    my_score: int | None
    their_score: int | None
    # "open", "completed" or "expired".
    status: str
    # "won", "lost" or "draw", once completed.
    outcome: str | None
    expires_at: datetime
    created_at: datetime
