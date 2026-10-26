from harbor.agents.terminus_2.failure_classifier import (
    FailureType,
    classify_command_result,
    classify_failure,
)


def test_classifies_context_limit():
    result = classify_failure(
        "Context length exceeded while processing the conversation"
    )
    assert result.failure_type is FailureType.CONTEXT_LIMIT


def test_classifies_output_limit():
    result = classify_failure("Output length exceeded and response was truncated")
    assert result.failure_type is FailureType.OUTPUT_LIMIT


def test_classifies_command_timeout():
    result = classify_failure("The command timed out after 30 seconds")
    assert result.failure_type is FailureType.COMMAND_TIMEOUT


def test_classifies_missing_dependency():
    result = classify_failure("ModuleNotFoundError: No module named 'pytest'")
    assert result.failure_type is FailureType.MISSING_DEPENDENCY


def test_unknown_failure_is_preserved():
    message = "Unexpected build failure"
    result = classify_failure(message)
    assert result.failure_type is FailureType.UNKNOWN
    assert result.evidence == message


def test_command_result_classifies_explicit_timeout():
    result = classify_command_result(True, "Command timed out after 10 seconds")
    assert result is not None
    assert result.failure_type is FailureType.COMMAND_TIMEOUT


def test_command_result_classifies_terminal_failure():
    result = classify_command_result(
        False, "ModuleNotFoundError: No module named 'pytest'"
    )
    assert result is not None
    assert result.failure_type is FailureType.MISSING_DEPENDENCY


def test_command_result_returns_none_for_successful_output():
    result = classify_command_result(False, "Tests passed successfully")
    assert result is None
