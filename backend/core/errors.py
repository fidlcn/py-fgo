"""Controlled exceptions used across backend and worker.

These map to spec section 13. Every worker failure is reported as one of
these so the runtime can translate it into a structured event / HTTP error
rather than letting a raw traceback escape.

Note: the worker imports these from here, so this module must stay free of
heavy third-party imports.
"""

from __future__ import annotations


class FgoError(Exception):
    """Base class for all controlled application errors."""

    code: str = "FGO_ERROR"

    def __init__(self, message: str = "", *, code: str | None = None) -> None:
        super().__init__(message)
        if code:
            self.code = code

    @property
    def message(self) -> str:
        return self.args[0] if self.args else ""


# --- ADB / device -----------------------------------------------------------


class ADBError(FgoError):
    """A generic ADB command failure (non-zero exit, unexpected output)."""

    code = "ADB_ERROR"


class ADBTimeoutError(ADBError):
    """An ADB command exceeded its timeout."""

    code = "ADB_TIMEOUT"


class DeviceOfflineError(FgoError):
    """The target device is not reachable via ADB."""

    code = "DEVICE_OFFLINE"


# --- Vision / state ---------------------------------------------------------


class StateDetectionError(FgoError):
    """Could not determine the current FGO state within the timeout."""

    code = "STATE_DETECTION_FAILED"


# --- Execution / task lifecycle --------------------------------------------


class ActionExecutionError(FgoError):
    """An action (tap, swipe, skill) could not be performed."""

    code = "ACTION_FAILED"


class TaskStoppedError(FgoError):
    """Raised inside a worker loop when a stop has been requested.

    This is a control-flow signal, not a crash: the loop catches it and
    exits cleanly at a safe point.
    """

    code = "TASK_STOPPED"


class TaskPausedError(FgoError):
    """Raised inside a worker loop when a pause has been requested.

    Like TaskStoppedError, a control-flow signal.
    """

    code = "TASK_PAUSED"


# --- Domain errors ----------------------------------------------------------


class SupportNotFoundError(FgoError):
    """No matching support could be found and fallback is disabled."""

    code = "SUPPORT_NOT_FOUND"


class BattlePlanError(FgoError):
    """A battle plan is invalid or cannot be executed as written."""

    code = "BATTLE_PLAN_ERROR"


class APInsufficientError(FgoError):
    """AP is insufficient and recovery is disabled or exhausted."""

    code = "AP_INSUFFICIENT"


class NotFoundError(FgoError):
    """A referenced resource (instance, profile, task) does not exist."""

    code = "NOT_FOUND"


class ValidationError(FgoError):
    """A request failed domain validation."""

    code = "VALIDATION_ERROR"


class ConflictError(FgoError):
    """A request conflicts with current state (e.g. duplicate device id)."""

    code = "CONFLICT"
