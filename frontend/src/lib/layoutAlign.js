/**
 * Diagram draw rules (all C4 layers):
 *  1. Flow lanes left→right (inputs left, sinks / last-reached right).
 *  2. Node cards must not overlap each other (hard clearance).
 *  3. Boundary wrappers (NodeWrappers) must keep considerable spacing.
 *
 * Packs nested cards into workflow lanes inside each boundary, separates any
 * remaining collisions, spaces sibling wrappers, and resizes parents to wrap.
 */

const CARD_W = 200;
const CARD_H = 118;
const GAP_X = 112;
const GAP_Y = 96;
const PAD_X = 72;
const PAD_TOP = 128;
const PAD_BOTTOM = 72;
/** Minimum clear space between card edges (non-overlap rule). */
const CLEAR_X = 56;
const CLEAR_Y = 48;
/** Considerable gap between sibling boundary wrappers. */
const BOUNDARY_CLEAR_X = 260;
const BOUNDARY_CLEAR_Y = 200;

export const GRID_STEP_X = CARD_W + GAP_X;
export const GRID_STEP_Y = CARD_H + GAP_Y;

const UI_HINTS = /\b(ui|frontend|front-end|web|spa|portal|client|react|angular|vue|next)\b/i;
const AUTH_HINTS = /\b(auth|sso|identity|login|oauth|saml|gateway|bff)\b/i;
const API_HINTS = /\b(api|service|ms-|microservice|backend|server|fastapi|spring)\b/i;
const AGENT_HINTS = /\b(agent|bodhi|docintel|llm|fabric|rule|orchestr)\b/i;
const DATA_HINTS = /\b(db|database|postgres|sql|store|redis|mongo|data)\b/i;

/**
 * Lower = earlier in the user/system workflow (left).
 * @param {any} node
 */
export function workflowTier(node) {
  const kind = node?.data?.kind || '';
  const hay = `${node?.data?.name || ''} ${node?.data?.technology || ''} ${node?.data?.description || ''}`;

  if (kind === 'person') return 0;
  if (kind === 'systemExternal' || kind === 'containerExternal') return 90;
  if (kind === 'containerDb' || (String(kind).startsWith('container') && DATA_HINTS.test(hay))) {
    return 80;
  }
  if (kind === 'system' && DATA_HINTS.test(hay)) return 80;
  if (UI_HINTS.test(hay)) return 10;
  if (AUTH_HINTS.test(hay)) return 20;
  if (AGENT_HINTS.test(hay)) return 45;
  if (API_HINTS.test(hay) || kind === 'container' || kind === 'component' || kind === 'system') {
    return 30;
  }
  if (kind === 'codeInterface') return 50;
  if (kind === 'codeClass') return 55;
  if (kind === 'codeEnum') return 60;
  return 40;
}

/**
 * @param {any[]} nodes
 * @param {any[]} edges
 */
function topoWithin(nodes, edges) {
  const ids = new Set(nodes.map((n) => n.id));
  const index = new Map(nodes.map((n, i) => [n.id, i]));
  /** @type {Map<string, string[]>} */
  const adj = new Map();
  /** @type {Map<string, number>} */
  const indeg = new Map(nodes.map((n) => [n.id, 0]));

  for (const e of edges || []) {
    if (!ids.has(e.source) || !ids.has(e.target) || e.source === e.target) continue;
    if (!adj.has(e.source)) adj.set(e.source, []);
    adj.get(e.source).push(e.target);
    indeg.set(e.target, (indeg.get(e.target) || 0) + 1);
  }

  const ready = nodes
    .filter((n) => (indeg.get(n.id) || 0) === 0)
    .sort((a, b) => (index.get(a.id) || 0) - (index.get(b.id) || 0))
    .map((n) => n.id);
  const q = [...ready];
  const orderedIds = [];
  while (q.length) {
    const cur = q.shift();
    orderedIds.push(cur);
    const nexts = [...(adj.get(cur) || [])].sort(
      (a, b) => (index.get(a) || 0) - (index.get(b) || 0)
    );
    for (const nxt of nexts) {
      indeg.set(nxt, (indeg.get(nxt) || 0) - 1);
      if (indeg.get(nxt) === 0) q.push(nxt);
    }
  }
  for (const n of nodes) {
    if (!orderedIds.includes(n.id)) orderedIds.push(n.id);
  }
  const byId = new Map(nodes.map((n) => [n.id, n]));
  return orderedIds.map((id) => byId.get(id)).filter(Boolean);
}

/**
 * @param {any[]} nodes
 * @param {any[]} [edges]
 */
export function orderNodesByWorkflow(nodes, edges = []) {
  /** @type {Map<number, any[]>} */
  const buckets = new Map();
  for (const node of nodes) {
    const tier = workflowTier(node);
    if (!buckets.has(tier)) buckets.set(tier, []);
    buckets.get(tier).push(node);
  }
  const ordered = [];
  for (const tier of [...buckets.keys()].sort((a, b) => a - b)) {
    const group = buckets.get(tier) || [];
    group.sort((a, b) =>
      String(a.data?.name || a.id).localeCompare(String(b.data?.name || b.id))
    );
    ordered.push(...topoWithin(group, edges));
  }
  return ordered;
}

/**
 * Left→right column index per node (inputs left, sinks right).
 * @param {any[]} nodes
 * @param {any[]} edges
 * @returns {Map<string, number>}
 */
export function assignWorkflowColumns(nodes, edges = []) {
  /** @type {Map<string, number>} */
  const columns = new Map();
  if (!nodes.length) return columns;

  const ids = new Set(nodes.map((n) => n.id));
  /** @type {Map<string, string[]>} */
  const succ = new Map();
  /** @type {Map<string, number>} */
  const indeg = new Map(nodes.map((n) => [n.id, 0]));

  for (const e of edges || []) {
    if (!ids.has(e.source) || !ids.has(e.target) || e.source === e.target) continue;
    if (!succ.has(e.source)) succ.set(e.source, []);
    succ.get(e.source).push(e.target);
    indeg.set(e.target, (indeg.get(e.target) || 0) + 1);
  }

  /** @type {Map<string, number>} */
  const depth = new Map(nodes.map((n) => [n.id, 0]));
  const indegWork = new Map(indeg);
  const q = nodes.filter((n) => (indegWork.get(n.id) || 0) === 0).map((n) => n.id);
  const seen = new Set();
  while (q.length) {
    const cur = q.shift();
    if (seen.has(cur)) continue;
    seen.add(cur);
    for (const nxt of succ.get(cur) || []) {
      depth.set(nxt, Math.max(depth.get(nxt) || 0, (depth.get(cur) || 0) + 1));
      indegWork.set(nxt, (indegWork.get(nxt) || 0) - 1);
      if (indegWork.get(nxt) === 0) q.push(nxt);
    }
  }

  const tiers = new Map(nodes.map((n) => [n.id, workflowTier(n)]));
  const uniqueTiers = [...new Set(tiers.values())].sort((a, b) => a - b);
  const tierFloor = new Map(uniqueTiers.map((t, i) => [t, i]));

  /** @type {Map<string, number>} */
  const raw = new Map();
  for (const n of nodes) {
    raw.set(
      n.id,
      Math.max(depth.get(n.id) || 0, tierFloor.get(tiers.get(n.id)) || 0)
    );
  }
  const used = [...new Set(raw.values())].sort((a, b) => a - b);
  const remap = new Map(used.map((v, i) => [v, i]));
  for (const [nid, c] of raw) {
    columns.set(nid, remap.get(c) ?? 0);
  }
  return columns;
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
 * @param {{ x: number, y: number, w: number, h: number }} a
 * @param {{ x: number, y: number, w: number, h: number }} b
 */
function rectsOverlap(a, b) {
  return !(
    a.x + a.w <= b.x ||
    b.x + b.w <= a.x ||
    a.y + a.h <= b.y ||
    b.y + b.h <= a.y
  );
}

/**
 * Considerable spacing between sibling boundary wrappers (all layers).
 * Upper-left wrappers stay; later ones move right or down.
 *
 * @param {any[]} nodes
 * @param {{ clearX?: number, clearY?: number }} [opts]
 * @returns {any[]}
 */
export function separateOverlappingBoundaries(nodes, opts = {}) {
  const clearX = opts.clearX ?? BOUNDARY_CLEAR_X;
  const clearY = opts.clearY ?? BOUNDARY_CLEAR_Y;
  const maxPasses = 32;

  const boundaries = nodes
    .filter((n) => n.type === 'c4Boundary')
    .map((b) => ({
      ...b,
      position: { ...b.position },
      width: Number(b.width) || Number.parseFloat(b.style?.width) || 640,
      height: Number(b.height) || Number.parseFloat(b.style?.height) || 400
    }));
  const rest = nodes.filter((n) => n.type !== 'c4Boundary');

  if (boundaries.length < 2) {
    return nodes;
  }

  boundaries.sort((a, b) => {
    const dy = (a.position?.y || 0) - (b.position?.y || 0);
    if (Math.abs(dy) > 1) return dy;
    return (a.position?.x || 0) - (b.position?.x || 0);
  });

  for (let pass = 0; pass < maxPasses; pass += 1) {
    let moved = false;
    for (let i = 0; i < boundaries.length; i += 1) {
      const a = boundaries[i];
      const aw = Number(a.width) || 640;
      const ah = Number(a.height) || 400;
      for (let j = i + 1; j < boundaries.length; j += 1) {
        const b = boundaries[j];
        const bw = Number(b.width) || 640;
        const bh = Number(b.height) || 400;
        const ar = {
          x: a.position.x,
          y: a.position.y,
          w: aw + clearX,
          h: ah + clearY
        };
        const br = { x: b.position.x, y: b.position.y, w: bw + clearX, h: bh + clearY };
        if (!rectsOverlap(ar, br)) continue;

        const pushRight = ar.x + ar.w - b.position.x;
        const pushDown = ar.y + ar.h - b.position.y;
        if (pushRight > 0 && pushRight <= pushDown) {
          b.position = { ...b.position, x: b.position.x + pushRight };
        } else if (pushDown > 0) {
          b.position = { ...b.position, y: b.position.y + pushDown };
        } else if (pushRight > 0) {
          b.position = { ...b.position, x: b.position.x + pushRight };
        }
        moved = true;
      }
    }
    if (!moved) break;
  }

  return [...boundaries, ...rest];
}

/**
 * Hard rule: push node cards apart until no two overlap (with clearance).
 * Earlier workflow / upper-left cards stay put; later ones move down or right.
 * Operates per parentId group (parent-relative coords).
 *
 * @param {any[]} nodes
 * @param {{ edges?: any[], cardW?: number, cardH?: number, clearX?: number, clearY?: number }} [opts]
 * @returns {any[]}
 */
export function separateOverlappingNodes(nodes, opts = {}) {
  const edges = opts.edges ?? [];
  const cardW = opts.cardW ?? CARD_W;
  const cardH = opts.cardH ?? CARD_H;
  const clearX = opts.clearX ?? CLEAR_X;
  const clearY = opts.clearY ?? CLEAR_Y;
  const maxPasses = 48;

  const boundaries = nodes.filter((n) => n.type === 'c4Boundary');
  const elements = nodes.filter((n) => n.type === 'c4Node');
  const other = nodes.filter((n) => n.type !== 'c4Boundary' && n.type !== 'c4Node');

  /** @type {Map<string | null, any[]>} */
  const groups = new Map();
  for (const el of elements) {
    const key = el.parentId ?? null;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push({ ...el, position: { ...el.position } });
  }

  /** @type {any[]} */
  const nextElements = [];
  /** @type {Map<string, { w: number, h: number }>} */
  const boundarySize = new Map();

  for (const [parentKey, group] of groups) {
    const visible = group.filter((n) => !n.hidden);
    const hiddenOnes = group.filter((n) => n.hidden);

    // Stable order: workflow first, then geometry — earlier cards win collisions.
    const ranked = orderNodesByWorkflow(visible, edges);
    ranked.sort((a, b) => {
      const dy = (a.position?.y || 0) - (b.position?.y || 0);
      if (Math.abs(dy) > 1) return dy;
      return (a.position?.x || 0) - (b.position?.x || 0);
    });

    for (let pass = 0; pass < maxPasses; pass += 1) {
      let moved = false;
      for (let i = 0; i < ranked.length; i += 1) {
        const a = ranked[i];
        const ar = {
          x: a.position.x,
          y: a.position.y,
          w: cardW + clearX,
          h: cardH + clearY
        };
        for (let j = i + 1; j < ranked.length; j += 1) {
          const b = ranked[j];
          const br = {
            x: b.position.x,
            y: b.position.y,
            w: cardW + clearX,
            h: cardH + clearY
          };
          if (!rectsOverlap(ar, br)) continue;

          const pushRight = ar.x + ar.w - b.position.x;
          const pushDown = ar.y + ar.h - b.position.y;
          // Prefer preserving L→R lanes: nudge down when mostly stacked,
          // otherwise nudge right (later / sink side).
          if (pushDown > 0 && pushDown <= pushRight) {
            b.position = { ...b.position, y: b.position.y + pushDown };
          } else if (pushRight > 0) {
            b.position = { ...b.position, x: b.position.x + pushRight };
          } else if (pushDown > 0) {
            b.position = { ...b.position, y: b.position.y + pushDown };
          }
          moved = true;
        }
      }
      if (!moved) break;
    }

    nextElements.push(...ranked, ...hiddenOnes);

    if (parentKey != null && ranked.length > 0) {
      const maxR = Math.max(...ranked.map((n) => n.position.x + cardW));
      const maxB = Math.max(...ranked.map((n) => n.position.y + cardH));
      boundarySize.set(parentKey, {
        w: Math.ceil(maxR + PAD_X),
        h: Math.ceil(maxB + PAD_BOTTOM)
      });
    }
  }

  const nextBoundaries = boundaries.map((b) => {
    const size = boundarySize.get(b.id);
    if (!size) return b;
    const w = Math.max(Number(b.width) || 0, size.w);
    const h = Math.max(Number(b.height) || 0, size.h);
    return {
      ...b,
      width: w,
      height: h,
      style: {
        ...(b.style || {}),
        width: `${w}px`,
        height: `${h}px`
      }
    };
  });

  return [...nextBoundaries, ...nextElements, ...other];
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
 * Snap element nodes into L→R workflow lanes inside each boundary parent,
 * separate any overlaps, then grow the boundary to wrap children.
 * @param {any[]} nodes
 * @param {{ enabledKinds?: Set<string> | null, legendKinds?: Set<string> | null, cols?: number, edges?: any[] }} [opts]
 * @returns {any[]}
 */
export function alignNodesInBoundaries(nodes, opts = {}) {
  const enabledKinds = opts.enabledKinds ?? null;
  const legendKinds = opts.legendKinds ?? null;
  const edges = opts.edges ?? [];

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

  for (const [parentKey, group] of groups) {
    const ranked = orderNodesByWorkflow(group, edges);

    const visible = [];
    const hiddenOnes = [];
    for (const node of ranked) {
      if (isFilteredOut(node, enabledKinds, legendKinds)) hiddenOnes.push(node);
      else visible.push(node);
    }

    // Free (unparented) nodes keep authored X/Y — clearance pass separates them.
    if (parentKey == null) {
      for (const node of visible) {
        nextElements.push({ ...node, hidden: false });
      }
      for (const node of hiddenOnes) {
        nextElements.push({ ...node, hidden: true });
      }
      continue;
    }

    const columns = assignWorkflowColumns(visible, edges);
    /** @type {Map<number, any[]>} */
    const byCol = new Map();
    for (const node of visible) {
      const col = columns.get(node.id) ?? 0;
      if (!byCol.has(col)) byCol.set(col, []);
      byCol.get(col).push(node);
    }

    const colIndexes = [...byCol.keys()].sort((a, b) => a - b);

    for (const col of colIndexes) {
      const lane = byCol.get(col) || [];
      lane.forEach((node, row) => {
        nextElements.push({
          ...node,
          hidden: false,
          position: {
            x: PAD_X + col * GRID_STEP_X,
            y: PAD_TOP + row * GRID_STEP_Y
          }
        });
      });
    }

    for (const node of hiddenOnes) {
      nextElements.push({ ...node, hidden: true });
    }
  }

  // Hard rules: no node↔node overlap; considerable space between wrappers.
  const cleared = separateOverlappingNodes([...boundaries, ...nextElements, ...other], {
    edges
  });
  return separateOverlappingBoundaries(cleared);
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
