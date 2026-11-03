"""Shared C4 canvas spacing — keep nodes comfortably separated in the drawing area.

Frontend cards are ~200×118 (`C4Node.svelte` / `diagramData.js`). Steps must leave
a clear visual gap between cards and between boundary groups.
"""

from __future__ import annotations

# Element card stride (must exceed frontend card size + gap) — prefer L→R workflow lanes
NODE_STEP_X = 420
NODE_STEP_Y = 280

# Padding inside a zoomed-in boundary
BOUNDARY_PAD_X = 72
BOUNDARY_PAD_TOP = 140
BOUNDARY_PAD_BOTTOM = 72

# Gap between sibling boundary wrappers (NodeWrappers) — keep groups clearly separated
BOUNDARY_GAP_X = 280
BOUNDARY_GAP_Y = 220

# Left-rail actors / right-rail externals
RAIL_STEP_Y = 300
RAIL_LEFT_X = 30
RAIL_TOP_Y = 90

# Context / container grid inside the main business boundary
CONTEXT_CELL_X = 420
CONTEXT_CELL_Y = 280
CONTAINER_CELL_X = 420
CONTAINER_CELL_Y = 280
