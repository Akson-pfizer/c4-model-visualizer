/**
 * Snap / filter helpers for Svelte Flow diagrams.
 * Packing is only for nested code/component cards — Context/Container keep author positions.
 */

const CARD_W = 200;
const GAP_X = 56;
const GAP_Y = 44;
const PAD_X = 56;
const PAD_TOP = 120;

export const GRID_STEP_X = CARD_W + GAP_X;
export const GRID_STEP_Y = 118 + GAP_Y;

/**
 * Prefer Interface → Class → Enum so columns read consistently.
 * @param {any} node
 */
function kindRank(node) {
  const kind = node?.data?.kind || '';
  if (kind === 'codeInterface') return 0;
  if (kind === 'codeClass') return 1;
  if (kind === 'codeEnum') return 2;
  if (kind === 'component') return 3;
  return 4;
}

/**
 * @param {any} node
 * @param {Set<string> | null} enabledKinds
 * @param {Set<string> | null} legendKinds
 */
function isFilteredOut(node, enabledKinds, legendKinds) {
  const kind = node?.data?.kind;
  if (!enabledKinds || !legendKinds || !kind) return false;
  if (!legendKinds.has(kind)) return false;
  return !enabledKinds.has(kind);
}

/**
 * Visibility-only filter — preserves authored positions (Context / Container).
 * @param {any[]} nodes
 * @param {{ enabledKinds?: Set<string> | null, legendKinds?: Set<string> | null }} [opts]
 */
export function applyKindVisibility(nodes, opts = {}) {
  const enabledKinds = opts.enabledKinds ?? null;
  const legendKinds = opts.legendKinds ?? null;
  return nodes.map((node) => {
    if (node.type !== 'c4Node') return { ...node, hidden: false };
    const hidden = isFilteredOut(node, enabledKinds, legendKinds);
    return hidden === Boolean(node.hidden) ? node : { ...node, hidden };
  });
}

/**
 * Snap element nodes onto a clean grid inside each boundary parent.
 * @param {any[]} nodes
 * @param {{ enabledKinds?: Set<string> | null, legendKinds?: Set<string> | null, cols?: number }} [opts]
 * @returns {any[]}
 */
export function alignNodesInBoundaries(nodes, opts = {}) {
  const enabledKinds = opts.enabledKinds ?? null;
  const legendKinds = opts.legendKinds ?? null;
  const preferredCols = opts.cols ?? 2;

  const boundaries = nodes.filter((n) => n.type === 'c4Boundary');
  const elements = nodes.filter((n) => n.type === 'c4Node');
  const other = nodes.filter((n) => n.type !== 'c4Boundary' && n.type !== 'c4Node');

  /** @type {Map<string | null, any[]>} */
  const groups = new Map();
  for (const el of elements) {
    const key = el.parentId ?? null;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(el);
  }

  /** @type {any[]} */
  const nextElements = [];

  for (const [, group] of groups) {
    const ranked = [...group].sort((a, b) => {
      const rk = kindRank(a) - kindRank(b);
      if (rk !== 0) return rk;
      return String(a.data?.name || a.id).localeCompare(String(b.data?.name || b.id));
    });

    const visible = [];
    const hiddenOnes = [];
    for (const node of ranked) {
      if (isFilteredOut(node, enabledKinds, legendKinds)) hiddenOnes.push(node);
      else visible.push(node);
    }

    const cols = Math.min(preferredCols, Math.max(1, visible.length));

    visible.forEach((node, idx) => {
      const col = idx % cols;
      const row = Math.floor(idx / cols);
      let x = PAD_X + col * GRID_STEP_X;
      let y = PAD_TOP + row * GRID_STEP_Y;
      if (visible.length === 1 && node.parentId) {
        const parent = boundaries.find((b) => b.id === node.parentId);
        const pw = Number(parent?.width ?? GRID_STEP_X + PAD_X * 2);
        x = Math.max(PAD_X, Math.round((pw - CARD_W) / 2));
      }
      nextElements.push({
        ...node,
        hidden: false,
        position: { x, y }
      });
    });

    for (const node of hiddenOnes) {
      nextElements.push({ ...node, hidden: true });
    }
  }

  return [...boundaries, ...nextElements, ...other];
}

/**
 * Hide edges that touch a hidden node.
 * @param {any[]} edges
 * @param {any[]} nodes
 */
export function alignEdgesToVisibility(edges, nodes) {
  const hiddenIds = new Set(nodes.filter((n) => n.hidden).map((n) => n.id));
  return edges.map((e) => {
    const hidden = hiddenIds.has(e.source) || hiddenIds.has(e.target);
    return hidden === Boolean(e.hidden) ? e : { ...e, hidden };
  });
}
