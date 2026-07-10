"""Unit tests for QuestRunner orchestration edge cases."""

from __future__ import annotations

import pytest

from backend.core.errors import StateDetectionError
from worker.fgo import quest_runner as qr
from worker.fgo.enums import FgoState
from worker.fgo.quest_runner import QuestRunner


class DummyControl:
    def checkpoint(self) -> None:
        pass


class DummyContext:
    def __init__(self) -> None:
        self.control = DummyControl()
        self.completed_count = 0
        self.failure_count = 0
        self.last_error = None
        self.current_state = FgoState.UNKNOWN
        self.phases: list[tuple[str, str]] = []
        self.actions: list[str] = []

    def set_phase(self, phase: str, *, detail: str = "", clear_error: bool = True) -> None:
        self.phases.append((phase, detail))

    def set_phase_error(self, error: str) -> None:
        self.last_error = error

    def publish_status(self, **extra) -> None:
        pass

    def record_action(self, description: str) -> None:
        self.actions.append(description)


def test_handle_failure_does_not_abort_when_stop_on_failure_disabled(monkeypatch):
    ctx = DummyContext()
    runner = QuestRunner.__new__(QuestRunner)
    runner.ctx = ctx
    monkeypatch.setattr(runner, "_save_error_screenshot", lambda exc: None)

    should_abort = runner._handle_failure(RuntimeError("transient"), False, 1)

    assert should_abort is False
    assert ctx.failure_count == 1
    assert "RuntimeError: transient" == ctx.last_error


def test_handle_failure_aborts_at_threshold_when_enabled(monkeypatch):
    ctx = DummyContext()
    runner = QuestRunner.__new__(QuestRunner)
    runner.ctx = ctx
    monkeypatch.setattr(runner, "_save_error_screenshot", lambda exc: None)

    assert runner._handle_failure(RuntimeError("first"), True, 2) is False
    assert runner._handle_failure(RuntimeError("second"), True, 2) is True


def test_current_quest_mode_reenters_from_quest_detail(monkeypatch):
    ctx = DummyContext()
    runner = QuestRunner(ctx, quest_profile={"entry_mode": "current_quest"})
    calls: list[str] = []

    monkeypatch.setattr(qr.sm, "sense", lambda ctx: (FgoState.QUEST_DETAIL, None))
    monkeypatch.setattr(runner, "_enter_quest", lambda: calls.append("enter"))
    monkeypatch.setattr(runner.support, "select", lambda profile: calls.append("support"))
    monkeypatch.setattr(runner, "_confirm_party", lambda: calls.append("party"))
    monkeypatch.setattr(runner, "_run_battle_and_result", lambda: calls.append("battle"))

    runner.run_quest()

    assert calls == ["enter", "support", "party", "battle"]


def test_wait_for_next_sortie_takeover_accepts_stable_state(monkeypatch):
    ctx = DummyContext()
    runner = QuestRunner(ctx)
    states = iter([FgoState.UNKNOWN, FgoState.BATTLE_LOADING, FgoState.BATTLE_COMMAND])

    monkeypatch.setattr(qr.sm, "sense", lambda ctx: (next(states), None))
    monkeypatch.setattr(qr.time, "sleep", lambda seconds: None)

    runner._wait_for_next_sortie_takeover()


def test_wait_for_next_sortie_takeover_timeout_raises(monkeypatch):
    ctx = DummyContext()
    runner = QuestRunner(ctx)

    monkeypatch.setattr(qr.sm, "sense", lambda ctx: (FgoState.UNKNOWN, None))
    monkeypatch.setattr(qr.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(
        qr.time,
        "monotonic",
        iter([0.0, 1.0, 31.0]).__next__,
    )

    with pytest.raises(StateDetectionError):
        runner._wait_for_next_sortie_takeover()
