from dataclasses import dataclass
from enum import Enum


class FailureType(str, Enum):
    """Recognized failure categories for adaptive terminal recovery."""

    COMMAND_TIMEOUT = "command_timeout"
    CONTEXT_LIMIT = "context_limit"
    OUTPUT_LIMIT = "output_limit"
    MISSING_DEPENDENCY = "missing_dependency"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class FailureClassification:
    """A deterministic classification of a failure signal."""

    failure_type: FailureType
    evidence: str


def classify_failure(message: str) -> FailureClassification:
    """Classify an error message without executing recovery actions."""
    normalized = message.casefold()

    if any(
        term in normalized
        for term in (
            "context length exceeded",
            "context_length_exceeded",
            "maximum context length",
            "context window exceeded",
        )
    ):
        return FailureClassification(FailureType.CONTEXT_LIMIT, message)

    if any(
        term in normalized
        for term in (
            "output length exceeded",
            "output_length_exceeded",
            "maximum output length",
            "response was truncated",
        )
    ):
        return FailureClassification(FailureType.OUTPUT_LIMIT, message)

    if any(
        term in normalized
        for term in (
            "timed out",
            "timeout",
            "time out",
        )
    ):
        return FailureClassification(FailureType.COMMAND_TIMEOUT, message)

    if any(
        term in normalized
        for term in (
            "modulenotfounderror",
            "no module named",
            "command not found",
            "not recognized as an internal or external command",
            "no such file or directory",
        )
    ):
        return FailureClassification(FailureType.MISSING_DEPENDENCY, message)

    return FailureClassification(FailureType.UNKNOWN, message)


def classify_command_result(
    timeout_occurred: bool, terminal_output: str
) -> FailureClassification | None:
    """Classify a terminal command result when it represents a failure.

    Successful command results return ``None`` so callers can distinguish
    normal terminal output from an adaptive-recovery signal.
    """
    if timeout_occurred:
        return FailureClassification(
            FailureType.COMMAND_TIMEOUT,
            terminal_output,
        )

    classification = classify_failure(terminal_output)
    if classification.failure_type is FailureType.UNKNOWN:
        return None

    return classification
