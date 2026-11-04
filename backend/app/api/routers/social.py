import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.routers.games import _answers, round_view
from app.db.session import get_db
from app.models.course import Course
from app.models.social import Challenge, Friendship, GameRound
from app.models.user import User
from app.schemas.assessment import NewBadge
from app.schemas.game import AnswerResult, ChallengeInfo, GameResult, RoundRead, RoundSubmit
from app.schemas.social import (
    ChallengeCreate,
    ChallengeRead,
    FriendRead,
    FriendRequestCreate,
    FriendsOverview,
    LeaderboardRead,
    StandingRead,
)
from app.services import arcade, social
from app.services.gamification import BADGES_BY_CODE, _award, add_xp
from app.services.notifications import Notification, send_push

logger = logging.getLogger(__name__)

router = APIRouter(tags=["social"])

GAME_NAMES = {
    arcade.BEAT_THE_CLOCK: "Beat the Clock",
    arcade.CONCEPT_MATCH: "Concept Match",
    arcade.TRUE_FALSE: "True or False Blitz",
    arcade.ODD_ONE_OUT: "Odd One Out",
    arcade.THREE_STRIKES: "Three Strikes",
}


def _push(db: Session, user_id: uuid.UUID, note: Notification) -> None:
    """Best effort: a failed notification must not fail the request behind it."""
    try:
        send_push(db, user_id, note)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Social push to %s failed: %s", user_id, exc)


def _friend(user: User, xp: int = 0) -> FriendRead:
    return FriendRead(id=user.id, full_name=user.full_name, username=user.username, programme=user.programme, xp=xp)


# --- Friends ----------------------------------------------------------------


@router.get("/friends", response_model=FriendsOverview)
def overview(db: Session = Depends(get_db), me: User = Depends(get_current_user)) -> FriendsOverview:
    rows = db.query(Friendship).filter(or_(Friendship.requester_id == me.id, Friendship.addressee_id == me.id)).all()
    others = {row.requester_id if row.addressee_id == me.id else row.addressee_id for row in rows}
    users = {user.id: user for user in db.query(User).filter(User.id.in_(others))} if others else {}
    xp = social._xp(db, list(users), "all")

    friends, incoming, outgoing = [], [], []
    for row in rows:
        other_id = row.requester_id if row.addressee_id == me.id else row.addressee_id
        other = users.get(other_id)
        if other is None:
            continue
        if row.status == "accepted":
            friends.append(_friend(other, xp.get(other.id, 0)))
        elif row.addressee_id == me.id:
            incoming.append({"request_id": row.id, "user": _friend(other)})
        else:
            outgoing.append({"request_id": row.id, "user": _friend(other)})
    friends.sort(key=lambda f: -f.xp)
    return FriendsOverview(friends=friends, incoming=incoming, outgoing=outgoing)


@router.post("/friends/requests", status_code=status.HTTP_201_CREATED)
def send_request(
    payload: FriendRequestCreate,
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
) -> dict:
    username = payload.username.strip().lstrip("@").lower()
    other = db.query(User).filter(User.username == username).first() if username else None
    if other is None:
        raise HTTPException(status_code=404, detail="Nobody has that username. Check the spelling with your friend.")
    if other.id == me.id:
        raise HTTPException(status_code=400, detail="That is your own username.")
    existing = social.friendship(db, me.id, other.id)
    if existing is not None:
        if existing.status == "accepted":
            raise HTTPException(status_code=409, detail="You are already friends.")
        if existing.addressee_id == me.id:
            # They already asked: sending back counts as accepting.
            return accept_request(existing.id, db, me)
        raise HTTPException(status_code=409, detail="Request already sent. Waiting for them to accept.")

    db.add(Friendship(requester_id=me.id, addressee_id=other.id, status="pending"))
    db.commit()
    _push(db, other.id, Notification(
        title="New friend request",
        body=f"{me.full_name} wants to be friends on StudyMate.",
        path="/friends",
        tag="friend-request",
    ))
    return {"status": "pending"}


def _own_request(db: Session, request_id: uuid.UUID, me: User) -> Friendship:
    row = db.get(Friendship, request_id)
    if row is None or row.addressee_id != me.id or row.status != "pending":
        raise HTTPException(status_code=404, detail="Request not found")
    return row


@router.post("/friends/requests/{request_id}/accept")
def accept_request(request_id: uuid.UUID, db: Session = Depends(get_db), me: User = Depends(get_current_user)) -> dict:
    row = _own_request(db, request_id, me)
    row.status = "accepted"
    row.responded_at = datetime.now(timezone.utc)
    for student_id in (row.requester_id, row.addressee_id):
        _award(db, student_id, "first_friend", [])
    db.commit()
    _push(db, row.requester_id, Notification(
        title="Friend request accepted",
        body=f"{me.full_name} accepted your friend request. Challenge them in the Arcade!",
        path="/friends",
        tag="friend-request",
    ))
    return {"status": "accepted"}


@router.post("/friends/requests/{request_id}/decline", status_code=status.HTTP_204_NO_CONTENT)
def decline_request(request_id: uuid.UUID, db: Session = Depends(get_db), me: User = Depends(get_current_user)) -> None:
    db.delete(_own_request(db, request_id, me))
    db.commit()


@router.delete("/friends/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_friend(user_id: uuid.UUID, db: Session = Depends(get_db), me: User = Depends(get_current_user)) -> None:
    """Unfriend, or cancel a request sent."""
    row = social.friendship(db, me.id, user_id)
    if row is None or (row.status == "pending" and row.requester_id != me.id):
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(row)
    db.commit()


# --- Leaderboards -------------------------------------------------------------


@router.get("/leaderboard", response_model=LeaderboardRead)
def get_leaderboard(
    scope: str = "friends",
    period: str = "week",
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
) -> LeaderboardRead:
    if scope not in ("friends", "programme") or period not in ("week", "all"):
        raise HTTPException(status_code=400, detail="Unknown leaderboard")
    standings = social.leaderboard(db, me, scope, period)
    return LeaderboardRead(
        scope=scope,
        period=period,
        programme=me.programme,
        joined=me.public_leaderboard,
        standings=[StandingRead(**s.__dict__) for s in standings],
    )


@router.get("/programmes", response_model=list[str])
def programmes(db: Session = Depends(get_db), me: User = Depends(get_current_user)) -> list[str]:
    """Programme names already in use, offered as suggestions so spellings converge."""
    names: dict[str, tuple[str, int]] = {}
    for (name,) in db.query(User.programme).filter(User.programme.isnot(None)):
        key = social.programme_key(name)
        if not key:
            continue
        label, count = names.get(key, (name, 0))
        names[key] = (label, count + 1)
    return [label for label, _ in sorted(names.values(), key=lambda pair: -pair[1])][:200]


# --- Challenges ---------------------------------------------------------------


def _challenge_read(db: Session, row: Challenge, me: User) -> ChallengeRead:
    other_id = row.opponent_id if row.challenger_id == me.id else row.challenger_id
    other = db.get(User, other_id)
    mine = row.challenger_score if row.challenger_id == me.id else row.opponent_score
    theirs = row.opponent_score if row.challenger_id == me.id else row.challenger_score
    outcome = None
    if row.status == "completed" and mine is not None and theirs is not None:
        outcome = "won" if mine > theirs else "lost" if mine < theirs else "draw"
    return ChallengeRead(
        id=row.id,
        game=row.game,
        game_name=GAME_NAMES.get(row.game, row.game),
        title=row.title,
        direction="sent" if row.challenger_id == me.id else "received",
        other=_friend(other) if other else None,
        my_score=mine,
        their_score=theirs,
        status=row.status,
        outcome=outcome,
        expires_at=row.expires_at,
        created_at=row.created_at,
    )


@router.get("/challenges", response_model=list[ChallengeRead])
def list_challenges(db: Session = Depends(get_db), me: User = Depends(get_current_user)) -> list[ChallengeRead]:
    social.expire_old(db, me.id)
    db.commit()
    rows = (
        db.query(Challenge)
        .filter(or_(Challenge.challenger_id == me.id, Challenge.opponent_id == me.id))
        .order_by(Challenge.created_at.desc())
        .limit(50)
        .all()
    )
    return [_challenge_read(db, row, me) for row in rows]


@router.post("/challenges", response_model=list[ChallengeRead], status_code=status.HTTP_201_CREATED)
def create_challenges(
    payload: ChallengeCreate,
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
) -> list[ChallengeRead]:
    """Challenge friends to beat your score on a round you have just played."""
    round_ = db.get(GameRound, payload.round_id)
    if round_ is None or round_.student_id != me.id:
        raise HTTPException(status_code=404, detail="Round not found")
    if round_.submitted_at is None or round_.score is None:
        raise HTTPException(status_code=409, detail="Finish the round before challenging anyone to it.")
    title = f"{db.get(Course, round_.course_id).code} · {db.get(Course, round_.course_id).name}"

    created = []
    for friend_id in dict.fromkeys(payload.friend_ids):
        if not social.are_friends(db, me.id, friend_id):
            raise HTTPException(status_code=403, detail="You can only challenge friends.")
        row = Challenge(
            round_id=round_.id,
            challenger_id=me.id,
            opponent_id=friend_id,
            game=round_.game,
            title=title,
            challenger_score=round_.score,
            status="open",
            expires_at=social.new_expiry(),
        )
        db.add(row)
        created.append(row)
    db.commit()
    for row in created:
        _push(db, row.opponent_id, Notification(
            title=f"{me.full_name} challenged you",
            body=f"Beat {row.challenger_score:,} points in {GAME_NAMES[row.game]} ({title}) within {social.CHALLENGE_HOURS} hours.",
            path="/friends?tab=challenges",
            tag=f"challenge-{row.id}",
        ))
    return [_challenge_read(db, row, me) for row in created]


def _open_challenge(db: Session, challenge_id: uuid.UUID, me: User) -> Challenge:
    row = db.get(Challenge, challenge_id)
    if row is None or row.opponent_id != me.id:
        raise HTTPException(status_code=404, detail="Challenge not found")
    social.expire_old(db, me.id)
    db.refresh(row)
    if row.status != "open":
        raise HTTPException(status_code=409, detail="This challenge has already been played or has expired.")
    return row


@router.get("/challenges/{challenge_id}/round", response_model=RoundRead)
def challenge_round(challenge_id: uuid.UUID, db: Session = Depends(get_db), me: User = Depends(get_current_user)) -> RoundRead:
    """The challenger's exact round, for the friend to play."""
    row = _open_challenge(db, challenge_id, me)
    challenger = db.get(User, row.challenger_id)
    return round_view(
        db,
        db.get(GameRound, row.round_id),
        personal_best=None,
        challenge=ChallengeInfo(
            id=row.id,
            challenger_name=challenger.full_name if challenger else "A friend",
            challenger_score=row.challenger_score,
        ),
    )


@router.post("/challenges/{challenge_id}/submit", response_model=GameResult, status_code=status.HTTP_201_CREATED)
def submit_challenge(
    challenge_id: uuid.UUID,
    payload: RoundSubmit,
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
) -> GameResult:
    row = _open_challenge(db, challenge_id, me)
    round_ = db.get(GameRound, row.round_id)
    try:
        marked = arcade.mark(round_.game, round_.payload, _answers(payload), payload.mistakes, payload.duration_ms)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    row.opponent_score = marked.score
    row.status = "completed"
    row.completed_at = datetime.now(timezone.utc)

    # The material is the challenger's, so these answers say nothing about the
    # opponent's own courses: no mastery change, only XP for playing and winning.
    badges = []
    xp = marked.xp
    if marked.score > row.challenger_score:
        xp += social.CHALLENGE_WIN_XP
        _award(db, me.id, "challenge_won", badges)
    elif marked.score < row.challenger_score:
        add_xp(db, row.challenger_id, social.CHALLENGE_WIN_XP, "challenge")
        _award(db, row.challenger_id, "challenge_won", [])
    else:
        xp += social.CHALLENGE_DRAW_XP
        add_xp(db, row.challenger_id, social.CHALLENGE_DRAW_XP, "challenge")
    add_xp(db, me.id, xp, "challenge")
    db.commit()

    verdict = "beat you" if marked.score > row.challenger_score else "could not beat you" if marked.score < row.challenger_score else "drew with you"
    _push(db, row.challenger_id, Notification(
        title="Challenge result",
        body=f"{me.full_name} {verdict}: {marked.score:,} to your {row.challenger_score:,} in {GAME_NAMES[row.game]}.",
        path="/friends?tab=challenges",
        tag=f"challenge-{row.id}",
    ))
    return GameResult(
        game=round_.game,
        score=marked.score,
        correct=marked.correct,
        total=marked.total,
        xp_awarded=xp,
        personal_best=marked.score,
        is_personal_best=marked.score > row.challenger_score,
        new_badges=[NewBadge(code=b.code, name=b.name, description=b.description) for b in badges],
        answers=[AnswerResult(key=key, correct=correct, points=points) for key, correct, points in marked.answers],
    )
