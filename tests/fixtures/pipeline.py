"""Minimal .yxmd XML byte fixtures for pipeline integration tests.

ToolIDs 601+ allocated for Phase 6. No collision with Phases 1-5 (max 499).
Write bytes to tmp_path in tests — do NOT commit .yxmd files to disk.
"""

from __future__ import annotations

# Single Filter tool — base version
MINIMAL_YXMD_A: bytes = b"""<?xml version="1.0"?>
<AlteryxDocument yxmdVer="2020.1">
  <Nodes>
    <Node ToolID="601">
      <GuiSettings Plugin="AlteryxBasePluginsGui.Filter">
        <Position x="60" y="100"/>
      </GuiSettings>
      <Properties>
        <Configuration>
          <Expression>Field1 > 0</Expression>
        </Configuration>
      </Properties>
    </Node>
  </Nodes>
  <Connections/>
</AlteryxDocument>"""

# Same tool, different filter expression — produces one modified node diff
MINIMAL_YXMD_B: bytes = b"""<?xml version="1.0"?>
<AlteryxDocument yxmdVer="2020.1">
  <Nodes>
    <Node ToolID="601">
      <GuiSettings Plugin="AlteryxBasePluginsGui.Filter">
        <Position x="60" y="100"/>
      </GuiSettings>
      <Properties>
        <Configuration>
          <Expression>Field1 > 10</Expression>
        </Configuration>
      </Properties>
    </Node>
  </Nodes>
  <Connections/>
</AlteryxDocument>"""

# Identical content for both sides — produces empty DiffResult
IDENTICAL_YXMD: bytes = MINIMAL_YXMD_A
