/**
 * Diagram draw rules for edge labels (all C4 layers):
 *  1. Labels must not overlap node cards.
 *  2. Labels must not overlap other edge labels.
 *
 * C4Edge calls `placeEdgeLabel` during render. A per-pass registry records each
 * placed label so later edges dodge earlier ones (Visualizer + Developer).
 */

/**
 * @typedef {{ x: number, y: number, w: number, h: number, id?: string }} LabelObstacle
 */

/** @type {{ passKey: string, labels: LabelObstacle[] }} */
const registry = {
  passKey: '',
  labels: []
};

/**
 * @param {{ x: number, y: number, w: number, h: number }} a
 * @param {{ x: number, y: number, w: number, h: number }} b
 */
export function rectsOverlap(a, b) {
  return !(
    a.x + a.w <= b.x ||
    b.x + b.w <= a.x ||
    a.y + a.h <= b.y ||
    b.y + b.h <= a.y
  );
}

/**
 * @param {LabelObstacle} rect
 * @param {number} pad
 */
function inflate(rect, pad) {
  return {
    x: rect.x - pad,
    y: rect.y - pad,
    w: rect.w + pad * 2,
    h: rect.h + pad * 2
  };
}

/**
 * Stable key for a layout pass — changes when node geometry changes.
 * @param {any[]} nodes
 */
export function edgeLabelPassKey(nodes) {
  let key = String((nodes || []).length);
  for (const node of nodes || []) {
    if (!node || node.hidden) continue;
    const p = node.position || {};
    const w = node.measured?.width ?? node.width ?? 0;
    const h = node.measured?.height ?? node.height ?? 0;
    key += `|${node.id}:${Math.round(p.x)}:${Math.round(p.y)}:${Math.round(w)}:${Math.round(h)}`;
  }
  return key;
}

/**
 * Build absolute flow-space obstacles from Svelte Flow nodes.
 * @param {any[]} nodes
 * @param {(id: string) => any} [getInternalNode]
 * @returns {LabelObstacle[]}
 */
export function buildNodeObstacles(nodes, getInternalNode) {
  /** @type {LabelObstacle[]} */
  const out = [];
  for (const node of nodes || []) {
    if (!node || node.hidden) continue;
    if (node.type && node.type !== 'c4Node') continue;
    const internal = getInternalNode?.(node.id);
    const abs = internal?.internals?.positionAbsolute ?? node.positionAbsolute ?? node.position;
    if (!abs) continue;
    const w = Number(node.measured?.width ?? node.width ?? 200);
    const h = Number(node.measured?.height ?? node.height ?? 118);
    out.push({ id: node.id, x: abs.x, y: abs.y, w, h });
  }
  return out;
}

/**
 * Core placer: nudge a label until it clears every obstacle rect.
 * @param {{
 *   pathMidX: number,
 *   pathMidY: number,
 *   sourceX: number,
 *   sourceY: number,
 *   targetX: number,
 *   targetY: number,
 *   obstacles?: LabelObstacle[],
 *   labelW?: number,
 *   labelH?: number,
 *   pad?: number,
 *   excludeIds?: string[]
 * }} opts
 * @returns {{ x: number, y: number, clear: boolean }}
 */
export function placeEdgeLabelClearOfNodes(opts) {
  const {
    pathMidX,
    pathMidY,
    sourceX,
    sourceY,
    targetX,
    targetY,
    obstacles = [],
    labelW = 108,
    labelH = 30,
    pad = 10,
    excludeIds = []
  } = opts;

  const dx = targetX - sourceX;
  const dy = targetY - sourceY;
  const len = Math.hypot(dx, dy) || 1;
  const nx = -dy / len;
  const ny = dx / len;

  const baseX = sourceX + dx * 0.5;
  const baseY = sourceY + dy * 0.5;
  const midX = pathMidX * 0.35 + baseX * 0.65;
  const midY = pathMidY * 0.35 + baseY * 0.65;

  const blockers = obstacles
    .filter((o) => !excludeIds.includes(o.id || ''))
    .map((o) => inflate(o, pad));

  /** @type {number[]} — denser perpendicular + along-edge search for label↔label */
  const offsets = [20, -20, 38, -38, 56, -56, 74, -74, 92, -92, 110, -110, 0, 130, -130];
  const alongSteps = [0, 0.1, -0.1, 0.18, -0.18, 0.28, -0.28, 0.36, -0.36];

  for (const along of alongSteps) {
    const ax = midX + dx * along;
    const ay = midY + dy * along;
    for (const off of offsets) {
      const x = ax + nx * off;
      const y = ay + ny * off;
      const labelRect = {
        x: x - labelW / 2,
        y: y - labelH / 2,
        w: labelW,
        h: labelH
      };
      if (!blockers.some((b) => rectsOverlap(labelRect, b))) {
        return { x, y, clear: true };
      }
    }
  }

  return {
    x: midX + nx * 72,
    y: midY + ny * 72,
    clear: false
  };
}

/**
 * Draw-time placement used by C4Edge — avoids nodes **and** other edge labels.
 * @param {string} edgeId
 * @param {{
 *   passKey: string,
 *   pathMidX: number,
 *   pathMidY: number,
 *   sourceX: number,
 *   sourceY: number,
 *   targetX: number,
 *   targetY: number,
 *   nodeObstacles?: LabelObstacle[],
 *   labelW?: number,
 *   labelH?: number,
 *   pad?: number
 * }} opts
 * @returns {{ x: number, y: number, clear: boolean }}
 */
export function placeEdgeLabel(edgeId, opts) {
  const labelW = opts.labelW ?? 108;
  const labelH = opts.labelH ?? 30;
  const pad = opts.pad ?? 12;

  if (opts.passKey !== registry.passKey) {
    registry.passKey = opts.passKey;
    registry.labels = [];
  }

  // Drop our previous slot so re-renders don't block ourselves.
  const others = registry.labels.filter((l) => l.id !== edgeId);

  const placed = placeEdgeLabelClearOfNodes({
    pathMidX: opts.pathMidX,
    pathMidY: opts.pathMidY,
    sourceX: opts.sourceX,
    sourceY: opts.sourceY,
    targetX: opts.targetX,
    targetY: opts.targetY,
    obstacles: [...(opts.nodeObstacles || []), ...others],
    labelW,
    labelH,
    pad
  });

  registry.labels = [
    ...others,
    {
      id: edgeId,
      x: placed.x - labelW / 2,
      y: placed.y - labelH / 2,
      w: labelW,
      h: labelH
    }
  ];

  return placed;
}

/** Test helper — reset coordinated label registry. */
export function resetEdgeLabelRegistry() {
  registry.passKey = '';
  registry.labels = [];
}

/**
 * @param {{ x: number, y: number }} center
 * @param {LabelObstacle[]} obstacles
 * @param {{ labelW?: number, labelH?: number, pad?: number }} [opts]
 */
export function edgeLabelOverlapsNodes(center, obstacles, opts = {}) {
  const labelW = opts.labelW ?? 108;
  const labelH = opts.labelH ?? 30;
  const pad = opts.pad ?? 10;
  const labelRect = {
    x: center.x - labelW / 2,
    y: center.y - labelH / 2,
    w: labelW,
    h: labelH
  };
  return obstacles.some((o) => rectsOverlap(labelRect, inflate(o, pad)));
}
