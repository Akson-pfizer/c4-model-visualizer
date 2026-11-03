"""Workflow ordering should put UI before APIs before data/externals (L→R)."""

from __future__ import annotations

from app.schemas import Boundary, C4Edge, C4Node, LLMExtraction, NodeData, Position, Size
from app.workflow_layout import (
    apply_workflow_layout,
    assign_workflow_columns,
    order_nodes_by_workflow,
    workflow_tier,
)


def _node(nid: str, name: str, kind: str, **extra) -> C4Node:
    return C4Node(
        id=nid,
        position=Position(x=0, y=0),
        data=NodeData(
            kind=kind,
            name=name,
            technology=extra.get("tech"),
            description=extra.get("desc") or name,
        ),
        parentId=extra.get("parent"),
        extent="parent" if extra.get("parent") else None,
    )


def test_workflow_tiers_prefer_ui_before_data() -> None:
    ui = _node("ui", "Cggenai UI Container", "container", tech="React")
    db = _node("db", "Platform Relational Data Store", "containerDb", tech="SQL")
    assert workflow_tier(ui) < workflow_tier(db)


def test_order_nodes_by_workflow_uses_edges() -> None:
    a = _node("a", "UI App", "container", tech="React")
    b = _node("b", "Content API", "container", tech="FastAPI")
    c = _node("c", "Rules Service", "container", tech="FastAPI", desc="rule management")
    edges = [
        C4Edge(id="e1", source="a", target="b", label="calls"),
        C4Edge(id="e2", source="b", target="c", label="calls"),
    ]
    ordered = order_nodes_by_workflow([c, b, a], edges)
    assert [n.id for n in ordered] == ["a", "b", "c"]


def test_assign_workflow_columns_is_left_to_right() -> None:
    ui = _node("ui", "UI Container", "container", tech="React")
    api = _node("api", "Ms Content", "container", tech="API")
    db = _node("db", "Data Store", "containerDb")
    ext = _node("ext", "LLM Hub", "systemExternal")
    cols = assign_workflow_columns([db, ext, api, ui], [])
    assert cols["ui"] < cols["api"] < cols["db"] <= cols["ext"]


def test_apply_workflow_layout_places_children_left_to_right() -> None:
    boundary = Boundary(
        id="b1",
        label="Platform",
        position=Position(x=40, y=40),
        size=Size(width=800, height=600),
    )
    nodes = [
        _node("db", "Data Store", "containerDb", parent="b1"),
        _node("ui", "UI Container", "container", tech="React", parent="b1"),
        _node("api", "Ms Content", "container", tech="API", parent="b1"),
        _node("agent", "Bodhi Agent", "container", tech="FastAPI", desc="agentic content", parent="b1"),
    ]
    extraction = LLMExtraction(boundaries=[boundary], nodes=nodes, edges=[])
    result = apply_workflow_layout(extraction, "container")
    by_id = {n.id: n for n in result.nodes}
    assert by_id["ui"].position.x < by_id["api"].position.x
    assert by_id["api"].position.x < by_id["agent"].position.x
    assert by_id["agent"].position.x < by_id["db"].position.x


def test_apply_workflow_layout_persons_left_externals_right() -> None:
    person = _node("p1", "Marketing Users", "person")
    system = _node("s1", "Platform", "system", tech="Java")
    external = _node("e1", "Enterprise SSO", "systemExternal")
    extraction = LLMExtraction(boundaries=[], nodes=[external, system, person], edges=[])
    result = apply_workflow_layout(extraction, "context")
    by_id = {n.id: n for n in result.nodes}
    assert by_id["p1"].position.x < by_id["s1"].position.x < by_id["e1"].position.x


def test_separate_overlapping_nodes_clears_collisions() -> None:
    from app.workflow_layout import separate_overlapping_nodes

    a = _node("a", "Filter", "component", tech="Spring")
    b = _node("b", "LLM Service", "component", tech="Python")
    a.position = Position(x=100, y=100)
    b.position = Position(x=120, y=140)  # heavily overlaps a
    separate_overlapping_nodes([a, b], [])
    # Cards are 200×118 with clearance — centers must not share the same box.
    ax2, ay2 = a.position.x + 200 + 56, a.position.y + 118 + 48
    assert b.position.x >= ax2 or b.position.y >= ay2
