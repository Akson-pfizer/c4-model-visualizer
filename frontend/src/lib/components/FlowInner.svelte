<script>
  import { untrack } from 'svelte';
  import {
    SvelteFlow,
    Background,
    BackgroundVariant,
    Controls,
    ControlButton,
    MiniMap,
    Panel,
    MarkerType,
    useSvelteFlow
  } from '@xyflow/svelte';

  import C4Node from './nodes/C4Node.svelte';
  import C4Boundary from './nodes/C4Boundary.svelte';
  import C4Edge from './edges/C4Edge.svelte';
  import CollapsibleLegend from './CollapsibleLegend.svelte';
  import {
    alignEdgesToVisibility,
    alignNodesInBoundaries,
    applyKindVisibility,
    separateOverlappingBoundaries,
    separateOverlappingNodes
  } from '../layoutAlign.js';

  let {
    layer,
    onNodeSelect,
    onNodeDoubleClick,
    onBoundaryClick,
    loadGeneration,
    onReady,
    onHistoryStateChange
  } = $props();

  let legendOpen = $state(false);

  const EDGE_IDLE = '#8fa9c9';
  const EDGE_HOT = '#0095FF';

  const nodeTypes = { c4Node: C4Node, c4Boundary: C4Boundary };
  const edgeTypes = { c4Edge: C4Edge };
  const defaultEdgeOptions = {
    markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16, color: EDGE_IDLE }
  };

  function attachNodeDrillHandlers(rawNodes) {
    return rawNodes.map((n) => {
      if (n.type === 'c4Boundary') {
        return {
          ...n,
          data: {
            ...n.data,
            onNavigateUpper: () => onBoundaryClick?.(n)
          },
          // Boundaries are visual scopes only — navigation is via breadcrumb.
          selectable: false,
          draggable: false
        };
      }
      if (n.type !== 'c4Node') return n;
      return {
        ...n,
        data: {
          ...n.data,
          onDrillDown: () => onNodeDoubleClick?.(n)
        }
      };
    });
  }

  /**
   * Merge A→B + B→A into one bidirectional edge (arrows both ends).
   * @param {any[]} edgeList
   */
  function coalesceBidirectional(edgeList) {
    /** @type {Map<string, any>} */
    const kept = new Map();
    /** @type {Set<string>} */
    const consumed = new Set();

    for (const edge of edgeList) {
      if (consumed.has(edge.id)) continue;
      const reverse = edgeList.find(
        (other) =>
          other.id !== edge.id &&
          !consumed.has(other.id) &&
          other.source === edge.target &&
          other.target === edge.source
      );
      if (!reverse) {
        kept.set(edge.id, { ...edge, data: { ...edge.data, bidirectional: false } });
        continue;
      }
      consumed.add(edge.id);
      consumed.add(reverse.id);
      const labelParts = [edge.label, reverse.label].filter(Boolean);
      const label =
        labelParts.length === 2 && labelParts[0] !== labelParts[1]
          ? `${labelParts[0]} ↔ ${labelParts[1]}`
          : labelParts[0] || 'Interacts with';
      const tech =
        edge.data?.technology && reverse.data?.technology && edge.data.technology !== reverse.data.technology
          ? `${edge.data.technology} / ${reverse.data.technology}`
          : edge.data?.technology || reverse.data?.technology || null;
      kept.set(edge.id, {
        ...edge,
        label,
        data: {
          ...edge.data,
          technology: tech,
          style: edge.data?.style || reverse.data?.style,
          bidirectional: true
        },
        markerStart: {
          type: MarkerType.ArrowClosed,
          width: 16,
          height: 16,
          color: EDGE_IDLE
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: 16,
          height: 16,
          color: EDGE_IDLE
        }
      });
    }
    return [...kept.values()];
  }

  const legendKinds = untrack(
    () => new Set((layer.legend || []).map((item) => item.kind).filter(Boolean))
  );
  const interactiveLegend = legendKinds.size > 0;
  const packOnFilter = untrack(
    () =>
      layer.layer === 'code' ||
      layer.layer === 'component' ||
      layer.layer === 'container' ||
      Boolean(layer.focusParentId)
  );
  const showMiniMap = untrack(() => {
    const count = (layer.elementNodes || layer.nodes || []).filter(
      (n) => n.type === 'c4Node' || !n.type
    ).length;
    return count > 0 && count <= 14;
  });

  let activeKinds = $state.raw(untrack(() => new Set(legendKinds)));
  let selectedNodeId = $state.raw(/** @type {string | null} */ (null));
  let movePast = $state.raw(/** @type {any[]} */ ([]));
  let moveFuture = $state.raw(/** @type {any[]} */ ([]));

  const seedNodes = untrack(() => attachNodeDrillHandlers(layer.nodes));
  const seedEdges = untrack(() => coalesceBidirectional(layer.edges || []));

  function withEdgeEmphasis(edgeList, nodeId) {
    return edgeList.map((e) => {
      const hot = Boolean(nodeId && (e.source === nodeId || e.target === nodeId));
      const color = hot ? EDGE_HOT : EDGE_IDLE;
      const size = hot ? 18 : 16;
      const markerEnd = {
        type: MarkerType.ArrowClosed,
        width: size,
        height: size,
        color
      };
      const markerStart = e.data?.bidirectional
        ? { type: MarkerType.ArrowClosed, width: size, height: size, color }
        : e.markerStart;
      return {
        ...e,
        zIndex: hot ? 12 : e.zIndex ?? 0,
        data: { ...e.data, emphasize: hot },
        markerEnd,
        markerStart
      };
    });
  }

  function buildVisible(kinds, nodeId = selectedNodeId) {
    const opts = {
      enabledKinds: interactiveLegend ? kinds : null,
      legendKinds: interactiveLegend ? legendKinds : null,
      cols: 4,
      edges: seedEdges
    };
    // Hard rules (all layers): no node overlap; considerable gap between wrappers.
    const packed = packOnFilter
      ? alignNodesInBoundaries(seedNodes, opts)
      : separateOverlappingBoundaries(
          separateOverlappingNodes(applyKindVisibility(seedNodes, opts), {
            edges: seedEdges
          })
        );
    const aligned = packed;
    const nextEdges = withEdgeEmphasis(alignEdgesToVisibility(seedEdges, aligned), nodeId);
    return { aligned, nextEdges };
  }

  const initial = untrack(() => buildVisible(activeKinds, null));
  let nodes = $state.raw(initial.aligned);
  let edges = $state.raw(initial.nextEdges);

  function notifyHistory() {
    onHistoryStateChange?.({
      canUndoMove: movePast.length > 0,
      canRedoMove: moveFuture.length > 0
    });
  }

  function snapshotPositions() {
    return nodes
      .filter((n) => n.type === 'c4Node')
      .map((n) => ({ id: n.id, x: n.position.x, y: n.position.y }));
  }

  function applyPositions(snap) {
    const byId = new Map(snap.map((s) => [s.id, s]));
    nodes = nodes.map((n) => {
      const hit = byId.get(n.id);
      if (!hit) return n;
      return { ...n, position: { x: hit.x, y: hit.y } };
    });
  }

  function handleNodeDragStart() {
    movePast = [...movePast.slice(-39), snapshotPositions()];
    moveFuture = [];
    notifyHistory();
  }

  /** @returns {boolean} */
  export function undoMove() {
    if (movePast.length === 0) return false;
    const current = snapshotPositions();
    const prev = movePast[movePast.length - 1];
    movePast = movePast.slice(0, -1);
    moveFuture = [...moveFuture, current];
    applyPositions(prev);
    notifyHistory();
    return true;
  }

  /** @returns {boolean} */
  export function redoMove() {
    if (moveFuture.length === 0) return false;
    const current = snapshotPositions();
    const next = moveFuture[moveFuture.length - 1];
    moveFuture = moveFuture.slice(0, -1);
    movePast = [...movePast, current];
    applyPositions(next);
    notifyHistory();
    return true;
  }

  function applyKindFilter(kinds) {
    activeKinds = new Set(kinds);
    const { aligned, nextEdges } = buildVisible(activeKinds, selectedNodeId);
    nodes = aligned;
    edges = nextEdges;
    movePast = [];
    moveFuture = [];
    notifyHistory();
  }

  function setSelection(nodeId) {
    selectedNodeId = nodeId;
    edges = withEdgeEmphasis(edges, nodeId);
  }

  function handleLegendToggle(kind) {
    if (!legendKinds.has(kind)) return;
    const next = new Set(activeKinds);
    if (next.has(kind)) {
      if (next.size <= 1) return;
      next.delete(kind);
    } else {
      next.add(kind);
    }
    applyKindFilter(next);
  }

  const { fitView } = useSvelteFlow();

  function centerDiagram(duration = 0) {
    fitView({ padding: 0.16, duration, includeHiddenNodes: false });
  }

  function handleInit() {
    requestAnimationFrame(() => {
      centerDiagram(0);
      notifyHistory();
      onReady?.(loadGeneration);
    });
  }

  $effect(() => {
    /** @type {ReturnType<typeof setTimeout> | undefined} */
    let timer;
    function onFullscreenChange() {
      clearTimeout(timer);
      requestAnimationFrame(() => {
        requestAnimationFrame(() => centerDiagram(220));
      });
      timer = setTimeout(() => centerDiagram(180), document.fullscreenElement ? 120 : 80);
    }
    document.addEventListener('fullscreenchange', onFullscreenChange);
    return () => {
      clearTimeout(timer);
      document.removeEventListener('fullscreenchange', onFullscreenChange);
    };
  });

  function handleNodeClick({ node }) {
    if (node?.hidden) return;
    if (node.type === 'c4Node') {
      setSelection(node.id);
      onNodeSelect?.(node);
    }
  }

  function handleNodeDoubleClick({ node }) {
    if (node?.hidden) return;
    if (node.type === 'c4Node') onNodeDoubleClick?.(node);
  }

  function handlePaneClick() {
    setSelection(null);
    onNodeSelect?.(null);
  }
</script>

<SvelteFlow
  bind:nodes
  bind:edges
  {nodeTypes}
  {edgeTypes}
  {defaultEdgeOptions}
  fitView
  fitViewOptions={{ padding: 0.16, duration: 0 }}
  minZoom={0.12}
  maxZoom={1.6}
  zoomOnDoubleClick={false}
  nodesDraggable={true}
  proOptions={{ hideAttribution: true }}
  oninit={handleInit}
  onnodeclick={handleNodeClick}
  onnodedoubleclick={handleNodeDoubleClick}
  onpaneclick={handlePaneClick}
  onnodedragstart={handleNodeDragStart}
>
  <Background variant={BackgroundVariant.Dots} gap={28} size={1} color="#d7e3f1" />
  <Controls showInteractive={false}>
    {#if (layer.legend || []).length}
      <ControlButton
        class={legendOpen ? 'legend-control is-active' : 'legend-control'}
        title={legendOpen ? 'Hide legend' : 'Legend'}
        aria-label={legendOpen ? 'Hide legend' : 'Show legend'}
        aria-pressed={legendOpen}
        onclick={() => (legendOpen = !legendOpen)}
      >
        <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
          <path
            fill="currentColor"
            d="M4 5h16v2H4V5zm0 6h10v2H4v-2zm0 6h16v2H4v-2zm14-7.5 1.5 3 3.3.4-2.5 2.3.7 3.2L18 15.8 15 17.4l.7-3.2-2.5-2.3 3.3-.4L18 9.5z"
          />
        </svg>
      </ControlButton>
    {/if}
  </Controls>
  {#if showMiniMap}
    <MiniMap
      position="top-right"
      width={110}
      height={72}
      pannable={false}
      zoomable={false}
      nodeColor={() => '#bcd0e8'}
      maskColor="rgba(29,78,216,0.06)"
    />
  {/if}
  {#if legendOpen}
    <Panel position="bottom-left">
      <CollapsibleLegend
        legend={layer.legend}
        activeKinds={activeKinds}
        interactive={interactiveLegend}
        onToggle={handleLegendToggle}
      />
    </Panel>
  {/if}
</SvelteFlow>

<style>
  :global(.svelte-flow__controls-button.legend-control.is-active) {
    background: var(--blue-50, #eff6ff) !important;
    color: var(--blue-700, #1d4ed8) !important;
  }
</style>
