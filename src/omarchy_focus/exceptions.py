"""Application-specific exceptions."""


class OmarchyFocusError(Exception):
    """Base exception for the application."""


class TaskNotFoundError(OmarchyFocusError):
    """Raised when a task is not found."""


class PomodoroError(OmarchyFocusError):
    """Raised for invalid pomodoro actions."""


class FocusModeError(OmarchyFocusError):
    """Raised when focus mode operations fail."""
