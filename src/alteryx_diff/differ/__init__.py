"""Diff engine pipeline stage for alteryx_diff.

Public surface: diff()

  from alteryx_diff.differ import diff
  result = diff(match_result, old_connections, new_connections)
"""

from __future__ import annotations

from alteryx_diff.differ.differ import diff

__all__ = ["diff"]
