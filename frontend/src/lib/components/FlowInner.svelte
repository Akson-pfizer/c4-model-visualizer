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

  // App.svelte remounts this component fresh per layer (via {#key}), so `layer`
  // is only ever read once per instance — untrack() makes that explicit.
  let nodes = $state.raw(untrack(() => attachNodeDrillHandlers(layer.nodes)));
  let edges = $state.raw(untrack(() => layer.edges));

  const { fitView } = useSvelteFlow();

  // fitView on mount races the flex/fade layout settling on its final size,
  // which can freeze the viewport at a stale (smaller) zoom. Re-run it one
  // frame after init, once the container has its real dimensions.
  function handleInit() {
    requestAnimationFrame(() => {
      fitView({ padding: 0.16, duration: 200 });
      onReady?.(loadGeneration);
    });
  }

  function handleNodeClick({ node }) {
    if (node.type === 'c4Node') {
      onNodeSelect?.(node);
    } else if (node.type === 'c4Boundary' && node.data?.targetUpperLayer) {
      onBoundaryClick?.(node);
    }
  }

  function handleNodeDoubleClick({ node }) {
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
  fitViewOptions={{ padding: 0.16 }}
  minZoom={0.12}
  maxZoom={1.6}
  zoomOnDoubleClick={false}
  proOptions={{ hideAttribution: true }}
  oninit={handleInit}
  onnodeclick={handleNodeClick}
  onnodedoubleclick={handleNodeDoubleClick}
  onpaneclick={handlePaneClick}
>
  <Background variant={BackgroundVariant.Dots} gap={22} size={1} color="#d7e3f1" />
  <Controls showInteractive={false} />
  <MiniMap
    position="top-right"
    width={130}
    height={90}
    pannable
    zoomable
    nodeColor={() => '#bcd0e8'}
    maskColor="rgba(29,78,216,0.06)"
  />
  <Panel position="top-left">
    <Legend legend={layer.legend} />
  </Panel>
</SvelteFlow>
