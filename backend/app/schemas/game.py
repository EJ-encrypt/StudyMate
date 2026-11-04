import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.assessment import NewBadge


class ChallengeInfo(BaseModel):
    """Shown while playing a friend's challenge: whose score to beat."""

    id: uuid.UUID
    challenger_name: str
    challenger_score: int


class RoundRead(BaseModel):
    """A dealt round of any game.

    The game's own content sits alongside these fields, as stored: for
    example "questions" for Beat the Clock and Three Strikes, "pairs" for
    Concept Match, "statements" for True or False Blitz, "puzzles" for Odd One
    Out. Answers are included so feedback is instant; scoring never trusts
    the browser and re-marks everything against the stored round.
    """

    model_config = ConfigDict(extra="allow")

    round_id: uuid.UUID
    game: str
    course_id: uuid.UUID
    # "MATH 223 · Calculus II": what a friend sees, who does not have the course.
    title: str
    personal_best: int | None
    challenge: ChallengeInfo | None = None


class RoundAnswer(BaseModel):
    # The question, statement or puzzle answered: an item id, a statement key,
    # or a puzzle's position.
    key: str = Field(max_length=200)
    response: str = Field(max_length=500)
    time_ms: int = Field(ge=0, le=600_000)


class RoundSubmit(BaseModel):
    answers: list[RoundAnswer] = Field(default=[], max_length=100)
    # Concept Match only: wrong pairs, and how long the whole board took.
    mistakes: int = Field(default=0, ge=0, le=500)
    duration_ms: int = Field(default=0, ge=0, le=3_600_000)


class AnswerResult(BaseModel):
    key: str
    correct: bool
    points: int


class GameResult(BaseModel):
    game: str
    round_id: uuid.UUID | None = None
    score: int
    correct: int
    total: int
    xp_awarded: int
    personal_best: int
    is_personal_best: bool
    new_badges: list[NewBadge] = []
    answers: list[AnswerResult] = []


class GameStats(BaseModel):
    game: str
    plays: int
    best: int | None
    last_played_at: datetime | None


class CourseGameStats(BaseModel):
    course_id: uuid.UUID
    games: list[GameStats]
    clock_questions_available: int
    concepts_available: int
    # Whole-course Concept Match rounds still possible without repeats.
    match_fresh_rounds: int = 0
