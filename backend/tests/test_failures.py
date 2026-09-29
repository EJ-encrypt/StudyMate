"""A participant in an unmoderated session reads these messages, not a log."""

import pytest
from google.genai import errors

from app.services.failures import describe


def _api_error(code: int) -> errors.APIError:
    error = errors.APIError.__new__(errors.APIError)
    error.code = code
    error.message = "simulated"
    error.status = "ERROR"
    error.details = {"error": {"code": code, "message": "raw provider detail"}}
    return error


@pytest.mark.parametrize("code", [429, 500, 503])
def test_transient_provider_failures_are_retryable(code: int) -> None:
    message, can_retry = describe(_api_error(code))

    assert can_retry
    assert "try again" in message.lower()
    assert str(code) not in message, "a status code means nothing to a student"
    assert "RESOURCE_EXHAUSTED" not in message


def test_rate_limit_reassures_that_nothing_is_lost() -> None:
    message, _ = describe(_api_error(429))
    assert "nothing is lost" in message.lower()


def test_auth_failure_is_not_the_students_problem_to_retry() -> None:
    message, can_retry = describe(_api_error(403))

    assert not can_retry
    assert "administrator" in message.lower()


def test_unreadable_file_is_not_retryable_and_explains_why() -> None:
    message, can_retry = describe(ValueError("No readable text found in this document"))

    assert not can_retry
    assert "scanned image" in message.lower()


def test_unsupported_type_message_is_passed_through() -> None:
    from app.services.extraction import UnsupportedDocumentType

    message, can_retry = describe(UnsupportedDocumentType("Cannot extract text from '.mp3' files"))

    assert not can_retry
    assert ".mp3" in message


def test_empty_knowledge_base_tells_the_student_what_to_do_first() -> None:
    message, can_retry = describe(ValueError("This course has no concepts to draw on yet"))

    assert not can_retry
    assert "upload" in message.lower()


def test_unknown_failure_is_retryable_and_mentions_the_researcher() -> None:
    message, can_retry = describe(RuntimeError("some internal detail nobody should see"))

    assert can_retry
    assert "some internal detail" not in message
    assert "researcher" in message.lower()
