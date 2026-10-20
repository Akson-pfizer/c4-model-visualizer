<script>
  import { onMount } from 'svelte';
  import {
    SvelteFlow,
    SvelteFlowProvider,
    Background,
    BackgroundVariant,
    Controls,
    MiniMap,
    Panel,
    MarkerType
  } from '@xyflow/svelte';
  import '@xyflow/svelte/dist/style.css';
  import C4Node from './nodes/C4Node.svelte';
  import C4Edge from './edges/C4Edge.svelte';
  import Legend from './Legend.svelte';
  import { LAYER_ORDER } from '../diagramData.js';

  let {
    hierarchy = [],
    onNodeSelect,
    onNodeDoubleClick,
    loadGeneration = 0,
    onReady
  } = $props();

  const nodeTypes = { c4Node: C4Node };
  const edgeTypes = { c4Edge: C4Edge };

  const LAYER_BADGES = {
    context: '1 · Context (Root)',
    container: '2 · Container',
    component: '3 · Component',
    code: '4 · Code / Class Modules'
  };

  const LAYER_Y = {
    context: 40,
    container: 280,
    component: 520,
    code: 760
  };

  const NODE_WIDTH = 220;
  const NODE_HEIGHT = 150;
  const X_GAP = 255;

  function buildTreeFlow(roots) {
    /** @type {any[]} */
    const flowNodes = [];
    /** @type {any[]} */
    const flowEdges = [];
    const seenKinds = [];

    let leafCursor = 0;

    /**
     * Post-order traversal assigns each leaf a sequential horizontal slot and
     * centers each parent above its children across the 4 C4 layers:
     * Context (y=40) -> Container (y=280) -> Component (y=520) -> Code (y=760).
     */
    function layoutSubtree(item, depth) {
      const layerKey = item.layer || LAYER_ORDER[Math.min(depth, 3)];
      const flowId = `tree-${layerKey}-${item.id}`;
      const children = item.children ?? [];

      let xCenter;
      if (children.length === 0) {
        xCenter = leafCursor * X_GAP + NODE_WIDTH / 2 + 40;
        leafCursor += 1;
      } else {
        const childCenters = children.map((child) => layoutSubtree(child, depth + 1));
        xCenter = (childCenters[0] + childCenters[childCenters.length - 1]) / 2;
      }

      if (!seenKinds.includes(item.kind)) {
        seenKinds.push(item.kind);
      }

      const nextLayer =
        LAYER_ORDER.indexOf(layerKey) < LAYER_ORDER.length - 1
          ? LAYER_ORDER[LAYER_ORDER.indexOf(layerKey) + 1]
          : null;

      flowNodes.push({
        id: flowId,
        type: 'c4Node',
        position: {
          x: Math.round(xCenter - NODE_WIDTH / 2),
          y: LAYER_Y[layerKey] ?? depth * 240 + 40
        },
        width: NODE_WIDTH,
        height: NODE_HEIGHT,
        zIndex: 1,
        data: {
          rawId: item.id,
          kind: item.kind,
          name: item.name,
          technology: item.technology
            ? `${LAYER_BADGES[layerKey]} · ${item.technology}`
            : LAYER_BADGES[layerKey],
          description: item.description,
          layer: layerKey,
          nextLayer,
          parentNodeId: item.parentNodeId ?? null,
          onDrillDown: () =>
            onNodeDoubleClick?.({
              id: item.id,
              type: 'c4Node',
              data: {
                ...item,
                layer: layerKey,
                nextLayer
              }
            })
        }
      });

      for (const child of children) {
        const childLayer = child.layer || LAYER_ORDER[Math.min(depth + 1, 3)];
        const childFlowId = `tree-${childLayer}-${child.id}`;
        flowEdges.push({
          id: `tree-edge-${flowId}-${childFlowId}`,
          source: flowId,
          target: childFlowId,
          sourceHandle: 'bottom',
          targetHandle: 'top',
          type: 'c4Edge',
          label: `${layerKey} → ${childLayer}`,
          markerEnd: {
            type: MarkerType.ArrowClosed,
            width: 15,
            height: 15,
            color: '#6488b4'
          }
        });
      }

      return xCenter;
    }

    for (const root of roots) {
      layoutSubtree(root, 0);
      leafCursor += 0.35; // visual breathing room between separate root trees
    }

    return { flowNodes, flowEdges };
  }

  let built = $derived(buildTreeFlow(hierarchy));
  let nodes = $state.raw([]);
  let edges = $state.raw([]);

  $effect(() => {
    nodes = built.flowNodes;
    edges = built.flowEdges;
  });

  const legend = [
    { kind: 'system', label: '1 · Context (Root)' },
    { kind: 'container', label: '2 · Container' },
    { kind: 'component', label: '3 · Component' },
    { kind: 'codeClass', label: '4 · Code / Class Modules' }
  ];

  function handleNodeClick({ node }) {
    if (node.type === 'c4Node') onNodeSelect?.(node);
  }

  function handleNodeDoubleClick({ node }) {
    if (node.type === 'c4Node') {
      onNodeDoubleClick?.({
        ...node,
        id: node.data.rawId || node.id
      });
    }
  }

  function handlePaneClick() {
    onNodeSelect?.(null);
  }

  onMount(() => {
    requestAnimationFrame(() => {
      onReady?.(loadGeneration);
    });
  });
</script>

<div class="tree-canvas" aria-label="C4 hierarchy tree view">
  <SvelteFlowProvider>
    <SvelteFlow
      bind:nodes
      bind:edges
      {nodeTypes}
      {edgeTypes}
      fitView
      fitViewOptions={{ padding: 0.2 }}
      minZoom={0.2}
      maxZoom={1.5}
      zoomOnDoubleClick={false}
      proOptions={{ hideAttribution: true }}
      onnodeclick={handleNodeClick}
      onnodedoubleclick={handleNodeDoubleClick}
      onpaneclick={handlePaneClick}
    >
      <Background variant={BackgroundVariant.Dots} gap={22} size={1} color="#d7e3f1" />
      <Controls showInteractive={false} />
      <MiniMap
        position="top-right"
        width={140}
        height={95}
        pannable
        zoomable
        nodeColor={() => '#bcd0e8'}
        maskColor="rgba(29,78,216,0.06)"
      />
      <Panel position="top-left">
        <div class="tree-banner">
          <span class="tree-banner__title">Hierarchy Tree Order</span>
          <span class="tree-banner__order">
            Context (Root) → Container → Component → Code Class Modules
          </span>
          <Legend {legend} />
        </div>
      </Panel>
    </SvelteFlow>
  </SvelteFlowProvider>
</div>

<style>
  .tree-canvas {
    flex: 1;
    min-width: 0;
    min-height: 0;
    height: 100%;
    background: var(--canvas-bg);
  }

  .tree-banner {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 8px 12px;
    background: color-mix(in srgb, var(--surface) 94%, transparent);
    border: 1px solid var(--border);
    border-radius: 10px;
    box-shadow: var(--shadow-sm);
  }

  .tree-banner__title {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: var(--blue-700);
  }

  .tree-banner__order {
    font-size: 11.5px;
    font-weight: 600;
    color: var(--text);
  }
</style>
