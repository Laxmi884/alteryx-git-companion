"""Node matcher pipeline stage for alteryx_diff.

Public surface: match(), MatchResult

  from alteryx_diff.matcher import match, MatchResult
  result = match(old_nodes, new_nodes)  # list[NormalizedNode] x2 -> MatchResult
"""

from alteryx_diff.matcher.matcher import MatchResult, match

__all__ = ["match", "MatchResult"]
