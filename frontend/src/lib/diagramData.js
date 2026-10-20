// Adapts backend-shaped C4 layer payloads (either the default static demo JSON
// or the live multi-agent backend response from POST /api/c4/model) into Svelte
// Flow's node/edge shape, and builds the hierarchical tree model across
// Context -> Container -> Component -> Code.
import contextData from './data/context.json';
import containerData from './data/container.json';
import componentData from './data/component.json';
import codeData from './data/code.json';

export const DEFAULT_RAW_BY_LAYER = {
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

export const LAYER_ORDER = ['context', 'container', 'component', 'code'];

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

export function adaptRawLayer(raw) {
  const boundaryNodes = (raw.boundaries ?? []).map(boundaryToNode);
  const elementNodes = (raw.nodes ?? []).map((node) => ({
    ...node,
    width: 220,
    height: 150,
    zIndex: 1
  }));

  return {
    layer: raw.layer,
    title: raw.title,
    subtitle: raw.subtitle,
    description: raw.description,
    note: raw.note ?? null,
    legend: raw.legend ?? [],
    nodes: [...boundaryNodes, ...elementNodes],
    elementNodes,
    edges: raw.edges ?? []
  };
}

export function getLayer(layerId, rawByLayer = DEFAULT_RAW_BY_LAYER) {
  const raw = rawByLayer[layerId] ?? DEFAULT_RAW_BY_LAYER[layerId];
  if (!raw) {
    throw new Error(`Unknown C4 layer: ${layerId}`);
  }
  return adaptRawLayer(raw);
}

/**
 * Builds the 4-level C4 hierarchy forest:
 *   Context (root nodes) -> Container -> Component -> Code
 * Each layer's nodes attach to their parent in the layer above via `data.parentNodeId`
 * (with automatic fallback to the primary in-scope parent if not explicitly set).
 */
export function buildHierarchyFromLayers(rawByLayer = DEFAULT_RAW_BY_LAYER) {
  /** @type {Record<string, Map<string, any>>} */
  const byLayer = {};

  for (const layerId of LAYER_ORDER) {
    const raw = rawByLayer[layerId] ?? DEFAULT_RAW_BY_LAYER[layerId];
    const map = new Map();
    for (const node of raw?.nodes ?? []) {
      if (node.type && node.type !== 'c4Node') continue;
      map.set(node.id, {
        id: node.id,
        name: node.data.name,
        layer: layerId,
        kind: node.data.kind,
        technology: node.data.technology ?? null,
        description: node.data.description ?? '',
        parentNodeId: node.data.parentNodeId ?? null,
        children: []
      });
    }
    byLayer[layerId] = map;
  }

  for (let i = 0; i < LAYER_ORDER.length - 1; i += 1) {
    const parentLayerId = LAYER_ORDER[i];
    const childLayerId = LAYER_ORDER[i + 1];
    const parentMap = byLayer[parentLayerId];
    const childMap = byLayer[childLayerId];
    if (!parentMap || parentMap.size === 0) continue;

    const parentList = [...parentMap.values()];
    const fallbackParent =
      parentList.find((p) => ['system', 'container', 'component'].includes(p.kind)) ??
      parentList[0];

    for (const child of childMap.values()) {
      const parent =
        (child.parentNodeId && parentMap.get(child.parentNodeId)) ||
        parentList.find(
          (p) => p.id === child.id || p.name.toLowerCase() === child.name.toLowerCase()
        ) ||
        fallbackParent;
      if (parent) {
        child.parentNodeId = parent.id;
        parent.children.push(child);
      }
    }
  }

  return [...(byLayer.context?.values() ?? [])];
}
