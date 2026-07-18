"""Run context: ties together settings, state, dry-run mode, logging, and notifications."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from gtm_forge.config import Settings
from gtm_forge.core.logging import get_logger
from gtm_forge.core.notify import notify_run_finished
from gtm_forge.core.state import StateStore


@dataclass
class RunContext:
    """One per CLI invocation. Records the run and fires notifications on exit."""

    settings: Settings
    state: StateStore
    dry_run: bool = False
    skill: str = "cli"
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def __post_init__(self) -> None:
        self.log = get_logger(f"gtm_forge.{self.skill}")

    def begin(self, command: str) -> RunContext:
        self.state.start_run(self.run_id, self.skill, command, self.dry_run)
        self.log.info("run started", extra={"run_id": self.run_id, "skill": self.skill})
        return self

    def end(self, status: str = "success", error: str | None = None) -> None:
        self.state.finish_run(self.run_id, status, error)
        cost = self.state.run_cost(self.run_id)
        self.log.info(
            "run finished",
            extra={"run_id": self.run_id, "skill": self.skill, "status": status, "cost_usd": cost},
        )
        notify_run_finished(
            self.settings,
            skill=self.skill,
            status=status,
            run_id=self.run_id,
            cost_usd=cost,
            error=error,
            dry_run=self.dry_run,
        )

    def fail(self, error: str) -> None:
        self.end(status="failed", error=error)

    def plan(self, steps: list[str], **extra: Any) -> dict[str, Any]:
        """Standard dry-run payload: what *would* happen, in order."""
        return {
            "dry_run": True,
            "run_id": self.run_id,
            "skill": self.skill,
            "steps": steps,
            **extra,
        }
