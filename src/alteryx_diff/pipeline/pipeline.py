from __future__ import annotations

import pathlib
from dataclasses import dataclass

from alteryx_diff.differ import diff
from alteryx_diff.matcher import match
from alteryx_diff.models import DiffResult
from alteryx_diff.normalizer import normalize
from alteryx_diff.parser import parse


@dataclass(frozen=True, kw_only=True, slots=True)
class DiffRequest:
    """Input to pipeline.run(): paths to two .yxmd files to compare."""

    path_a: pathlib.Path
    path_b: pathlib.Path


@dataclass(frozen=True, kw_only=True, slots=True)
class DiffResponse:
    """Output of pipeline.run(): the completed DiffResult."""

    result: DiffResult


def run(request: DiffRequest) -> DiffResponse:
    """Execute the full diff pipeline for two .yxmd files.

    Raises:
        MissingFileError: If either path does not exist.
        UnreadableFileError: If either path exists but cannot be read.
        MalformedXMLError: If either file contains invalid XML.

    Does NOT call sys.exit(), print(), or perform any file I/O beyond
    reading the two input .yxmd files via parser.parse().
    """
    doc_a, doc_b = parse(request.path_a, request.path_b)
    norm_a = normalize(doc_a)
    norm_b = normalize(doc_b)
    match_result = match(list(norm_a.nodes), list(norm_b.nodes))
    diff_result = diff(match_result, doc_a.connections, doc_b.connections)
    return DiffResponse(result=diff_result)
