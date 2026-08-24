"""Allowlist enforcement — application-level gate, NOT the security boundary.

This is still your own code policing itself; the real boundary is the
container/sandbox underneath (see README). This module's job is to fail
loudly and log, not to be trusted as sufficient on its own.
"""
from __future__ import annotations

from pathlib import Path


class PolicyViolation(Exception):
    pass


class Allowlist:
    def __init__(self, roots: list[str]):
        self.roots = [Path(r).resolve() for r in roots]

    def check(self, path: str) -> Path:
        """Resolve `path` and confirm it falls under an allowed root.

        Raises PolicyViolation if not. Always compare resolved paths —
        never raw strings — or `..`, junctions, and 8.3 short names slip
        through.
        """
        # TODO: resolved = Path(path).resolve()
        #       for root in self.roots: if resolved is relative to root, return resolved
        #       raise PolicyViolation(f"{path} -> {resolved} outside allowlist")
        raise NotImplementedError

    def requires_confirmation(self, action: str) -> bool:
        return action in {"delete", "overwrite"}
