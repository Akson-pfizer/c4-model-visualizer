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
        "Identify the software system(s) this repository implements, the people/actors "
        "who use it, and any external systems it integrates with (databases-as-a-service, "
        "third-party APIs, other internal systems it calls or is called by). "
        "This is the big-picture view for a non-technical audience — no technology details."
    ),
    "container": (
        "Identify the deployable/runnable units inside this system: web apps, APIs/services, "
        "background workers, CLIs, databases, queues. For each, name the concrete technology "
        "(language, framework, datastore engine) you can see evidence of in the source. "
        "Include the people/external systems from the context view as supporting nodes if they "
        "directly interact with a container."
    ),
    "component": (
        "Zoom into ONE container (pick the most central one, e.g. the main API/service) and "
        "identify its major internal building blocks — controllers, services, repositories, "
        "facades — and their responsibilities. Include the containers/external systems that "
        "directly call into or are called by this container's components as supporting nodes."
    ),
    "code": (
        "Zoom into ONE component from the container above and identify its key classes, "
        "interfaces, and enums, and how they relate (implements/uses/extends). "
        "Keep this small and illustrative — C4 guidance recommends against hand-modelling "
        "this level in real projects; this is a best-effort illustrative snapshot only."
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
