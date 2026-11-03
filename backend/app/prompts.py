"""Per-layer prompt templates for extracting a C4 diagram from source code.

Grounded in the same C4 notation rules baked into the frontend's demo data
(see c4-model-visualizer/claude_output/frontend_implementation.md):
relationships are labeled verb phrases, container-to-container relationships
name their technology/protocol, and diagrams stay under ~15-20 elements.
"""

from __future__ import annotations

from app.schemas import KINDS_BY_LAYER, Layer

LAYER_FRAMING: dict[Layer, str] = {
    "context": (
        "Act as the high-level Business Reference for the system's components and containers. "
        "Identify the core business capabilities/contexts delivered on top of the containers, "
        "the business personas/roles who interact with them, and the external business/platform "
        "systems integrated with the solution. Each in-scope system node should serve as a "
        "business capability reference explaining what domain context is worked on top of the containers."
    ),
    "container": (
        "Carry forward the upper-layer Business Context system(s) as enlarged, transparent-bordered "
        "boundaries (zoomed-in frames) and identify ALL deployable/runtime containers inside them: "
        "web apps, UI component suites, domain/agent libraries, state/query hooks, APIs/services, "
        "and databases/migrations. Name the concrete technology for each and include supporting "
        "business personas and external systems."
    ),
    "component": (
        "Carry forward EVERY in-scope Container from the Container layer as an enlarged, "
        "transparent-bordered boundary (`upperLayer: 'container'`) — imagine each container is "
        "zoomed in and opened up to explain the internal components inside it. Do NOT drop "
        "containers: extract the major internal components (routes, UI modules, services, queries, "
        "hooks, data/schema modules) inside every carried-forward container boundary."
    ),
    "code": (
        "Carry forward the upper-layer Components from the Component layer as enlarged, "
        "transparent-bordered boundaries (`upperLayer: 'component'`) and open each component up "
        "to show its key classes, interfaces, hooks, functions, and types inside its transparent border."
    ),
}

SYSTEM_PROMPT = """You are a software architect producing a C4 model diagram from source code.

Output STRICT JSON only — no markdown fences, no commentary before or after — matching exactly this shape:

{
  "boundaries": [
    {"id": "string", "label": "string", "position": {"x": number, "y": number}, "size": {"width": number, "height": number}}
  ],
  "nodes": [
    {
      "id": "string (unique, lowercase, hyphenated)",
      "type": "c4Node",
      "position": {"x": number, "y": number},
      "parentId": "string, optional — references a boundary id to nest this node inside it",
      "extent": "parent, optional — set this whenever parentId is set",
      "data": {
        "kind": "one of the allowed kinds for this layer, see below",
        "name": "string",
        "technology": "string or null",
        "description": "one or two sentences"
      }
    }
  ],
  "edges": [
    {
      "id": "string (unique)",
      "source": "a node id from the nodes array",
      "target": "a node id from the nodes array",
      "type": "c4Edge",
      "label": "a specific verb phrase, e.g. 'Reads from and writes to', not 'Uses'",
      "data": {"technology": "protocol/technology string or null"}
    }
  ]
}

Rules:
- Every node id referenced by an edge's source/target MUST exist in the nodes array.
- Keep the whole diagram under 15 elements (boundaries + nodes) — this is a key C4 density rule.
- Lay nodes out so they don't overlap: increment x/y in steps of at least 260/180 pixels between
  nodes, and size any boundary generously enough to contain its children with ~40px margin.
- WORKFLOW ORDER (required): place nodes left→right / top→bottom in real runtime flow —
  (1) people/actors, (2) UI/web clients, (3) auth/gateway, (4) domain APIs & agent services,
  (5) databases/stores, (6) external systems. Edges must reinforce that flow (user→UI→API→DB/external).
  Do NOT dump nodes alphabetically or in folder-discovery order.
- Only infer what the source code actually supports — if you're not confident about a
  technology or relationship, omit the detail rather than inventing specifics.
- If the repository genuinely doesn't contain enough information for this layer, return the
  closest reasonable best-effort diagram rather than an empty one.
"""


def build_prompt(layer: Layer, repo_context: str) -> tuple[str, str]:
    allowed_kinds = ", ".join(KINDS_BY_LAYER[layer])
    user_prompt = (
        f"C4 layer: {layer}\n\n"
        f"{LAYER_FRAMING[layer]}\n\n"
        f"Allowed values for data.kind at this layer: {allowed_kinds}\n\n"
        f"--- Repository context ---\n{repo_context}\n--- end repository context ---\n\n"
        "Produce the JSON now."
    )
    return SYSTEM_PROMPT, user_prompt


def build_repair_prompt(original_output: str, error: str) -> str:
    return (
        "Your previous response failed validation against the required JSON schema.\n\n"
        f"Validation error:\n{error}\n\n"
        f"Your previous response was:\n{original_output}\n\n"
        "Return a corrected, STRICT JSON response (no markdown fences, no commentary) that "
        "fixes this error while keeping everything else the same."
    )
