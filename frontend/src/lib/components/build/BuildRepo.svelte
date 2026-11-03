<script>
  import { onDestroy } from 'svelte';
  import { fade } from 'svelte/transition';
  import { SvelteFlowProvider } from '@xyflow/svelte';
  import '@xyflow/svelte/dist/style.css';
  import { ARROWS, SHAPES, buildArchitecturePlan } from '../../buildCatalog.js';
  import {
    EMPTY_RAW_BY_LAYER,
    LAYERS,
    buildHierarchyFromLayers,
    getLayer,
    getNextLayerId,
    getPrevLayerId
  } from '../../diagramData.js';
  import { plainClone } from '../../plainClone.js';
  import LayerSelect from '../LayerSelect.svelte';
  import HierarchyTreeCanvas from '../HierarchyTreeCanvas.svelte';
  import OrthosLoader from '../OrthosLoader.svelte';
  import ToastBanner from './ToastBanner.svelte';
  import BuildCanvas from './BuildCanvas.svelte';
  import BuildPalette from './BuildPalette.svelte';
  import BuildPlanPanel from './BuildPlanPanel.svelte';

  const MIN_LOADER_MS = 900;

  let {
    active = true,
    layerId = 'context',
    rawByLayer = EMPTY_RAW_BY_LAYER,
    hierarchy = [],
    sourceRevision = 0,
    onLayerChange
  } = $props();

  function createInitialDiagrams(sourceMap = EMPTY_RAW_BY_LAYER) {
    /** @type {Record<string, { nodes: any[], edges: any[] }>} */
    const map = {};
    for (const item of LAYERS) {
      const layerData = getLayer(item.id, sourceMap);
      // plainClone avoids structuredClone failures on Svelte reactive Proxies.
      const nodes = plainClone(layerData.nodes).map((n) =>
        n.type === 'c4Boundary' ? { ...n, selectable: true, draggable: true } : n
      );
      const edges = plainClone(layerData.edges);
      map[item.id] = { nodes, edges };
    }
    return map;
  }

  let diagramsByLayer = $state.raw(createInitialDiagrams());
  let lastRevision = -1;
  $effect(() => {
    if (sourceRevision !== lastRevision) {
      lastRevision = sourceRevision;
      diagramsByLayer = createInitialDiagrams(rawByLayer);
    }
  });

  let collapsed = $state(false);
  let buildLayerId = $derived(layerId);
  let viewMode = $state('layer'); // 'layer' | 'tree'
  let loading = $state(false);
  let loadGeneration = $state(0);
  let loaderStartedAt = Date.now();
  let planOpen = $state(false);
  let planCollapsed = $state(false);
  let plan = $state(null);
  let planApproved = $state(false);
  let activeArrowId = $state('uses');
  let toast = $state(null);
  let canvasRef = $state();
  let historyState = $state({ canUndo: false, canRedo: false, hasClipboard: false });

  let layer = $derived(getLayer(buildLayerId, rawByLayer));
  // Build hierarchy only when Tree view is active — avoid scanning all layers while editing.
  let activeHierarchy = $derived.by(() => {
    if (viewMode !== 'tree') return hierarchy ?? [];
    if (hierarchy && hierarchy.length > 0) return hierarchy;
    return buildHierarchyFromLayers(rawByLayer);
  });

  /** @type {ReturnType<typeof setInterval> | undefined} */
  let countdown;
  /** @type {ReturnType<typeof setTimeout> | undefined} */
  let hideTimer;

  function selectArrow(component) {
    if (component.kind === 'Arrow') activeArrowId = component.id;
  }

  function handleLayerChange(id) {
    if (id === buildLayerId && viewMode === 'layer') return;
    clearTimeout(hideTimer);
    loadGeneration += 1;
    loaderStartedAt = Date.now();
    loading = true;
    viewMode = 'layer';
    onLayerChange?.(id);
    if (planOpen) {
      const nextLayer = getLayer(id, rawByLayer);
      const nextDiagram = diagramsByLayer[id];
      plan = buildArchitecturePlan(nextDiagram.nodes, nextDiagram.edges, nextLayer.title);
      planApproved = false;
    }
  }

  function handleViewModeChange(mode) {
    if (mode === viewMode) return;
    clearTimeout(hideTimer);
    loadGeneration += 1;
    loaderStartedAt = Date.now();
    loading = true;
    viewMode = mode;
  }

  function handleNodeDoubleClick(node) {
    if (!node) return;
    const sourceLayer = node.data?.layer || buildLayerId;
    const nextLayerId = getNextLayerId(sourceLayer);
    if (!nextLayerId) return;
    handleLayerChange(nextLayerId);
  }

  function handleBoundaryClick(boundaryNode) {
    if (!boundaryNode) return;
    const targetUpperLayer =
      boundaryNode.data?.targetUpperLayer || getPrevLayerId(buildLayerId);
    if (!targetUpperLayer || targetUpperLayer === buildLayerId) return;
    handleLayerChange(targetUpperLayer);
  }

  function handleCanvasReady(generation) {
    if (!loading) return;
    const wait = Math.max(0, MIN_LOADER_MS - (Date.now() - loaderStartedAt));
    clearTimeout(hideTimer);
    hideTimer = setTimeout(() => {
      if (generation !== loadGeneration) return;
      loading = false;
    }, wait);
  }

  function handleDiagramChange(layerIdVal, nodes, edges) {
    // Reassign map so $state.raw consumers see a new reference when needed.
    diagramsByLayer = {
      ...diagramsByLayer,
      [layerIdVal]: { nodes, edges }
    };
    // Skip plan rebuild during drag/edit churn — user can hit Plan again.
  }

  function generatePlan() {
    const diagram =
      canvasRef?.getDiagram?.() ?? diagramsByLayer[buildLayerId] ?? { nodes: [], edges: [] };
    plan = buildArchitecturePlan(diagram.nodes, diagram.edges, layer.title);
    planApproved = false;
    planOpen = true;
    planCollapsed = false;
  }

  function refreshIfOpen() {
    if (!planOpen) return;
    const diagram =
      canvasRef?.getDiagram?.() ?? diagramsByLayer[buildLayerId] ?? { nodes: [], edges: [] };
    plan = buildArchitecturePlan(diagram.nodes, diagram.edges, layer.title);
    planApproved = false;
  }

  function approvePlan() {
    planApproved = true;
    toast = { id: Date.now(), name: `${layer.title} Architecture`, remaining: 10 };
    clearInterval(countdown);
    countdown = setInterval(() => {
      if (!toast || toast.remaining <= 1) {
        clearInterval(countdown);
        toast = null;
        return;
      }
      toast = { ...toast, remaining: toast.remaining - 1 };
    }, 1000);
  }

  function onDragStart(event, component) {
    selectArrow(component);
    event.dataTransfer?.setData('application/x-c4-component', component.id);
    event.dataTransfer?.setData('text/plain', component.id);
    if (event.dataTransfer) event.dataTransfer.effectAllowed = 'copy';
  }

  function addToCanvas(component) {
    selectArrow(component);
    canvasRef?.addItem(component.id);
    refreshIfOpen();
  }

  export function handleShortcutCommand(cmd) {
    if (viewMode === 'tree') {
      if (cmd === 'toggle-tree') {
        handleViewModeChange('layer');
        return 'Switched to Layer view';
      }
      return null;
    }

    switch (cmd) {
      case 'undo':
        return canvasRef?.undo?.() ? 'Undid canvas change (⌘Z / Ctrl+Z)' : null;
      case 'redo':
        return canvasRef?.redo?.() ? 'Redid canvas change (⌘Y / Ctrl+Y)' : null;
      case 'copy': {
        const count = canvasRef?.copySelected?.() ?? 0;
        return count > 0 ? `Copied ${count} component${count > 1 ? 's' : ''} (⌘C / Ctrl+C)` : null;
      }
      case 'cut': {
        const count = canvasRef?.cutSelected?.() ?? 0;
        return count > 0 ? `Cut ${count} component${count > 1 ? 's' : ''} (⌘X / Ctrl+X)` : null;
      }
      case 'paste': {
        const count = canvasRef?.pasteClipboard?.() ?? 0;
        return count > 0 ? `Pasted ${count} component${count > 1 ? 's' : ''} (⌘V / Ctrl+V)` : null;
      }
      case 'duplicate': {
        const count = canvasRef?.duplicateSelected?.() ?? 0;
        return count > 0
          ? `Duplicated ${count} component${count > 1 ? 's' : ''} (⌘D / Ctrl+D)`
          : null;
      }
      case 'delete': {
        const count = canvasRef?.deleteSelected?.() ?? 0;
        return count > 0 ? `Deleted ${count} selected item${count > 1 ? 's' : ''}` : null;
      }
      case 'select-all': {
        const count = canvasRef?.selectAllNodes?.() ?? 0;
        return count > 0 ? `Selected all ${count} components (⌘A / Ctrl+A)` : null;
      }
      case 'escape':
        canvasRef?.clearSelection?.();
        return 'Cleared selection';
      case 'toggle-tree':
        handleViewModeChange(viewMode === 'tree' ? 'layer' : 'tree');
        return `Switched to ${viewMode === 'tree' ? 'Tree' : 'Layer'} view`;
      default:
        return null;
    }
  }

  onDestroy(() => {
    clearInterval(countdown);
    clearTimeout(hideTimer);
  });
</script>

<div class="build" class:build--inactive={!active}>
  <BuildPalette
    shapes={SHAPES}
    arrows={ARROWS}
    {activeArrowId}
    {collapsed}
    onToggleCollapse={() => (collapsed = !collapsed)}
    onDragStart={active ? onDragStart : undefined}
    onAdd={active ? addToCanvas : undefined}
  />

  <section
    class="work-area"
    class:work-area--inactive={!active}
    aria-label="Architecture work area"
    aria-busy={loading}
  >
    <header class="work-area__bar">
      <p class="work-area__hint">
        {#if !active}
          <strong>Developer idle</strong> · Analyze a repository to unlock the build canvas
        {:else if viewMode === 'tree'}
          <strong>Hierarchy Tree View</strong> · Context → Container → Component → Code Class Modules
        {:else}
          <strong>{layer.title} layer</strong> · {layer.subtitle}
        {/if}
      </p>
      <div class="work-area__actions">
        {#if active && viewMode === 'layer'}
          <div class="shortcut-strip" role="group" aria-label="Canvas history and clipboard actions">
            <button
              type="button"
              class="shortcut-btn"
              disabled={!historyState.canUndo}
              title="Undo (⌘Z / Ctrl+Z)"
              onclick={() => canvasRef?.undo?.()}
            >
              ↶ Undo
            </button>
            <button
              type="button"
              class="shortcut-btn"
              disabled={!historyState.canRedo}
              title="Redo (⌘Y / Ctrl+Y / ⌘⇧Z)"
              onclick={() => canvasRef?.redo?.()}
            >
              ↷ Redo
            </button>
            <button
              type="button"
              class="shortcut-btn"
              title="Copy selected (⌘C / Ctrl+C)"
              onclick={() => canvasRef?.copySelected?.()}
            >
              Copy
            </button>
            <button
              type="button"
              class="shortcut-btn"
              disabled={!historyState.hasClipboard}
              title="Paste (⌘V / Ctrl+V)"
              onclick={() => canvasRef?.pasteClipboard?.()}
            >
              Paste
            </button>
          </div>
        {/if}
        {#if planApproved}
          <span class="work-area__status">Plan approved</span>
        {/if}
        <div class="view-toggle" role="group" aria-label="Developer visualization mode">
          <button
            type="button"
            class="view-toggle__btn"
            class:active={viewMode === 'layer'}
            aria-pressed={viewMode === 'layer'}
            disabled={!active}
            onclick={() => handleViewModeChange('layer')}
          >
            Layer
          </button>
          <button
            type="button"
            class="view-toggle__btn"
            class:active={viewMode === 'tree'}
            aria-pressed={viewMode === 'tree'}
            disabled={!active}
            onclick={() => handleViewModeChange('tree')}
          >
            Tree
          </button>
        </div>
        <LayerSelect
          idPrefix="build-layer"
          value={buildLayerId}
          disabled={!active || viewMode === 'tree'}
          onChange={handleLayerChange}
        />
        <button type="button" class="plan-button" disabled={!active} onclick={generatePlan}>
          Plan
        </button>
      </div>
    </header>
    <div class="work-area__canvas">
      {#if active}
        {#key `${buildLayerId}-${viewMode}-${sourceRevision}-${active}`}
          {#if viewMode === 'tree'}
            <HierarchyTreeCanvas
              hierarchy={activeHierarchy}
              {loadGeneration}
              onNodeDoubleClick={handleNodeDoubleClick}
              onReady={handleCanvasReady}
            />
          {:else}
            <SvelteFlowProvider>
              <BuildCanvas
                bind:this={canvasRef}
                {activeArrowId}
                initialNodes={diagramsByLayer[buildLayerId].nodes}
                initialEdges={diagramsByLayer[buildLayerId].edges}
                legend={layer.legend}
                {loadGeneration}
                onChange={(nodes, edges) => handleDiagramChange(buildLayerId, nodes, edges)}
                onHistoryStateChange={(state) => (historyState = state)}
                onNodeDoubleClick={handleNodeDoubleClick}
                onBoundaryClick={handleBoundaryClick}
                onReady={handleCanvasReady}
              />
            </SvelteFlowProvider>
          {/if}
        {/key}
        {#if loading}
          <div class="work-area__loader" out:fade={{ duration: 180 }}>
            <OrthosLoader
              label={viewMode === 'tree'
                ? 'Loading C4 Hierarchy Tree'
                : `Loading ${layer.title} diagram`}
            />
          </div>
        {/if}
      {:else}
        <div class="canvas-idle" role="status">
          <p class="canvas-idle__eyebrow">Build canvas locked</p>
          <h2 class="canvas-idle__title">Analyze a repository first</h2>
          <p class="canvas-idle__body">
            The Developer canvas stays inactive until analysis finishes. Then you can edit layers, plan, and refine the architecture.
          </p>
        </div>
      {/if}
    </div>
  </section>

  {#if planOpen && plan}
    <BuildPlanPanel
      {plan}
      collapsed={planCollapsed}
      approved={planApproved}
      onToggleCollapse={() => (planCollapsed = !planCollapsed)}
      onRefresh={generatePlan}
      onApprove={approvePlan}
    />
  {/if}
</div>

{#if toast}
  {#key toast.id}
    <ToastBanner name={toast.name} remaining={toast.remaining} />
  {/key}
{/if}

<style>
  .build {
    flex: 1;
    min-height: 0;
    display: flex;
    gap: 16px;
    padding: 16px 24px 20px;
  }

  .build--inactive :global(.palette) {
    opacity: 0.45;
    pointer-events: none;
    filter: grayscale(0.35);
  }

  .work-area {
    flex: 1;
    min-width: 0;
    min-height: 0;
    display: flex;
    flex-direction: column;
    background: var(--canvas-bg);
    border: 1px solid var(--border);
    border-radius: 14px;
    box-shadow: var(--shadow-sm);
    overflow: hidden;
  }

  .work-area--inactive {
    background: color-mix(in srgb, var(--canvas-bg) 70%, #dbe4f0);
  }

  .work-area__bar {
    position: relative;
    z-index: 10;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 8px 14px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    font-size: 12px;
    color: var(--text-muted);
  }

  .work-area__hint {
    margin: 0;
  }

  .work-area__actions {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-shrink: 0;
  }

  .shortcut-strip {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px;
    border-radius: 8px;
    background: var(--surface-muted);
    border: 1px solid var(--border);
  }

  .shortcut-btn {
    padding: 4px 8px;
    border: none;
    border-radius: 6px;
    background: transparent;
    color: var(--text-muted);
    font-size: 11.5px;
    font-weight: 700;
    cursor: pointer;
  }

  .shortcut-btn:hover:not(:disabled) {
    background: var(--surface);
    color: var(--blue-700);
  }

  .shortcut-btn:disabled {
    opacity: 0.42;
    cursor: not-allowed;
  }

  .work-area__status {
    font-weight: 700;
    color: var(--blue-700);
  }

  .view-toggle {
    display: inline-flex;
    padding: 3px;
    background: var(--surface-muted);
    border: 1px solid var(--border-strong);
    border-radius: 10px;
    gap: 2px;
  }

  .view-toggle__btn {
    padding: 5px 11px;
    border: none;
    border-radius: 7px;
    background: transparent;
    color: var(--text-muted);
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
  }

  .view-toggle__btn.active {
    background: var(--blue-700);
    color: #ffffff;
    box-shadow: var(--shadow-sm);
  }

  .plan-button {
    padding: 6px 16px;
    border: none;
    border-radius: 9px;
    background: var(--blue-700);
    color: #fff;
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
    box-shadow: var(--shadow-sm);
  }

  .plan-button:hover:not(:disabled) {
    background: var(--blue-900);
  }

  .plan-button:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  .view-toggle__btn:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  .work-area__canvas {
    position: relative;
    flex: 1;
    min-height: 0;
    display: flex;
  }

  .canvas-idle {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 32px;
    text-align: center;
    color: var(--text-muted);
    background:
      radial-gradient(circle at 50% 35%, color-mix(in srgb, var(--blue-100, #dbeafe) 55%, transparent), transparent 55%),
      repeating-linear-gradient(
        -12deg,
        transparent,
        transparent 11px,
        color-mix(in srgb, var(--border) 55%, transparent) 11px,
        color-mix(in srgb, var(--border) 55%, transparent) 12px
      );
  }

  .canvas-idle__eyebrow {
    margin: 0;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-faint);
  }

  .canvas-idle__title {
    margin: 0;
    font-size: 22px;
    font-weight: 750;
    color: var(--text);
  }

  .canvas-idle__body {
    margin: 0;
    max-width: 420px;
    font-size: 13.5px;
    line-height: 1.45;
  }

  .work-area__loader {
    position: absolute;
    inset: 0;
    z-index: 6;
    display: flex;
    align-items: center;
    justify-content: center;
    background: color-mix(in srgb, var(--canvas-bg) 86%, white);
  }

  @media (max-width: 960px) {
    .build {
      flex-direction: column;
      overflow: auto;
    }

    .work-area {
      min-height: 440px;
    }
  }
</style>
