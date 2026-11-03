/**
 * Deep-clone plain JSON-like data without choking on Svelte 5 proxies
 * (structuredClone fails on reactive Proxies and on functions).
 */
export function plainClone(value) {
  return JSON.parse(JSON.stringify(value ?? null));
}

/**
 * Clone Svelte Flow nodes/edges while dropping function callbacks in `data`.
 */
export function cloneFlowElements(nodes = [], edges = []) {
  const cleanNodes = nodes.map((n) => {
    const data = {};
    for (const [k, v] of Object.entries(n.data ?? {})) {
      if (typeof v !== 'function') data[k] = v;
    }
    return plainClone({ ...n, data });
  });
  const cleanEdges = edges.map((e) => plainClone(e));
  return { nodes: cleanNodes, edges: cleanEdges };
}
