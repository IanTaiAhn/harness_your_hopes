"""Context-management strategies applied to `messages` before each chat() call.

Implement exactly 2 of the 3 — pick the pair you want to compare and
delete/leave-unimplemented the third.
"""
from __future__ import annotations


def summarize_old_turns(messages: list[dict], keep_last: int = 6) -> list[dict]:
    # TODO: messages[:-keep_last] -> one summary message (heuristic or a
    #       second cheap model call); messages[-keep_last:] kept verbatim
    raise NotImplementedError


def drop_tool_outputs(messages: list[dict], keep_last_outputs: int = 3) -> list[dict]:
    # TODO: walk messages, for tool-role messages beyond the most recent
    #       keep_last_outputs, replace content with a short "[output omitted]"
    #       placeholder but keep the preceding assistant tool_call intact
    raise NotImplementedError


def full_reset_from_state(messages: list[dict], progress) -> list[dict]:
    # TODO: build a fresh messages list from Project 2's Progress object —
    #       system prompt + a "resume" user message summarizing
    #       steps_completed/steps_remaining — discarding everything else
    raise NotImplementedError
