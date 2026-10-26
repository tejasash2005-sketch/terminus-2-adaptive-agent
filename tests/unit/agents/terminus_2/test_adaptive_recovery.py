from harbor.agents.terminus_2.adaptive_recovery import (
    AdaptiveRecoveryConfig,
    RecoveryAction,
    RecoveryRecord,
    choose_recovery,
    recovery_attempt_allowed,
    resolve_recovery_record,
)
from harbor.agents.terminus_2.failure_classifier import (
    FailureClassification,
    FailureType,
)


def test_timeout_inspects_terminal_state_before_retry():
    decision = choose_recovery(
        FailureClassification(FailureType.COMMAND_TIMEOUT, "timeout")
    )
    assert decision.action is RecoveryAction.INSPECT_TERMINAL_STATE


def test_missing_dependency_investigates_dependency():
    decision = choose_recovery(
        FailureClassification(FailureType.MISSING_DEPENDENCY, "missing")
    )
    assert decision.action is RecoveryAction.INVESTIGATE_DEPENDENCY


def test_context_limit_uses_context_recovery():
    decision = choose_recovery(
        FailureClassification(FailureType.CONTEXT_LIMIT, "context")
    )
    assert decision.action is RecoveryAction.USE_CONTEXT_RECOVERY


def test_output_limit_uses_output_recovery():
    decision = choose_recovery(
        FailureClassification(FailureType.OUTPUT_LIMIT, "output")
    )
    assert decision.action is RecoveryAction.USE_OUTPUT_RECOVERY


def test_unknown_failure_stops():
    decision = choose_recovery(FailureClassification(FailureType.UNKNOWN, "unknown"))
    assert decision.action is RecoveryAction.STOP


def test_recovery_attempt_allowed_below_limit():
    assert recovery_attempt_allowed(AdaptiveRecoveryConfig(max_attempts=2), 0)
    assert recovery_attempt_allowed(AdaptiveRecoveryConfig(max_attempts=2), 1)


def test_recovery_attempt_denied_at_limit():
    assert not recovery_attempt_allowed(AdaptiveRecoveryConfig(max_attempts=2), 2)


def test_recovery_attempt_denied_when_disabled():
    assert not recovery_attempt_allowed(AdaptiveRecoveryConfig(enabled=False), 0)


def test_negative_recovery_attempt_count_raises():
    import pytest

    with pytest.raises(ValueError, match="attempts_used must be non-negative"):
        recovery_attempt_allowed(AdaptiveRecoveryConfig(), -1)


def test_recovery_delay_uses_configured_backoff():
    from harbor.agents.terminus_2.adaptive_recovery import recovery_delay_sec

    assert recovery_delay_sec(AdaptiveRecoveryConfig(backoff_sec=2.5), 0) == 2.5


def test_recovery_delay_is_zero_when_attempt_limit_reached():
    from harbor.agents.terminus_2.adaptive_recovery import recovery_delay_sec

    assert (
        recovery_delay_sec(AdaptiveRecoveryConfig(max_attempts=1, backoff_sec=2.5), 1)
        == 0.0
    )


def test_repeated_historical_strategy_failures_select_stop():
    decision = choose_recovery(
        FailureClassification(FailureType.COMMAND_TIMEOUT, "timeout"),
        previous_strategy_failures=2,
    )
    assert decision.action is RecoveryAction.STOP
    assert "failed repeatedly" in decision.reason


def test_one_historical_strategy_failure_does_not_force_stop():
    decision = choose_recovery(
        FailureClassification(FailureType.COMMAND_TIMEOUT, "timeout"),
        previous_strategy_failures=1,
    )
    assert decision.action is RecoveryAction.INSPECT_TERMINAL_STATE


def test_negative_historical_failure_count_is_rejected():
    import pytest

    with pytest.raises(ValueError, match="previous_strategy_failures"):
        choose_recovery(
            FailureClassification(FailureType.COMMAND_TIMEOUT, "timeout"),
            previous_strategy_failures=-1,
        )


def test_resolved_record_only_claims_failure_signal_clearance():
    record = RecoveryRecord(
        failure_type=FailureType.COMMAND_TIMEOUT,
        action=RecoveryAction.INSPECT_TERMINAL_STATE,
        attempts_used=0,
        succeeded=None,
    )
    resolved = resolve_recovery_record(record, None)
    assert resolved.succeeded is True
    assert resolved.outcome == "no_recognized_failure_on_following_command"
    assert "task" not in resolved.outcome


def test_unresolved_failure_signal_is_recorded():
    record = RecoveryRecord(
        failure_type=FailureType.COMMAND_TIMEOUT,
        action=RecoveryAction.INSPECT_TERMINAL_STATE,
        attempts_used=0,
        succeeded=None,
    )
    resolved = resolve_recovery_record(record, FailureType.MISSING_DEPENDENCY)
    assert resolved.succeeded is False
    assert resolved.outcome == "failure_signal_persisted:missing_dependency"
