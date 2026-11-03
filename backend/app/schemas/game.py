import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.assessment import NewBadge


class ClockQuestionRead(BaseModel):
    item_id: uuid.UUID
    kind: str
    question: str
    # Four buttons; empty means the answer is typed.
    options: list[str]
    # Sent with the round so feedback after each answer is instant. Scoring
    # does not trust the browser: the server re-marks every response.
    answer: str
    explanation: str


class ClockRound(BaseModel):
    course_id: uuid.UUID
    seconds_per_question: int
    questions: list[ClockQuestionRead]
    personal_best: int | None


class ClockAnswer(BaseModel):
    item_id: uuid.UUID
    response: str = Field(max_length=500)
    time_ms: int = Field(ge=0, le=600_000)


class ClockSubmit(BaseModel):
    course_id: uuid.UUID
    answers: list[ClockAnswer] = Field(min_length=1, max_length=20)


class ClockAnswerResult(BaseModel):
    item_id: uuid.UUID
    correct: bool
    points: int


class MatchPairRead(BaseModel):
    concept_id: uuid.UUID
    name: str
    clue: str


class MatchRound(BaseModel):
    course_id: uuid.UUID
    pairs: list[MatchPairRead]
    personal_best: int | None


class MatchSubmit(BaseModel):
    course_id: uuid.UUID
    concept_ids: list[uuid.UUID] = Field(min_length=1, max_length=12)
    mistakes: int = Field(ge=0, le=500)
    duration_ms: int = Field(ge=0, le=3_600_000)


class GameResult(BaseModel):
    game: str
    score: int
    correct: int
    total: int
    xp_awarded: int
    personal_best: int
    is_personal_best: bool
    new_badges: list[NewBadge] = []
    answers: list[ClockAnswerResult] = []


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
