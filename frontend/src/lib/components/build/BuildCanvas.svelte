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
  import C4Node from '../nodes/C4Node.svelte';
  import C4Boundary from '../nodes/C4Boundary.svelte';
  import C4Edge from '../edges/C4Edge.svelte';
  import Legend from '../Legend.svelte';
  import { ARROWS, SHAPES } from '../../buildCatalog.js';

  let {
    activeArrowId = 'uses',
    initialNodes = [],
    initialEdges = [],
    legend = [],
    loadGeneration = 0,
    onChange,
    onReady
  } = $props();

  const nodeTypes = { c4Node: C4Node, c4Boundary: C4Boundary };
  const edgeTypes = { c4Edge: C4Edge };

  const KIND_BY_SHAPE = {
    person: 'person',
    system: 'system',
    'external-system': 'systemExternal',
    container: 'container',
    database: 'containerDb',
    component: 'component'
  };

  const closedMarker = { type: MarkerType.ArrowClosed, width: 16, height: 16, color: '#8fa9c9' };
  const openMarker = { type: MarkerType.Arrow, width: 16, height: 16, color: '#8fa9c9' };

  const defaultEdgeOptions = {
    type: 'c4Edge',
    markerEnd: closedMarker
  };

  let nodes = $state.raw(untrack(() => initialNodes));
  let edges = $state.raw(untrack(() => initialEdges));

  $effect(() => {
    onChange?.(nodes, edges);
  });

  let seq = 1;

  const { screenToFlowPosition, fitView } = useSvelteFlow();

  function handleInit() {
    requestAnimationFrame(() => {
      fitView({ padding: 0.2, duration: 200 });
      onReady?.(loadGeneration);
    });
  }

  function makeEdge(id, source, target, arrowId) {
    const arrow = ARROWS.find((a) => a.id === arrowId) ?? ARROWS[0];
    const dashed = arrow.id === 'async' || arrow.id === 'dependency';
    const markerEnd = arrow.id === 'dependency' ? openMarker : closedMarker;
    const markerStart = arrow.id === 'bidirectional' ? closedMarker : undefined;
    return {
      id,
      source,
      target,
      type: 'c4Edge',
      label: arrow.name,
      data: dashed ? { style: 'dashed' } : {},
      markerStart,
      markerEnd
    };
  }

  export function addItem(itemId, clientX, clientY) {
    const shape = SHAPES.find((s) => s.id === itemId);
    const arrow = ARROWS.find((a) => a.id === itemId);

    if (shape) {
      const point =
        clientX != null && clientY != null
          ? screenToFlowPosition({ x: clientX, y: clientY })
          : { x: 180 + (seq % 4) * 50, y: 120 + (seq % 3) * 40 };

      seq += 1;
      const id = `node-${seq}-${shape.id}`;

      if (shape.id === 'boundary') {
        const boundary = {
          id,
          type: 'c4Boundary',
          position: { x: Math.round(point.x - 190), y: Math.round(point.y - 120) },
          width: 380,
          height: 240,
          zIndex: 0,
          data: { label: `${shape.name} ${seq}` }
        };
        nodes = [boundary, ...nodes];
        return;
      }

      const node = {
        id,
        type: 'c4Node',
        position: { x: Math.round(point.x - 110), y: Math.round(point.y - 75) },
        width: 220,
        height: 150,
        zIndex: 1,
        data: {
          kind: KIND_BY_SHAPE[shape.id] ?? 'container',
          name: shape.name,
          technology: shape.id === 'database' ? 'SQL' : undefined,
          description: shape.summary
        }
      };
      nodes = [...nodes, node];
      return;
    }

    if (arrow) {
      const elementNodes = nodes.filter((n) => n.type === 'c4Node');
      if (elementNodes.length < 2) return;
      const source = elementNodes[elementNodes.length - 2].id;
      const target = elementNodes[elementNodes.length - 1].id;
      seq += 1;
      edges = [...edges, makeEdge(`edge-${seq}-${arrow.id}`, source, target, arrow.id)];
    }
  }

  export function getDiagram() {
    return { nodes, edges };
  }

  function handleConnect(connection) {
    if (!connection.source || !connection.target) return;
    seq += 1;
    edges = [
      ...edges,
      makeEdge(`edge-${seq}-${activeArrowId}`, connection.source, connection.target, activeArrowId)
    ];
  }

  function onDragOver(event) {
    event.preventDefault();
    if (event.dataTransfer) event.dataTransfer.dropEffect = 'copy';
  }

  function onDrop(event) {
    event.preventDefault();
    const id =
      event.dataTransfer?.getData('application/x-c4-component') ||
      event.dataTransfer?.getData('text/plain');
    if (!id) return;
    addItem(id, event.clientX, event.clientY);
  }
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="work-surface" ondragover={onDragOver} ondrop={onDrop}>
  <SvelteFlow
    bind:nodes
    bind:edges
    {nodeTypes}
    {edgeTypes}
    {defaultEdgeOptions}
    oninit={handleInit}
    onconnect={handleConnect}
    fitView
    fitViewOptions={{ padding: 0.2 }}
    minZoom={0.3}
    maxZoom={1.6}
    proOptions={{ hideAttribution: true }}
  >
    <Background variant={BackgroundVariant.Dots} gap={22} size={1} color="#d7e3f1" />
    <Controls />
    <MiniMap
      position="top-right"
      width={130}
      height={90}
      pannable
      zoomable
      nodeColor={() => '#bcd0e8'}
      maskColor="rgba(29,78,216,0.06)"
    />
    {#if legend.length > 0}
      <Panel position="top-left">
        <Legend {legend} />
      </Panel>
    {/if}
  </SvelteFlow>
</div>

<style>
  .work-surface {
    flex: 1;
    min-width: 0;
    min-height: 0;
    height: 100%;
  }
</style>
