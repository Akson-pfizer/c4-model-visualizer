# C4 Model Visualiser

A read-only demo UI for navigating the four layers of the [C4 model](https://c4model.com)
— System Context, Container, Component, and Code — as interactive node/edge
diagrams, built with Svelte 5 and [Svelte Flow](https://svelteflow.dev).

## The idea

The [C4 model](https://c4model.com) describes software architecture at four
zoom levels, each for a different audience:

| Layer | Shows | Audience |
|---|---|---|
| **Context** | The system and the people/external systems it talks to | Everyone, non-technical included |
| **Container** | The applications and data stores inside the system | Architects, tech leads |
| **Component** | The internal building blocks of one container | Developers working on that container |
| **Code** | Classes/interfaces inside one component | The developer currently in that code (and per C4 guidance, this level shouldn't really be hand-drawn — see the in-app note) |

This app lets you switch between those four layers from one dropdown and see
each one rendered as a proper diagram — typed boxes, labelled relationships,
boundary frames, a legend — rather than a static picture. All four layers zoom
into the *same* worked example (the canonical "Internet Banking System" from
c4model.com/Structurizr), so Context → Container → Component → Code actually
drill into each other instead of being four unrelated screenshots.

It's a frontend-only visualiser: the diagram data is static demo JSON rather
than coming from a live backend, but it's shaped exactly like an API response
would be — see [Implementation](#implementation) below — so wiring up a real
backend later is a small change, not a rewrite.

## What you'll see

- **Header**: a "C4 Model Visualiser" mark top-left, the layer-select dropdown
  in the middle, a Pfizer wordmark top-right (placeholder — see note below).
- **Dropdown**: click it (or Tab to it and press Enter) to pick a layer. Full
  keyboard support — arrow keys to move, Enter to select, Escape to close.
- **Canvas**: the selected layer's diagram, pannable/zoomable, with a legend,
  minimap, and zoom controls.
- **Side panel**: click any box on the canvas to see its full description,
  technology, and type. Click elsewhere (or the ✕) to clear the selection.
- Switching layers crossfades out the old diagram and fades in the new one.

> **Note on the Pfizer mark**: it's a placeholder text wordmark, not the real
> Pfizer logo asset — no official logo image was available to embed, and
> reproducing a trademarked logo programmatically isn't appropriate. Swap
> `.pfizer-mark` in `src/lib/components/AppHeader.svelte` for the real asset
> before this is shown to anyone outside this exercise.

## Implementation

**Stack**: Svelte 5 (runes) + Vite, [@xyflow/svelte](https://svelteflow.dev)
for the diagrams, plain CSS custom properties for the soft white/blue theme.
No SvelteKit — this is a single-page app with four view-states, not a
multi-route site.

```
src/
├── App.svelte               # layer state + crossfade transition
├── app.css                  # theme tokens (soft white / blue palette)
└── lib/
    ├── diagramData.js       # adapts data/*.json → Svelte Flow's node/edge shape
    ├── c4Kinds.js           # visual metadata (colour, shape, stereotype) per element kind
    ├── data/
    │   ├── context.json     # one JSON file per C4 layer — see schema below
    │   ├── container.json
    │   ├── component.json
    │   └── code.json
    └── components/
        ├── AppHeader.svelte     # brand mark · layer dropdown · Pfizer mark
        ├── LayerSelect.svelte   # accessible combobox-style dropdown
        ├── DiagramCanvas.svelte # wraps SvelteFlowProvider
        ├── FlowInner.svelte     # the actual <SvelteFlow> diagram
        ├── DetailPanel.svelte   # layer / selected-node description
        ├── Legend.svelte
        ├── nodes/{C4Node,C4Boundary}.svelte
        └── edges/C4Edge.svelte
```

### Data shape

Each `data/*.json` file is shaped like what a real backend endpoint
(`GET /api/c4/{layer}`) should return:

```jsonc
{
  "layer": "container",
  "title": "Container",
  "description": "...",           // shown in the side panel by default
  "note": null,                   // optional callout, e.g. Code layer's "don't hand-model this"
  "legend": [{ "kind": "container", "label": "Container" }, ...],
  "boundaries": [                 // optional System/Container frames
    { "id": "ibs-boundary", "label": "Internet Banking System",
      "position": { "x": 260, "y": 40 }, "size": { "width": 820, "height": 400 } }
  ],
  "nodes": [
    { "id": "apiapp", "type": "c4Node", "position": { "x": 300, "y": 220 },
      "parentId": "ibs-boundary", "extent": "parent",
      "data": { "kind": "container", "name": "API Application",
                "technology": "Java, Docker Container", "description": "..." } }
  ],
  "edges": [
    { "id": "e-api-db", "source": "apiapp", "target": "database", "type": "c4Edge",
      "label": "Reads from and writes to", "data": { "technology": "JDBC" } }
  ]
}
```

`diagramData.js` is the one place that adapts this into Svelte Flow's shape
(turning `boundaries[]` into actual nodes, etc.) — pointing its imports at a
`fetch()` call instead of static JSON is the only change a real backend
integration needs.

For the full design rationale (why a combobox instead of `<select>`, why the
side panel instead of inline canvas text, the research this traces back to,
and some implementation gotchas worth knowing about) see
[`claude_output/frontend_implementation.md`](../claude_output/frontend_implementation.md)
at the project root.

## How to run

### Docker Compose (recommended — matches the verified production build)

From the **project root** (one level up from this folder):

```bash
cd ..                      # into claude_bootcamp/, if you're in frontend/
docker compose up --build
```

Open **http://localhost:8080**. Stop it with `docker compose down`.

> If the build fails pulling `node:22-alpine` with an error like
> `x509: certificate signed by unknown authority`, that's a corporate proxy
> intercepting Docker Hub traffic that Docker Desktop doesn't trust — not a
> problem with this app. The `Dockerfile` is already pinned to `node:20-alpine`
> to work around this; if you still hit it, point `FROM` at whatever Node image
> is already cached on your machine (`docker images`), or get your corporate
> root CA added to Docker Desktop's trust store.

### Dev server (hot reload, for making changes)

From **this folder** (`frontend/`):

```bash
npm install
npm run dev
```

Open the URL it prints (typically http://localhost:5173).
