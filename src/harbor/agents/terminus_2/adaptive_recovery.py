from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

from harbor.agents.terminus_2.failure_classifier import (
    FailureClassification,
    FailureType,
)


class AdaptiveRecoveryConfig(BaseModel):
    """Configuration for Terminus-2 adaptive terminal recovery."""

    enabled: bool = Field(
        default=True,
        description="Enable adaptive recovery decisions for terminal failures.",
    )
    max_attempts: int = Field(
        default=2,
        description="Maximum recovery attempts for a single failure.",
        ge=0,
    )
    backoff_sec: float = Field(
        default=1.0,
        description="Delay between adaptive recovery attempts in seconds.",
        ge=0.0,
    )
    knowledge_store_path: str | None = Field(
        default=None,
        description="Optional SQLite path for persistent recovery outcomes; unset disables persistence.",
    )


class RecoveryAction(str, Enum):
    """Recovery actions selected from terminal failure classifications."""

    INSPECT_TERMINAL_STATE = "inspect_terminal_state"
    INVESTIGATE_DEPENDENCY = "investigate_dependency"
    USE_CONTEXT_RECOVERY = "use_context_recovery"
    USE_OUTPUT_RECOVERY = "use_output_recovery"
    STOP = "stop"


@dataclass(frozen=True)
class RecoveryDecision:
    """Deterministic recovery decision for a classified failure."""

    action: RecoveryAction
    reason: str


@dataclass(frozen=True)
class RecoveryRecord:
    """Outcome record for one adaptive recovery decision.

    ``succeeded`` describes whether the previously observed failure signal cleared,
    not whether the overall task completed successfully.
    """

    failure_type: FailureType
    action: RecoveryAction
    attempts_used: int
    succeeded: bool | None
    evidence: str = ""
    outcome: str | None = None
    recorded_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


def choose_recovery(
    classification: FailureClassification,
    *,
    previous_strategy_failures: int = 0,
    stop_after_failures: int = 2,
) -> RecoveryDecision:
    """Choose a safe action, avoiding strategies with repeated failed outcomes."""
    if previous_strategy_failures < 0:
        raise ValueError("previous_strategy_failures must be non-negative")
    if stop_after_failures < 1:
        raise ValueError("stop_after_failures must be positive")
    actions = {
        FailureType.COMMAND_TIMEOUT: RecoveryDecision(
            RecoveryAction.INSPECT_TERMINAL_STATE,
            "Inspect the terminal state before considering a retry.",
        ),
        FailureType.MISSING_DEPENDENCY: RecoveryDecision(
            RecoveryAction.INVESTIGATE_DEPENDENCY,
            "Inspect the missing dependency before retrying.",
        ),
        FailureType.CONTEXT_LIMIT: RecoveryDecision(
            RecoveryAction.USE_CONTEXT_RECOVERY,
            "Use Terminus-2 existing context recovery path.",
        ),
        FailureType.OUTPUT_LIMIT: RecoveryDecision(
            RecoveryAction.USE_OUTPUT_RECOVERY,
            "Use Terminus-2 existing output recovery path.",
        ),
        FailureType.UNKNOWN: RecoveryDecision(
            RecoveryAction.STOP,
            "No safe adaptive recovery strategy is known.",
        ),
    }
    decision = actions[classification.failure_type]
    if (
        decision.action is not RecoveryAction.STOP
        and previous_strategy_failures >= stop_after_failures
    ):
        return RecoveryDecision(
            RecoveryAction.STOP,
            "Historical outcomes show this strategy failed repeatedly; "
            "stop and request a safer alternative instead of repeating it.",
        )
    return decision


def resolve_recovery_record(
    record: RecoveryRecord,
    next_failure_type: FailureType | None,
) -> RecoveryRecord:
    """Resolve a decision from the next observed result, without claiming task success."""
    if next_failure_type is None:
        return replace(
            record,
            succeeded=True,
            outcome="no_recognized_failure_on_following_command",
        )
    return replace(
        record,
        succeeded=False,
        outcome=f"failure_signal_persisted:{next_failure_type.value}",
    )


def recovery_attempt_allowed(
    config: AdaptiveRecoveryConfig,
    attempts_used: int,
) -> bool:
    """Return whether another recovery attempt is allowed."""
    if attempts_used < 0:
        raise ValueError("attempts_used must be non-negative")
    return config.enabled and attempts_used < config.max_attempts


def recovery_delay_sec(
    config: AdaptiveRecoveryConfig,
    attempts_used: int,
) -> float:
    """Return the configured delay when another recovery attempt is allowed."""
    if not recovery_attempt_allowed(config, attempts_used):
        return 0.0
    return config.backoff_sec
