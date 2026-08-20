"""Contracts for deterministic, in-memory experimental tools."""

from __future__ import annotations

from abc import ABC, abstractmethod

from iqa_soa.types import Action, ToolResult


class SandboxedTool(ABC):
    """A tool implementation that is restricted to :class:`SandboxState`.

    Tool implementations receive an action but never a filesystem path, network
    client, or process handle.  This makes the safety boundary explicit and also
    keeps paired experimental runs reproducible.
    """

    name: str

    @abstractmethod
    def execute(self, action: Action) -> ToolResult:
        """Execute *action* against in-memory state only."""


__all__ = ["SandboxedTool"]
