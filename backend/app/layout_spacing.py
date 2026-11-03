"""Shared C4 canvas spacing — keep nodes comfortably separated in the drawing area.

Frontend cards are ~200×118 (`C4Node.svelte` / `diagramData.js`). Steps must leave
a clear visual gap between cards and between boundary groups.
"""

from __future__ import annotations

# Element card stride (must exceed frontend card size + gap)
NODE_STEP_X = 360
NODE_STEP_Y = 250

# Padding inside a zoomed-in boundary
BOUNDARY_PAD_X = 56
BOUNDARY_PAD_TOP = 128
BOUNDARY_PAD_BOTTOM = 56

# Gap between sibling boundaries / outer columns
BOUNDARY_GAP_X = 110
BOUNDARY_GAP_Y = 100

# Left-rail actors / right-rail externals
RAIL_STEP_Y = 270
RAIL_LEFT_X = 30
RAIL_TOP_Y = 90

# Context / container grid inside the main business boundary
CONTEXT_CELL_X = 360
CONTEXT_CELL_Y = 250
CONTAINER_CELL_X = 360
CONTAINER_CELL_Y = 260
