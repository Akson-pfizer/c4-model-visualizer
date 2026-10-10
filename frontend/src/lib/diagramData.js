// Demo data layer. Each JSON file in ./data follows the schema documented in
// claude_output/frontend_implementation.md — the exact shape a future backend
// endpoint (e.g. GET /api/c4/{layer}) should return. This module is the one place
// that adapts that backend-shaped schema into Svelte Flow's node/edge shape, so
// swapping the static imports below for a fetch() call is the only change a real
// integration needs.
import contextData from './data/context.json';
import containerData from './data/container.json';
import componentData from './data/component.json';
import codeData from './data/code.json';

const RAW_BY_LAYER = {
  context: contextData,
  container: containerData,
  component: componentData,
  code: codeData
};

export const LAYERS = [
  { id: 'context', label: 'Context', description: 'System Context' },
  { id: 'container', label: 'Container', description: 'Container' },
  { id: 'component', label: 'Component', description: 'Component' },
  { id: 'code', label: 'Code', description: 'Code' }
];

function boundaryToNode(boundary) {
  return {
    id: boundary.id,
    type: 'c4Boundary',
    position: boundary.position,
    width: boundary.size.width,
    height: boundary.size.height,
    selectable: false,
    draggable: false,
    zIndex: 0,
    data: { label: boundary.label }
  };
}

export function getLayer(layerId) {
  const raw = RAW_BY_LAYER[layerId];
  if (!raw) {
    throw new Error(`Unknown C4 layer: ${layerId}`);
  }

  const boundaryNodes = (raw.boundaries ?? []).map(boundaryToNode);
  // Explicit width/height avoid a fitView race: Svelte Flow can only compute an
  // accurate initial fit if every node's size is known synchronously, before the
  // async DOM measurement (ResizeObserver) pass completes.
  const elementNodes = raw.nodes.map((node) => ({ ...node, width: 220, height: 150, zIndex: 1 }));

  return {
    layer: raw.layer,
    title: raw.title,
    subtitle: raw.subtitle,
    description: raw.description,
    note: raw.note ?? null,
    legend: raw.legend,
    nodes: [...boundaryNodes, ...elementNodes],
    edges: raw.edges
  };
}
