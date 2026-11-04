# Import every model module so Base.metadata is fully populated wherever
# this package is imported (Alembic autogenerate, test schema setup, etc.)
# without reintroducing the base.py <-> models circular import.
from app.models.user import User  # noqa: F401
from app.models.course import Course, Enrollment  # noqa: F401
from app.models.document import (  # noqa: F401
    CourseConcept,
    KnowledgeConcept,
    LectureDocument,
)
from app.models.assessment import (  # noqa: F401
    Assessment,
    AssessmentItem,
    Attempt,
    AttemptAnswer,
)
from app.models.mastery import ConceptMastery  # noqa: F401
from app.models.gamification import EarnedBadge, StudentProgress  # noqa: F401
from app.models.game import GameSession  # noqa: F401
from app.models.job import Job  # noqa: F401
from app.models.schedule import LectureSlot, PushSubscription, SentReminder  # noqa: F401
from app.models.social import (  # noqa: F401
    Challenge,
    Friendship,
    GameRound,
    UserBlock,
    UserReport,
    XpEvent,
)
from app.models.usage import AiUsage  # noqa: F401
from app.models.review import FlashcardReview  # noqa: F401
