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
  import C4Node from '../nodes/C4Node.svelte';
  import C4Boundary from '../nodes/C4Boundary.svelte';
  import C4Edge from '../edges/C4Edge.svelte';
  import CollapsibleLegend from '../CollapsibleLegend.svelte';
  import { ARROWS, SHAPES } from '../../buildCatalog.js';
  import { cloneDiagramSnapshot } from '../../keyboardShortcuts.js';
  import { plainClone } from '../../plainClone.js';

  let {
    activeArrowId = 'uses',
    initialNodes = [],
    initialEdges = [],
    legend = [],
    loadGeneration = 0,
    onChange,
    onHistoryStateChange,
    onNodeDoubleClick,
    onBoundaryClick,
    onReady
  } = $props();

  let legendOpen = $state(false);

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

  function decorateNodes(rawNodes) {
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
      if (n.type === 'c4Node') {
        return {
          ...n,
          data: {
            ...n.data,
            onDrillDown: () => onNodeDoubleClick?.(n)
          }
        };
      }
      return n;
    });
  }

  let nodes = $state.raw(untrack(() => decorateNodes(initialNodes)));
  let edges = $state.raw(untrack(() => initialEdges));

  // Undo / Redo & Clipboard state for canvas edits
  let pastStack = $state.raw([]);
  let futureStack = $state.raw([]);
  let clipboardBuffer = $state.raw({ nodes: [], edges: [] });

  function notifyHistoryState() {
    onHistoryStateChange?.({
      canUndo: pastStack.length > 0,
      canRedo: futureStack.length > 0,
      hasClipboard: clipboardBuffer.nodes.length > 0
    });
  }

  function recordSnapshot() {
    const snap = cloneDiagramSnapshot(nodes, edges);
    pastStack = [...pastStack.slice(-39), snap];
    futureStack = [];
    notifyHistoryState();
  }

  function handleNodeClick({ node }) {
    if (node?.type === 'c4Boundary' && node.data?.targetUpperLayer) {
      onBoundaryClick?.(node);
    }
  }

  function handleNodeDoubleClick({ node }) {
    if (!node || node.type !== 'c4Node') return;
    onNodeDoubleClick?.(node);
  }

  function handleNodeDragStart() {
    recordSnapshot();
  }

  function publishChange() {
    onChange?.(nodes, edges);
  }

  function handleNodeDragStop() {
    publishChange();
  }

  let seq = 1;

  const { screenToFlowPosition, fitView } = useSvelteFlow();

  function handleInit() {
    requestAnimationFrame(() => {
      fitView({ padding: 0.2, duration: 200 });
      notifyHistoryState();
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
      recordSnapshot();
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
        publishChange();
        return;
      }

      const node = {
        id,
        type: 'c4Node',
        position: { x: Math.round(point.x - 100), y: Math.round(point.y - 59) },
        width: 200,
        height: 118,
        zIndex: 1,
        data: {
          kind: KIND_BY_SHAPE[shape.id] ?? 'container',
          name: shape.name,
          technology: shape.id === 'database' ? 'SQL' : undefined,
          description: shape.summary
        }
      };
      nodes = decorateNodes([...nodes, node]);
      publishChange();
      return;
    }

    if (arrow) {
      const elementNodes = nodes.filter((n) => n.type === 'c4Node');
      if (elementNodes.length < 2) return;
      recordSnapshot();
      const source = elementNodes[elementNodes.length - 2].id;
      const target = elementNodes[elementNodes.length - 1].id;
      seq += 1;
      edges = [...edges, makeEdge(`edge-${seq}-${arrow.id}`, source, target, arrow.id)];
      publishChange();
    }
  }

  export function undo() {
    if (pastStack.length === 0) return false;
    const currentSnap = cloneDiagramSnapshot(nodes, edges);
    const previousSnap = pastStack[pastStack.length - 1];
    pastStack = pastStack.slice(0, -1);
    futureStack = [...futureStack, currentSnap];
    nodes = decorateNodes(previousSnap.nodes);
    edges = previousSnap.edges;
    notifyHistoryState();
    publishChange();
    return true;
  }

  export function redo() {
    if (futureStack.length === 0) return false;
    const currentSnap = cloneDiagramSnapshot(nodes, edges);
    const nextSnap = futureStack[futureStack.length - 1];
    futureStack = futureStack.slice(0, -1);
    pastStack = [...pastStack, currentSnap];
    nodes = decorateNodes(nextSnap.nodes);
    edges = nextSnap.edges;
    notifyHistoryState();
    publishChange();
    return true;
  }

  export function copySelected() {
    const selectedNodes = nodes.filter((n) => n.selected && n.type === 'c4Node');
    const fallbackNodes =
      selectedNodes.length > 0
        ? selectedNodes
        : nodes.filter((n) => n.type === 'c4Node').slice(-1);
    if (fallbackNodes.length === 0) return 0;

    const selectedIds = new Set(fallbackNodes.map((n) => n.id));
    const relatedEdges = edges.filter(
      (e) => selectedIds.has(e.source) && selectedIds.has(e.target)
    );
    clipboardBuffer = cloneDiagramSnapshot(fallbackNodes, relatedEdges);
    notifyHistoryState();

    try {
      navigator.clipboard?.writeText(
        JSON.stringify(
          fallbackNodes.map((n) => ({
            id: n.id,
            name: n.data?.name,
            kind: n.data?.kind,
            technology: n.data?.technology,
            description: n.data?.description
          })),
          null,
          2
        )
      );
    } catch {
      // Ignore browser clipboard permission errors; internal canvas clipboard still works
    }
    return fallbackNodes.length;
  }

  export function cutSelected() {
    const count = copySelected();
    if (count > 0) {
      deleteSelected();
    }
    return count;
  }

  export function pasteClipboard() {
    if (!clipboardBuffer.nodes || clipboardBuffer.nodes.length === 0) return 0;
    recordSnapshot();

    const idMap = new Map();
    const newNodes = clipboardBuffer.nodes.map((orig) => {
      seq += 1;
      const newId = `${orig.id}-copy-${seq}`;
      idMap.set(orig.id, newId);
      return {
        ...plainClone(orig),
        id: newId,
        selected: true,
        position: {
          x: Math.round((orig.position?.x ?? 120) + 36),
          y: Math.round((orig.position?.y ?? 120) + 36)
        },
        data: {
          ...orig.data,
          name: orig.data?.name?.endsWith('(Copy)')
            ? orig.data.name
            : `${orig.data?.name || 'Component'} (Copy)`
        }
      };
    });

    const newEdges = (clipboardBuffer.edges ?? [])
      .filter((e) => idMap.has(e.source) && idMap.has(e.target))
      .map((e) => {
        seq += 1;
        return {
          ...plainClone(e),
          id: `edge-${seq}-copy`,
          source: idMap.get(e.source),
          target: idMap.get(e.target)
        };
      });

    const deselectedExisting = nodes.map((n) => (n.selected ? { ...n, selected: false } : n));
    nodes = decorateNodes([...deselectedExisting, ...newNodes]);
    edges = [...edges, ...newEdges];
    publishChange();
    return newNodes.length;
  }

  export function duplicateSelected() {
    const copied = copySelected();
    if (copied === 0) return 0;
    return pasteClipboard();
  }

  export function deleteSelected() {
    const selectedNodeIds = new Set(nodes.filter((n) => n.selected).map((n) => n.id));
    const selectedEdgeIds = new Set(edges.filter((e) => e.selected).map((e) => e.id));
    if (selectedNodeIds.size === 0 && selectedEdgeIds.size === 0) return 0;

    recordSnapshot();
    nodes = nodes.filter((n) => !selectedNodeIds.has(n.id));
    edges = edges.filter(
      (e) =>
        !selectedEdgeIds.has(e.id) &&
        !selectedNodeIds.has(e.source) &&
        !selectedNodeIds.has(e.target)
    );
    publishChange();
    return selectedNodeIds.size + selectedEdgeIds.size;
  }

  export function selectAllNodes() {
    nodes = nodes.map((n) => (n.type === 'c4Node' ? { ...n, selected: true } : n));
    return nodes.filter((n) => n.selected).length;
  }

  export function clearSelection() {
    nodes = nodes.map((n) => (n.selected ? { ...n, selected: false } : n));
    edges = edges.map((e) => (e.selected ? { ...e, selected: false } : e));
  }

  export function getDiagram() {
    return { nodes, edges };
  }

  function handleConnect(connection) {
    if (!connection.source || !connection.target) return;
    recordSnapshot();
    seq += 1;
    edges = [
      ...edges,
      makeEdge(`edge-${seq}-${activeArrowId}`, connection.source, connection.target, activeArrowId)
    ];
    publishChange();
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
    onnodeclick={handleNodeClick}
    onnodedoubleclick={handleNodeDoubleClick}
    onnodedragstart={handleNodeDragStart}
    onnodedragstop={handleNodeDragStop}
    zoomOnDoubleClick={false}
    fitView
    fitViewOptions={{ padding: 0.2 }}
    minZoom={0.3}
    maxZoom={1.6}
    proOptions={{ hideAttribution: true }}
  >
    <Background variant={BackgroundVariant.Dots} gap={22} size={1} color="#d7e3f1" />
    <Controls>
      {#if legend.length > 0}
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
    <MiniMap
      position="top-right"
      width={130}
      height={90}
      pannable
      zoomable
      nodeColor={() => '#bcd0e8'}
      maskColor="rgba(29,78,216,0.06)"
    />
    {#if legendOpen}
      <Panel position="bottom-left">
        <CollapsibleLegend {legend} />
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

  :global(.svelte-flow__controls-button.legend-control.is-active) {
    background: var(--blue-50, #eff6ff) !important;
    color: var(--blue-700, #1d4ed8) !important;
  }
</style>
