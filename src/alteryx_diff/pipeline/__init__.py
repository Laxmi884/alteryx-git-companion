"""Pipeline orchestration stage for alteryx_diff.

Public surface: run(), DiffRequest, DiffResponse

  from alteryx_diff.pipeline import run, DiffRequest, DiffResponse
  response = run(DiffRequest(path_a=path_a, path_b=path_b))
"""

from __future__ import annotations

from alteryx_diff.pipeline.pipeline import DiffRequest, DiffResponse, run

__all__ = ["DiffRequest", "DiffResponse", "run"]
