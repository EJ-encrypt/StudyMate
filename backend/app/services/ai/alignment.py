"""Matching returned grades back to the answers they belong to.

Shared by every provider, because the failure it guards against is not
provider-specific: a model asked to echo an identifier may decorate it,
reorder it, or drop it. Getting this wrong once already caused every answer in
a submission to be reported unmarkable.
"""

import logging

from app.services.ai.base import ShortAnswerGrade, ShortAnswerSubmission

logger = logging.getLogger(__name__)


def clean_reference(reference: str) -> str:
    return reference.strip().strip("[]()\"'").strip().lower()


def align_grades(
    submissions: list[ShortAnswerSubmission],
    returned: list[ShortAnswerGrade],
) -> list[ShortAnswerGrade]:
    """Match grades to submissions, tolerating how the model echoes references.

    Models decorate the reference (brackets, quotes, stray whitespace), so
    matching is done on a cleaned form. If a reference still cannot be matched
    but the counts line up, order is trusted instead. Anything left over is
    left out, so it stays unmarked, rather than risking a grade being attributed to the wrong
    question.
    """
    by_reference = {clean_reference(grade.reference): grade for grade in returned}
    positional = returned if len(returned) == len(submissions) else []

    results = []
    for index, submission in enumerate(submissions):
        grade = by_reference.get(clean_reference(submission.reference))
        if grade is None and positional:
            grade = positional[index]
            logger.warning(
                "Reference %s not echoed back; matched grade by position",
                submission.reference,
            )

        if grade is None:
            # Left out, so the caller treats it as unmarked rather than wrong.
            logger.warning("No grade returned for %s; leaving it unmarked", submission.reference)
        else:
            # Return our own reference so callers can always match on it.
            results.append(
                ShortAnswerGrade(
                    reference=submission.reference,
                    is_correct=grade.is_correct,
                    feedback=grade.feedback,
                )
            )
    return results
