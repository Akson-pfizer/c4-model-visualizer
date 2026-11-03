<script>
  import {
    BaseEdge,
    EdgeLabel,
    getSmoothStepPath,
    useEdges,
    useNodes,
    useSvelteFlow
  } from '@xyflow/svelte';
  import {
    buildNodeObstacles,
    edgeLabelPassKey,
    placeEdgeLabel
  } from '../../edgeLabelLayout.js';

  let {
    id,
    source,
    target,
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    label,
    data,
    markerStart,
    markerEnd
  } = $props();

  const nodesApi = useNodes();
  const edgesApi = useEdges();
  const { getInternalNode } = useSvelteFlow();

  let hot = $derived(Boolean(data?.emphasize));

  let layout = $derived.by(() => {
    const [path, pathMidX, pathMidY] = getSmoothStepPath({
      sourceX,
      sourceY,
      targetX,
      targetY,
      sourcePosition,
      targetPosition,
      borderRadius: 10,
      offset: 28
    });

    if (!label) {
      return { path, x: pathMidX, y: pathMidY, clear: true };
    }

    // Reactive: re-place when nodes/edges change. Pass key resets the shared registry.
    const liveNodes = nodesApi.current || [];
    const liveEdges = edgesApi.current || [];
    // Shared across all edges so later labels can dodge earlier ones in this pass.
    const passKey = `${edgeLabelPassKey(liveNodes)}|${liveEdges.map((e) => e.id).sort().join(',')}`;
    const nodeObstacles = buildNodeObstacles(liveNodes, getInternalNode);

    const placed = placeEdgeLabel(String(id), {
      passKey,
      pathMidX,
      pathMidY,
      sourceX,
      sourceY,
      targetX,
      targetY,
      nodeObstacles,
      labelW: 112,
      labelH: 34,
      pad: 14
    });

    return { path, x: placed.x, y: placed.y, clear: placed.clear };
  });

  let strokeStyle = $derived(
    hot
      ? data?.style === 'dashed'
        ? 'stroke: var(--edge-hot); stroke-width: 2.75; stroke-dasharray: 6 4;'
        : 'stroke: var(--edge-hot); stroke-width: 2.75;'
      : data?.style === 'dashed'
        ? 'stroke: var(--border-strong); stroke-width: 1.5; stroke-dasharray: 5 4;'
        : 'stroke: var(--border-strong); stroke-width: 1.5;'
  );

  let shortLabel = $derived.by(() => {
    const raw = String(label || '');
    return raw.length > 36 ? `${raw.slice(0, 34).trimEnd()}…` : raw;
  });
</script>

<BaseEdge {id} path={layout.path} style={strokeStyle} {markerStart} {markerEnd} />

{#if label}
  <EdgeLabel x={layout.x} y={layout.y}>
    <div
      class="c4-edge-label"
      class:hot
      class:tight={!layout.clear}
      title={label}
    >
      <span class="c4-edge-label__text">{shortLabel}</span>
      {#if data?.technology}
        <span class="c4-edge-label__tech">[{data.technology}]</span>
      {/if}
    </div>
  </EdgeLabel>
{/if}

<style>
  .c4-edge-label {
    max-width: 112px;
    background: color-mix(in srgb, var(--surface) 94%, transparent);
    border: 1px solid var(--border);
    border-radius: 5px;
    padding: 2px 6px;
    font-size: 9.5px;
    line-height: 1.2;
    color: var(--text);
    box-shadow: var(--shadow-sm);
    text-align: center;
    pointer-events: none;
    backdrop-filter: blur(2px);
  }

  .c4-edge-label.hot {
    border-color: var(--edge-hot);
    color: var(--pfizer-blue-90, #000067);
    box-shadow: 0 0 0 1px color-mix(in srgb, var(--edge-hot) 28%, transparent);
    pointer-events: auto;
  }

  .c4-edge-label.tight {
    max-width: 96px;
    font-size: 9px;
    opacity: 0.96;
  }

  .c4-edge-label__text {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    word-break: break-word;
  }

  .c4-edge-label__tech {
    display: block;
    font-family: var(--mono);
    font-size: 8px;
    color: var(--text-muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
</style>
