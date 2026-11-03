<script>
  import { untrack } from 'svelte';
  import {
    SvelteFlow,
    Background,
    BackgroundVariant,
    Controls,
    MiniMap,
    Panel,
    MarkerType,
    useSvelteFlow
  } from '@xyflow/svelte';

  import C4Node from './nodes/C4Node.svelte';
  import C4Boundary from './nodes/C4Boundary.svelte';
  import C4Edge from './edges/C4Edge.svelte';
  import Legend from './Legend.svelte';
  import {
    alignEdgesToVisibility,
    alignNodesInBoundaries,
    applyKindVisibility
  } from '../layoutAlign.js';

  let { layer, onNodeSelect, onNodeDoubleClick, onBoundaryClick, loadGeneration, onReady } =
    $props();

  const nodeTypes = { c4Node: C4Node, c4Boundary: C4Boundary };
  const edgeTypes = { c4Edge: C4Edge };
  const defaultEdgeOptions = {
    markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16, color: '#8fa9c9' }
  };

  function attachNodeDrillHandlers(rawNodes) {
    return rawNodes.map((n) => {
      if (n.type === 'c4Boundary') {
        return {
          ...n,
          data: {
            ...n.data,
            onNavigateUpper: () => onBoundaryClick?.(n)
          }
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

  const legendKinds = untrack(
    () => new Set((layer.legend || []).map((item) => item.kind).filter(Boolean))
  );
  const interactiveLegend = legendKinds.size > 0;
  // Only re-pack nested code/component cards — Context/Container keep authored layout.
  const packOnFilter = untrack(
    () => layer.layer === 'code' || layer.layer === 'component'
  );
  // MiniMap redraws on every pan frame — skip it on dense diagrams.
  const showMiniMap = untrack(() => {
    const count = (layer.elementNodes || layer.nodes || []).filter(
      (n) => n.type === 'c4Node' || !n.type
    ).length;
    return count > 0 && count <= 14;
  });

  let activeKinds = $state.raw(untrack(() => new Set(legendKinds)));

  const seedNodes = untrack(() => attachNodeDrillHandlers(layer.nodes));
  const seedEdges = untrack(() => layer.edges);

  function buildVisible(kinds) {
    const opts = {
      enabledKinds: interactiveLegend ? kinds : null,
      legendKinds: interactiveLegend ? legendKinds : null,
      cols: 2
    };
    const aligned = packOnFilter
      ? alignNodesInBoundaries(seedNodes, opts)
      : applyKindVisibility(seedNodes, opts);
    const nextEdges = alignEdgesToVisibility(seedEdges, aligned);
    return { aligned, nextEdges };
  }

  const initial = untrack(() => buildVisible(activeKinds));
  let nodes = $state.raw(initial.aligned);
  let edges = $state.raw(initial.nextEdges);

  function applyKindFilter(kinds) {
    activeKinds = new Set(kinds);
    const { aligned, nextEdges } = buildVisible(activeKinds);
    nodes = aligned;
    edges = nextEdges;
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

  function handleInit() {
    requestAnimationFrame(() => {
      fitView({ padding: 0.16, duration: 0 });
      onReady?.(loadGeneration);
    });
  }

  function handleNodeClick({ node }) {
    if (node?.hidden) return;
    if (node.type === 'c4Node') {
      onNodeSelect?.(node);
    } else if (node.type === 'c4Boundary' && node.data?.targetUpperLayer) {
      onBoundaryClick?.(node);
    }
  }

  function handleNodeDoubleClick({ node }) {
    if (node?.hidden) return;
    if (node.type === 'c4Node') onNodeDoubleClick?.(node);
  }

  function handlePaneClick() {
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
  proOptions={{ hideAttribution: true }}
  oninit={handleInit}
  onnodeclick={handleNodeClick}
  onnodedoubleclick={handleNodeDoubleClick}
  onpaneclick={handlePaneClick}
>
  <Background variant={BackgroundVariant.Dots} gap={28} size={1} color="#d7e3f1" />
  <Controls showInteractive={false} />
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
  <Panel position="top-left">
    <Legend
      legend={layer.legend}
      activeKinds={activeKinds}
      interactive={interactiveLegend}
      onToggle={handleLegendToggle}
    />
  </Panel>
</SvelteFlow>
