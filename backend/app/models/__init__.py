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
