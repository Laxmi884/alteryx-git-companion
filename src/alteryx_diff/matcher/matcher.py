"""Node matcher implementation for alteryx_diff.

Two-pass node matching:
  Pass 1 (this file): Exact ToolID lookup — O(n), handles common case.
  Pass 2 (Plan 02):   Hungarian algorithm per tool-type — handles ToolID churn.
"""

from __future__ import annotations

from dataclasses import dataclass

from alteryx_diff.models import NormalizedNode

COST_THRESHOLD = 0.8


@dataclass(frozen=True, kw_only=True, slots=True)
class MatchResult:
    """Output of the two-pass node matcher.

    matched: pairs of (old_node, new_node) successfully paired
    removed: nodes in old workflow absent from new (genuine removals)
    added:   nodes in new workflow absent from old (genuine additions)
    """

    matched: tuple[tuple[NormalizedNode, NormalizedNode], ...]
    removed: tuple[NormalizedNode, ...]
    added: tuple[NormalizedNode, ...]


def match(
    old_nodes: list[NormalizedNode],
    new_nodes: list[NormalizedNode],
) -> MatchResult:
    """Two-pass node matcher. Pass 1: exact ToolID. Pass 2: Hungarian per-type."""
    matched: list[tuple[NormalizedNode, NormalizedNode]] = []

    # Pass 1: exact ToolID lookup — O(n)
    new_by_id = {n.source.tool_id: n for n in new_nodes}
    unmatched_old: list[NormalizedNode] = []
    matched_new_ids: set[int] = set()

    for old in old_nodes:
        if old.source.tool_id in new_by_id:
            matched.append((old, new_by_id[old.source.tool_id]))
            matched_new_ids.add(old.source.tool_id)
        else:
            unmatched_old.append(old)

    unmatched_new = [n for n in new_nodes if n.source.tool_id not in matched_new_ids]

    # Pass 2: Hungarian fallback — skip entirely if nothing left to match
    if unmatched_old and unmatched_new:
        extra_matched, remaining_old, remaining_new = _hungarian_match(
            unmatched_old, unmatched_new
        )
        matched.extend(extra_matched)
        unmatched_old = remaining_old
        unmatched_new = remaining_new

    return MatchResult(
        matched=tuple(matched),
        removed=tuple(unmatched_old),
        added=tuple(unmatched_new),
    )


def _hungarian_match(
    unmatched_old: list[NormalizedNode],
    unmatched_new: list[NormalizedNode],
) -> tuple[
    list[tuple[NormalizedNode, NormalizedNode]],
    list[NormalizedNode],
    list[NormalizedNode],
]:
    """Hungarian algorithm fallback — implemented in Plan 02 (_cost.py)."""
    raise NotImplementedError("Hungarian pass not yet implemented")
