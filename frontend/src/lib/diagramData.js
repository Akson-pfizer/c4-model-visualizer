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

export function getNextLayerId(currentLayerId) {
  const idx = LAYER_ORDER.indexOf(currentLayerId);
  if (idx === -1 || idx >= LAYER_ORDER.length - 1) return null;
  return LAYER_ORDER[idx + 1];
}

export function getPrevLayerId(currentLayerId) {
  const idx = LAYER_ORDER.indexOf(currentLayerId);
  if (idx <= 0) return null;
  return LAYER_ORDER[idx - 1];
}

function boundaryToNode(boundary, currentLayerId) {
  const fallbackUpperLayer = getPrevLayerId(currentLayerId);
  const targetUpperLayer =
    boundary.upperLayer && boundary.upperLayer !== currentLayerId
      ? boundary.upperLayer
      : fallbackUpperLayer;

  return {
    id: boundary.id,
    type: 'c4Boundary',
    position: boundary.position,
    width: boundary.size.width,
    height: boundary.size.height,
    selectable: false,
    draggable: false,
    zIndex: 0,
    data: {
      label: boundary.label,
      subtitle: boundary.subtitle ?? null,
      description: boundary.description ?? null,
      upperLayer: boundary.upperLayer ?? fallbackUpperLayer ?? null,
      targetUpperLayer: targetUpperLayer ?? null,
      sourceNodeId: boundary.sourceNodeId ?? null
    }
  };
}

export function adaptRawLayer(raw, focusParentId = null) {
  const allBoundaries = raw.boundaries ?? [];
  const allRawNodes = raw.nodes ?? [];
  const nextLayer = getNextLayerId(raw.layer);

  // Check if focusParentId matches any child nodes or carried-forward boundaries in this layer
  let matchingChildIds = new Set();
  let matchingBoundaryIds = new Set();

  if (focusParentId) {
    for (const b of allBoundaries) {
      if (b.sourceNodeId === focusParentId || b.id === `boundary-${focusParentId}`) {
        matchingBoundaryIds.add(b.id);
      }
    }
    for (const n of allRawNodes) {
      if (
        n.data?.parentNodeId === focusParentId ||
        (n.parentId && matchingBoundaryIds.has(n.parentId))
      ) {
        matchingChildIds.add(n.id);
        if (n.parentId) matchingBoundaryIds.add(n.parentId);
      }
    }
  }

  const hasFocusedSubset =
    Boolean(focusParentId) && (matchingChildIds.size > 0 || matchingBoundaryIds.size > 0);

  // Include external/actor neighbor nodes connected by edges to the focused subset
  if (hasFocusedSubset) {
    const rawById = new Map(allRawNodes.map((n) => [n.id, n]));
    for (const edge of raw.edges ?? []) {
      if (matchingChildIds.has(edge.source) || matchingChildIds.has(edge.target)) {
        const srcNode = rawById.get(edge.source);
        const tgtNode = rawById.get(edge.target);
        if (srcNode && !srcNode.parentId) matchingChildIds.add(edge.source);
        if (tgtNode && !tgtNode.parentId) matchingChildIds.add(edge.target);
      }
    }
  }

  const filteredBoundaries = hasFocusedSubset
    ? allBoundaries.filter((b) => matchingBoundaryIds.has(b.id))
    : allBoundaries;
  const filteredRawNodes = hasFocusedSubset
    ? allRawNodes.filter(
        (n) => matchingChildIds.has(n.id) || (n.parentId && matchingBoundaryIds.has(n.parentId))
      )
    : allRawNodes;

  // Reflow boundary positions when showing a single focused boundary so it sits cleanly at top-left
  const normalizedBoundaries =
    hasFocusedSubset && filteredBoundaries.length === 1
      ? [{ ...filteredBoundaries[0], position: { x: 260, y: 40 } }]
      : filteredBoundaries;

  const boundaryNodes = normalizedBoundaries.map((b) => {
    const bNode = boundaryToNode(b, raw.layer);
    if (hasFocusedSubset) {
      bNode.data = { ...bNode.data, focused: true };
    }
    return bNode;
  });

  const allowedNodeIds = new Set(filteredRawNodes.map((n) => n.id));
  const elementNodes = filteredRawNodes.map((node) => ({
    ...node,
    width: 220,
    height: 150,
    zIndex: 1,
    data: {
      ...node.data,
      nextLayer,
      focusedChild: hasFocusedSubset && node.data?.parentNodeId === focusParentId
    }
  }));

  const filteredEdges = (raw.edges ?? []).filter(
    (e) => allowedNodeIds.has(e.source) && allowedNodeIds.has(e.target)
  );

  return {
    layer: raw.layer,
    title: raw.title,
    subtitle: raw.subtitle,
    description: raw.description,
    note: raw.note ?? null,
    legend: raw.legend ?? [],
    focusParentId: hasFocusedSubset ? focusParentId : null,
    nodes: [...boundaryNodes, ...elementNodes],
    elementNodes,
    edges: filteredEdges
  };
}

export function getLayer(layerId, rawByLayer = DEFAULT_RAW_BY_LAYER, focusParentId = null) {
  const raw = rawByLayer[layerId] ?? DEFAULT_RAW_BY_LAYER[layerId];
  if (!raw) {
    throw new Error(`Unknown C4 layer: ${layerId}`);
  }
  return adaptRawLayer(raw, focusParentId);
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
