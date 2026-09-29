"""Turn an internal exception into something a student can act on.

Raw provider errors reach the UI as the reason a document or quiz failed.
"429 RESOURCE_EXHAUSTED. {'error': {'code': 429, ...}}" tells a student
nothing and, in an unmoderated session, ends their attempt at the task.
Each message here says what happened and what to do next.
"""

from google.genai import errors

# Rate limits and busy models are the common failure on a free-tier key, and
# they are worth retrying; a malformed document is not.
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


def describe(exc: Exception) -> tuple[str, bool]:
    """Return a student-facing message, and whether retrying may help."""
    if isinstance(exc, errors.APIError):
        if exc.code == 429:
            return (
                "The AI service has hit its usage limit for now. Nothing is lost - "
                "wait a minute and try again.",
                True,
            )
        if exc.code in RETRYABLE_STATUS:
            return (
                "The AI service is busy at the moment. Nothing is lost - "
                "wait a minute and try again.",
                True,
            )
        if exc.code in (401, 403):
            return (
                "StudyMate could not reach the AI service. This needs an "
                "administrator to check the service configuration.",
                False,
            )
        return ("The AI service could not process this. Please try again.", True)

    message = str(exc)
    if "No readable text" in message:
        return (
            "No text could be read from this file. If it is a scanned image "
            "rather than a text document, StudyMate cannot read it yet.",
            False,
        )
    if "Cannot extract text" in message:
        return (message, False)
    if "no usable questions" in message:
        return (
            "The AI service did not return any usable questions from this "
            "material. Try again, or try a different document.",
            True,
        )
    if "no concepts" in message:
        return (
            "There are no concepts to draw on yet. Upload some material and "
            "wait for it to finish processing first.",
            False,
        )

    return (
        "Something went wrong while processing this. Please try again, and "
        "tell the researcher if it keeps happening.",
        True,
    )
