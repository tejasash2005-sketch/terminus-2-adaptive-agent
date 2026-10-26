from harbor.agents.terminus_2.adaptive_recovery import RecoveryAction, RecoveryRecord
from harbor.agents.terminus_2.failure_classifier import FailureType
from harbor.agents.terminus_2.recovery_knowledge import RecoveryKnowledgeStore


def test_store_persists_outcomes_and_summarizes(tmp_path):
    store = RecoveryKnowledgeStore(tmp_path / "recovery.sqlite3")
    store.record(
        RecoveryRecord(
            failure_type=FailureType.COMMAND_TIMEOUT,
            action=RecoveryAction.INSPECT_TERMINAL_STATE,
            attempts_used=0,
            succeeded=False,
            evidence="command_timeout",
            outcome="failure_signal_persisted:command_timeout",
        )
    )
    store.record(
        RecoveryRecord(
            failure_type=FailureType.COMMAND_TIMEOUT,
            action=RecoveryAction.INSPECT_TERMINAL_STATE,
            attempts_used=0,
            succeeded=True,
            evidence="command_timeout",
            outcome="no_recognized_failure_on_following_command",
        )
    )

    assert store.failed_count("command_timeout", "inspect_terminal_state") == 1
    summary = store.summary()
    assert summary["total_records"] == 2
    assert summary["strategies"][0]["failure_signal_cleared"] == 1
    assert summary["strategies"][0]["failure_signal_not_cleared"] == 1


def test_store_does_not_persist_raw_evidence(tmp_path):
    path = tmp_path / "recovery.sqlite3"
    store = RecoveryKnowledgeStore(path)
    store.record(
        RecoveryRecord(
            failure_type=FailureType.UNKNOWN,
            action=RecoveryAction.STOP,
            attempts_used=0,
            succeeded=None,
            evidence="do-not-store-this-secret",
        )
    )
    import sqlite3

    with sqlite3.connect(path) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(recovery_outcomes)")
        }
    assert "evidence" not in columns


def test_store_rejects_negative_attempt_count(tmp_path):
    store = RecoveryKnowledgeStore(tmp_path / "recovery.sqlite3")
    record = RecoveryRecord(
        failure_type=FailureType.UNKNOWN,
        action=RecoveryAction.STOP,
        attempts_used=-1,
        succeeded=None,
    )
    import pytest

    with pytest.raises(ValueError, match="attempts_used"):
        store.record(record)
