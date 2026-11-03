"""Reorder C4 nodes into left-to-right *workflow* lanes on every layer.

Actors / inputs sit left; UI → auth → APIs → domain services follow in columns;
data stores and external sinks land on the right (last reached).
"""

from __future__ import annotations

import re
from collections import defaultdict, deque

from app.layout_spacing import (
    BOUNDARY_PAD_BOTTOM,
    BOUNDARY_PAD_TOP,
    BOUNDARY_PAD_X,
    CONTAINER_CELL_X,
    CONTAINER_CELL_Y,
    NODE_STEP_X,
    NODE_STEP_Y,
    RAIL_LEFT_X,
    RAIL_STEP_Y,
    RAIL_TOP_Y,
)
from app.schemas import Boundary, C4Edge, C4Node, LLMExtraction, Position, Size

_UI_HINTS = re.compile(
    r"\b(ui|frontend|front-end|web|spa|portal|client|react|angular|vue|next)\b",
    re.I,
)
_AUTH_HINTS = re.compile(r"\b(auth|sso|identity|login|oauth|saml|gateway|bff)\b", re.I)
_API_HINTS = re.compile(r"\b(api|service|ms-|microservice|backend|server|fastapi|spring)\b", re.I)
_AGENT_HINTS = re.compile(r"\b(agent|bodhi|docintel|llm|fabric|rule|orchestr)\b", re.I)
_DATA_HINTS = re.compile(r"\b(db|database|postgres|sql|store|redis|mongo|data)\b", re.I)


def workflow_tier(node: C4Node) -> int:
    """Lower = earlier in the user/system workflow (left)."""
    kind = (node.data.kind or "").strip()
    hay = f"{node.data.name} {node.data.technology or ''} {node.data.description or ''}"

    if kind == "person":
        return 0
    if kind in {"systemExternal", "containerExternal"}:
        return 90
    if kind == "containerDb" or (kind.startswith("container") and _DATA_HINTS.search(hay)):
        return 80
    if kind in {"system"} and _DATA_HINTS.search(hay):
        return 80
    if _UI_HINTS.search(hay):
        return 10
    if _AUTH_HINTS.search(hay):
        return 20
    if _AGENT_HINTS.search(hay):
        return 45
    if _API_HINTS.search(hay) or kind in {"container", "component", "system"}:
        return 30
    if kind.startswith("code"):
        if kind == "codeInterface":
            return 50
        if kind == "codeClass":
            return 55
        return 60
    return 40


def _topo_within_tier(nodes: list[C4Node], edges: list[C4Edge]) -> list[C4Node]:
    """Stable topological sort; isolated nodes keep relative order."""
    ids = {n.id for n in nodes}
    index = {n.id: i for i, n in enumerate(nodes)}
    indeg: dict[str, int] = {n.id: 0 for n in nodes}
    adj: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        if edge.source in ids and edge.target in ids and edge.source != edge.target:
            adj[edge.source].append(edge.target)
            indeg[edge.target] = indeg.get(edge.target, 0) + 1

    ready = sorted(
        [n.id for n in nodes if indeg.get(n.id, 0) == 0],
        key=lambda nid: index[nid],
    )
    q: deque[str] = deque(ready)
    ordered_ids: list[str] = []
    while q:
        cur = q.popleft()
        ordered_ids.append(cur)
        for nxt in sorted(adj.get(cur, []), key=lambda nid: index[nid]):
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                q.append(nxt)

    remaining = [n.id for n in nodes if n.id not in set(ordered_ids)]
    ordered_ids.extend(remaining)
    by_id = {n.id: n for n in nodes}
    return [by_id[i] for i in ordered_ids]


def order_nodes_by_workflow(nodes: list[C4Node], edges: list[C4Edge]) -> list[C4Node]:
    """Sort nodes into workflow order (tier, then edge topology, then name)."""
    buckets: dict[int, list[C4Node]] = defaultdict(list)
    for node in nodes:
        buckets[workflow_tier(node)].append(node)

    ordered: list[C4Node] = []
    for tier in sorted(buckets):
        group = buckets[tier]
        group.sort(key=lambda n: (n.data.name or n.id).lower())
        ordered.extend(_topo_within_tier(group, edges))
    return ordered


def assign_workflow_columns(nodes: list[C4Node], edges: list[C4Edge]) -> dict[str, int]:
    """Map each node to a left→right column (inputs left, sinks right).

    Combines longest-path depth along edges with a workflow-tier floor so data
    stores / externals stay to the right even when edges are sparse.
    """
    if not nodes:
        return {}

    ids = {n.id for n in nodes}
    indeg: dict[str, int] = {n.id: 0 for n in nodes}
    succ: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        if edge.source in ids and edge.target in ids and edge.source != edge.target:
            succ[edge.source].append(edge.target)
            indeg[edge.target] = indeg.get(edge.target, 0) + 1

    depth: dict[str, int] = {n.id: 0 for n in nodes}
    indeg_work = dict(indeg)
    q: deque[str] = deque([n.id for n in nodes if indeg_work[n.id] == 0])
    seen: set[str] = set()
    while q:
        cur = q.popleft()
        if cur in seen:
            continue
        seen.add(cur)
        for nxt in succ.get(cur, []):
            depth[nxt] = max(depth[nxt], depth[cur] + 1)
            indeg_work[nxt] -= 1
            if indeg_work[nxt] == 0:
                q.append(nxt)

    tiers = {n.id: workflow_tier(n) for n in nodes}
    unique_tiers = sorted(set(tiers.values()))
    tier_floor = {t: i for i, t in enumerate(unique_tiers)}

    raw = {
        n.id: max(depth[n.id], tier_floor[tiers[n.id]]) for n in nodes
    }
    used = sorted(set(raw.values()))
    remap = {v: i for i, v in enumerate(used)}
    return {nid: remap[c] for nid, c in raw.items()}


def place_nodes_in_lanes(
    nodes: list[C4Node],
    edges: list[C4Edge],
    *,
    step_x: int,
    step_y: int,
    pad_x: int,
    pad_top: int,
) -> None:
    """Place nodes in L→R columns; stack vertically within each column."""
    if not nodes:
        return
    columns = assign_workflow_columns(nodes, edges)
    ordered = order_nodes_by_workflow(nodes, edges)
    by_col: dict[int, list[C4Node]] = defaultdict(list)
    for node in ordered:
        by_col[columns[node.id]].append(node)

    for col in sorted(by_col):
        for row, node in enumerate(by_col[col]):
            node.position = Position(
                x=pad_x + col * step_x,
                y=pad_top + row * step_y,
            )


_CARD_W = 200
_CARD_H = 118
_CLEAR_X = 56
_CLEAR_Y = 48


def separate_overlapping_nodes(
    nodes: list[C4Node],
    edges: list[C4Edge],
    *,
    card_w: int = _CARD_W,
    card_h: int = _CARD_H,
    clear_x: int = _CLEAR_X,
    clear_y: int = _CLEAR_Y,
    max_passes: int = 48,
) -> None:
    """Hard rule: node cards must not overlap (all layers). Later cards move down/right."""
    if len(nodes) < 2:
        return

    ranked = order_nodes_by_workflow(nodes, edges)
    ranked = sorted(
        ranked,
        key=lambda n: (n.position.y, n.position.x, (n.data.name or n.id).lower()),
    )

    def _overlap(ax: float, ay: float, bx: float, by: float) -> bool:
        aw, ah = card_w + clear_x, card_h + clear_y
        bw, bh = card_w + clear_x, card_h + clear_y
        return not (ax + aw <= bx or bx + bw <= ax or ay + ah <= by or by + bh <= ay)

    for _ in range(max_passes):
        moved = False
        for i, a in enumerate(ranked):
            for b in ranked[i + 1 :]:
                if not _overlap(a.position.x, a.position.y, b.position.x, b.position.y):
                    continue
                push_right = (a.position.x + card_w + clear_x) - b.position.x
                push_down = (a.position.y + card_h + clear_y) - b.position.y
                if push_down > 0 and push_down <= push_right:
                    b.position = Position(x=b.position.x, y=b.position.y + int(push_down))
                elif push_right > 0:
                    b.position = Position(x=b.position.x + int(push_right), y=b.position.y)
                elif push_down > 0:
                    b.position = Position(x=b.position.x, y=b.position.y + int(push_down))
                moved = True
        if not moved:
            break


def _resize_boundary_to_children(
    boundary: Boundary,
    children: list[C4Node],
    *,
    card_w: int = 200,
    card_h: int = 118,
) -> None:
    if not children:
        return
    max_r = max(n.position.x + card_w for n in children)
    max_b = max(n.position.y + card_h for n in children)
    boundary.size = Size(
        width=max(int(boundary.size.width), int(max_r + BOUNDARY_PAD_X)),
        height=max(int(boundary.size.height), int(max_b + BOUNDARY_PAD_BOTTOM)),
    )


def apply_workflow_layout(extraction: LLMExtraction, layer: str) -> LLMExtraction:
    """Rewrite positions so every layer reads left→right as a workflow."""
    nodes = list(extraction.nodes)
    edges = list(extraction.edges)
    boundaries = list(extraction.boundaries)
    if not nodes:
        return extraction

    by_parent: dict[str | None, list[C4Node]] = defaultdict(list)
    for node in nodes:
        by_parent[node.parentId].append(node)

    boundary_by_id = {b.id: b for b in boundaries}

    step_x = NODE_STEP_X if layer in {"component", "code"} else CONTAINER_CELL_X
    step_y = NODE_STEP_Y if layer in {"component", "code"} else CONTAINER_CELL_Y

    # Nested cards inside boundaries — one workflow lane (column) per stage.
    for parent_id, group in by_parent.items():
        if parent_id is None:
            continue
        place_nodes_in_lanes(
            group,
            edges,
            step_x=step_x,
            step_y=step_y,
            pad_x=BOUNDARY_PAD_X,
            pad_top=BOUNDARY_PAD_TOP,
        )
        separate_overlapping_nodes(group, edges)
        boundary = boundary_by_id.get(parent_id)
        if boundary is not None:
            _resize_boundary_to_children(boundary, group)

    # Free (unparented) nodes — left persons, center runtime lanes, right sinks.
    free = by_parent.get(None) or []
    if free:
        persons = order_nodes_by_workflow(
            [n for n in free if n.data.kind == "person"], edges
        )
        externals = order_nodes_by_workflow(
            [
                n
                for n in free
                if n.data.kind in {"systemExternal", "containerExternal"}
                or workflow_tier(n) >= 80
            ],
            edges,
        )
        middle = order_nodes_by_workflow(
            [n for n in free if n not in persons and n not in externals],
            edges,
        )

        for idx, node in enumerate(persons):
            node.position = Position(x=RAIL_LEFT_X, y=RAIL_TOP_Y + idx * RAIL_STEP_Y)

        if boundaries:
            max_bx = max(b.position.x + b.size.width for b in boundaries)
            mid_x = int(min(b.position.x for b in boundaries))
            # Sit free middle nodes to the right of left rail / near boundary cluster.
            if mid_x < 280:
                mid_x = 280
            right_x = int(max_bx + 80)
        else:
            mid_x = 340
            right_x = mid_x + 4 * step_x + 80

        place_nodes_in_lanes(
            middle,
            edges,
            step_x=step_x,
            step_y=step_y,
            pad_x=mid_x,
            pad_top=RAIL_TOP_Y,
        )

        # Right rail: last-reached externals / data — stack top→bottom.
        for idx, node in enumerate(externals):
            node.position = Position(x=right_x, y=RAIL_TOP_Y + idx * RAIL_STEP_Y)

        if not boundaries and middle:
            for node in middle:
                if node.position.x < 200:
                    node.position.x = 340 + (node.position.x - mid_x)

        # Hard rule: free cards must not overlap either.
        separate_overlapping_nodes(free, edges)

    return LLMExtraction(boundaries=boundaries, nodes=nodes, edges=edges)
