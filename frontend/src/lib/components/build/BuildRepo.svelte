<script>
  import { onDestroy } from 'svelte';
  import { fade } from 'svelte/transition';
  import { SvelteFlowProvider } from '@xyflow/svelte';
  import '@xyflow/svelte/dist/style.css';
  import { ARROWS, SHAPES, buildArchitecturePlan } from '../../buildCatalog.js';
  import { DEFAULT_RAW_BY_LAYER, LAYERS, buildHierarchyFromLayers, getLayer } from '../../diagramData.js';
  import LayerSelect from '../LayerSelect.svelte';
  import HierarchyTreeCanvas from '../HierarchyTreeCanvas.svelte';
  import PfizerLoader from '../PfizerLoader.svelte';
  import ShapeIcon from './ShapeIcon.svelte';
  import ToastBanner from './ToastBanner.svelte';
  import BuildCanvas from './BuildCanvas.svelte';

  const MIN_LOADER_MS = 900;

  let {
    active = true,
    layerId = 'context',
    rawByLayer = DEFAULT_RAW_BY_LAYER,
    hierarchy = [],
    sourceRevision = 0,
    onLayerChange
  } = $props();

  function createInitialDiagrams(sourceMap = DEFAULT_RAW_BY_LAYER) {
    /** @type {Record<string, { nodes: any[], edges: any[] }>} */
    const map = {};
    for (const item of LAYERS) {
      const layerData = getLayer(item.id, sourceMap);
      map[item.id] = {
        nodes: structuredClone(layerData.nodes).map((n) =>
          n.type === 'c4Boundary' ? { ...n, selectable: true, draggable: true } : n
        ),
        edges: structuredClone(layerData.edges)
      };
    }
    return map;
  }

  const diagramsByLayer = createInitialDiagrams();
  let lastRevision = -1;
  $effect(() => {
    if (sourceRevision !== lastRevision) {
      lastRevision = sourceRevision;
      const fresh = createInitialDiagrams(rawByLayer);
      for (const key of Object.keys(fresh)) {
        diagramsByLayer[key] = fresh[key];
      }
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

  let layer = $derived(getLayer(buildLayerId, rawByLayer));
  let activeHierarchy = $derived(
    hierarchy && hierarchy.length > 0 ? hierarchy : buildHierarchyFromLayers(rawByLayer)
  );

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

  function handleCanvasReady(generation) {
    if (!loading) return;
    const wait = Math.max(0, MIN_LOADER_MS - (Date.now() - loaderStartedAt));
    clearTimeout(hideTimer);
    hideTimer = setTimeout(() => {
      if (generation !== loadGeneration) return;
      loading = false;
    }, wait);
  }

  function handleDiagramChange(layerId, nodes, edges) {
    diagramsByLayer[layerId] = { nodes, edges };
    if (planOpen && layerId === buildLayerId) {
      plan = buildArchitecturePlan(nodes, edges, layer.title);
      planApproved = false;
    }
  }

  function generatePlan() {
    const diagram = canvasRef?.getDiagram?.() ?? diagramsByLayer[buildLayerId] ?? { nodes: [], edges: [] };
    plan = buildArchitecturePlan(diagram.nodes, diagram.edges, layer.title);
    planApproved = false;
    planOpen = true;
    planCollapsed = false;
  }

  function refreshIfOpen() {
    if (!planOpen) return;
    const diagram = canvasRef?.getDiagram?.() ?? diagramsByLayer[buildLayerId] ?? { nodes: [], edges: [] };
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

  onDestroy(() => {
    clearInterval(countdown);
    clearTimeout(hideTimer);
  });
</script>

<div class="build">
  <aside class="palette" class:collapsed aria-label="Design components">
    <div class="palette__bar">
      {#if !collapsed}
        <span class="palette__title">Components</span>
      {/if}
      <button
        type="button"
        class="palette__toggle"
        aria-expanded={!collapsed}
        aria-controls="palette-body"
        aria-label={collapsed ? 'Expand components panel' : 'Collapse components panel'}
        onclick={() => (collapsed = !collapsed)}
      >
        {collapsed ? '»' : '«'}
      </button>
    </div>

    <div id="palette-body" class="palette__body" hidden={collapsed}>
      <div class="palette__group">
        <h2>Shapes</h2>
        <ul>
          {#each SHAPES as component (component.id)}
            <li
              class="palette__item"
              draggable="true"
              ondragstart={(event) => onDragStart(event, component)}
            >
              <span class="palette__icon" aria-hidden="true">
                <ShapeIcon id={component.id} />
              </span>
              <div class="palette__text">
                <span class="palette__name">{component.name}</span>
                <span class="palette__kind">Drag to work area</span>
              </div>
              <button
                type="button"
                class="palette__add"
                aria-label="Add {component.name} to work area"
                onclick={() => addToCanvas(component)}
              >
                +
              </button>
            </li>
          {/each}
        </ul>
      </div>

      <div class="palette__group">
        <h2>Arrows</h2>
        <ul>
          {#each ARROWS as component (component.id)}
            <li
              class="palette__item"
              class:active-arrow={activeArrowId === component.id}
              draggable="true"
              ondragstart={(event) => onDragStart(event, component)}
            >
              <span class="palette__icon" aria-hidden="true">
                <ShapeIcon id={component.id} />
              </span>
              <div class="palette__text">
                <span class="palette__name">{component.name}</span>
                <span class="palette__kind">Drag or connect</span>
              </div>
              <button
                type="button"
                class="palette__add"
                aria-label="Add {component.name} arrow to work area"
                onclick={() => addToCanvas(component)}
              >
                +
              </button>
            </li>
          {/each}
        </ul>
      </div>
    </div>
  </aside>

  <section class="work-area" aria-label="Architecture work area" aria-busy={loading}>
    <header class="work-area__bar">
      <p class="work-area__hint">
        {#if viewMode === 'tree'}
          <strong>Hierarchy Tree View</strong> · Context → Container → Component → Code Class Modules
        {:else}
          <strong>{layer.title} layer</strong> · {layer.subtitle} — Drag shapes and arrows onto the
          work area, then click <strong>Plan</strong> to generate an implementation plan.
        {/if}
      </p>
      <div class="work-area__actions">
        {#if planApproved}
          <span class="work-area__status">Plan approved</span>
        {/if}
        <div class="view-toggle" role="group" aria-label="Developer visualization mode">
          <button
            type="button"
            class="view-toggle__btn"
            class:active={viewMode === 'layer'}
            aria-pressed={viewMode === 'layer'}
            onclick={() => handleViewModeChange('layer')}
          >
            Layer
          </button>
          <button
            type="button"
            class="view-toggle__btn"
            class:active={viewMode === 'tree'}
            aria-pressed={viewMode === 'tree'}
            onclick={() => handleViewModeChange('tree')}
          >
            Tree
          </button>
        </div>
        <LayerSelect
          idPrefix="build-layer"
          value={buildLayerId}
          disabled={viewMode === 'tree'}
          onChange={handleLayerChange}
        />
        <button type="button" class="plan-button" onclick={generatePlan}>
          Plan
        </button>
      </div>
    </header>
    <div class="work-area__canvas">
      {#key `${buildLayerId}-${viewMode}-${sourceRevision}-${active}`}
        {#if viewMode === 'tree'}
          <HierarchyTreeCanvas
            hierarchy={activeHierarchy}
            {loadGeneration}
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
              onReady={handleCanvasReady}
            />
          </SvelteFlowProvider>
        {/if}
      {/key}
      {#if loading}
        <div class="work-area__loader" out:fade={{ duration: 180 }}>
          <PfizerLoader
            label={viewMode === 'tree'
              ? 'Loading C4 Hierarchy Tree'
              : `Loading ${layer.title} diagram`}
          />
        </div>
      {/if}
    </div>
  </section>

  {#if planOpen && plan}
    <aside class="plan-panel" class:collapsed={planCollapsed} aria-label="Implementation plan">
      <div class="plan-panel__bar">
        <button
          type="button"
          class="palette__toggle"
          aria-expanded={!planCollapsed}
          aria-controls="plan-panel-body"
          aria-label={planCollapsed ? 'Expand implementation plan panel' : 'Collapse implementation plan panel'}
          onclick={() => (planCollapsed = !planCollapsed)}
        >
          {planCollapsed ? '«' : '»'}
        </button>
        {#if !planCollapsed}
          <div class="plan-panel__heading">
            <span class="plan-panel__eyebrow">For human approval</span>
            <span class="plan-panel__title">Implementation Plan</span>
          </div>
        {/if}
      </div>

      <div id="plan-panel-body" class="plan-panel__body" hidden={planCollapsed}>
        <p class="plan-panel__summary">{plan.summary}</p>

        {#if plan.boundaryItems.length > 0}
          <section class="plan-panel__section">
            <h3>Boundaries in this diagram</h3>
            <ul>
              {#each plan.boundaryItems as item}
                <li>{item}</li>
              {/each}
            </ul>
          </section>
        {/if}

        {#if plan.componentItems.length > 0}
          <section class="plan-panel__section">
            <h3>Components read from the canvas ({plan.componentCount})</h3>
            <ol>
              {#each plan.componentItems as item}
                <li>{item}</li>
              {/each}
            </ol>
          </section>
        {/if}

        {#if plan.relationshipItems.length > 0}
          <section class="plan-panel__section">
            <h3>Connections and data flow ({plan.edgeCount})</h3>
            <ol>
              {#each plan.relationshipItems as item}
                <li>{item}</li>
              {/each}
            </ol>
          </section>
        {/if}

        {#if plan.steps.length > 0}
          <section class="plan-panel__section">
            <h3>Proposed build sequence</h3>
            <ol>
              {#each plan.steps as step}
                <li>{step}</li>
              {/each}
            </ol>
          </section>
        {/if}

        <footer class="plan-panel__footer">
          <button type="button" class="plan-panel__refresh" onclick={generatePlan}>
            Re-read diagram
          </button>
          <button type="button" class="plan-panel__approve" onclick={approvePlan}>
            {planApproved ? 'Approved ✓' : 'Approve Plan'}
          </button>
        </footer>
      </div>
    </aside>
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

  .palette {
    width: 280px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    min-height: 0;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    box-shadow: var(--shadow-sm);
    transition: width 0.16s ease;
  }

  .palette.collapsed {
    width: 52px;
  }

  .palette__bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 10px 10px 14px;
    border-bottom: 1px solid var(--border);
  }

  .palette.collapsed .palette__bar {
    justify-content: center;
    padding: 10px 6px;
    border-bottom: none;
  }

  .palette__title {
    font-size: 13px;
    font-weight: 700;
  }

  .palette__toggle {
    width: 30px;
    height: 30px;
    flex-shrink: 0;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--surface-muted);
    color: var(--blue-700);
    font-weight: 700;
    cursor: pointer;
  }

  .palette__body {
    overflow: auto;
    padding: 12px;
  }

  .palette__body[hidden] {
    display: none;
  }

  .palette__group + .palette__group {
    margin-top: 16px;
    padding-top: 12px;
    border-top: 1px solid var(--border);
  }

  h2 {
    margin: 0 0 8px;
    font-size: 11px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--text-faint);
  }

  .palette ul {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .palette__item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 4px;
    border: 1px solid transparent;
    border-radius: 10px;
    cursor: grab;
  }

  .palette__item:hover {
    background: var(--surface-muted);
    border-color: var(--border);
  }

  .palette__item.active-arrow {
    background: var(--blue-50);
    border-color: var(--blue-200);
  }

  .palette__icon {
    width: 42px;
    height: 42px;
    flex-shrink: 0;
    display: grid;
    place-items: center;
    border: 1px solid var(--border-strong);
    border-radius: 10px;
    background: var(--blue-50);
    color: var(--blue-700);
  }

  .palette__text {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  .palette__name {
    font-size: 13.5px;
    font-weight: 700;
  }

  .palette__kind {
    font-size: 11px;
    color: var(--text-faint);
  }

  .palette__add {
    width: 26px;
    height: 26px;
    flex-shrink: 0;
    border: 1px solid var(--border);
    border-radius: 7px;
    background: var(--surface);
    color: var(--text-muted);
    font-weight: 700;
    cursor: pointer;
  }

  .palette__add:hover {
    border-color: var(--blue-500);
    color: var(--blue-700);
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

  .plan-button:hover {
    background: var(--blue-900);
  }

  .work-area__canvas {
    position: relative;
    flex: 1;
    min-height: 0;
    display: flex;
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

  .plan-panel {
    width: 360px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    min-height: 0;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    box-shadow: var(--shadow-sm);
    transition: width 0.16s ease;
  }

  .plan-panel.collapsed {
    width: 52px;
  }

  .plan-panel__bar {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px 10px 10px;
    border-bottom: 1px solid var(--border);
  }

  .plan-panel.collapsed .plan-panel__bar {
    justify-content: center;
    padding: 10px 6px;
    border-bottom: none;
  }

  .plan-panel__heading {
    display: flex;
    flex-direction: column;
    line-height: 1.2;
  }

  .plan-panel__eyebrow {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--blue-700);
  }

  .plan-panel__title {
    font-size: 14px;
    font-weight: 700;
    color: var(--text);
  }

  .plan-panel__body {
    overflow: auto;
    padding: 14px 16px 16px;
    display: flex;
    flex-direction: column;
    gap: 14px;
    font-size: 13px;
    line-height: 1.5;
  }

  .plan-panel__body[hidden] {
    display: none;
  }

  .plan-panel__summary {
    margin: 0;
    padding: 10px 12px;
    border-radius: 10px;
    background: var(--blue-50);
    border: 1px solid var(--blue-200);
    color: var(--blue-900);
  }

  .plan-panel__section h3 {
    font-size: 12px;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--text-muted);
    margin: 0 0 6px;
  }

  .plan-panel__section ol,
  .plan-panel__section ul {
    margin: 0;
    padding-left: 1.2rem;
    color: var(--text);
  }

  .plan-panel__section li {
    margin-bottom: 6px;
  }

  .plan-panel__footer {
    margin-top: auto;
    padding-top: 12px;
    border-top: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .plan-panel__refresh {
    padding: 7px 12px;
    border: 1px solid var(--border-strong);
    border-radius: 9px;
    background: var(--surface);
    color: var(--text);
    font-size: 12.5px;
    font-weight: 600;
    cursor: pointer;
  }

  .plan-panel__approve {
    padding: 7px 14px;
    border: none;
    border-radius: 9px;
    background: var(--blue-700);
    color: #fff;
    font-size: 12.5px;
    font-weight: 700;
    cursor: pointer;
  }

  .plan-panel__approve:hover {
    background: var(--blue-900);
  }

  @media (max-width: 960px) {
    .build {
      flex-direction: column;
      overflow: auto;
    }

    .palette,
    .palette.collapsed,
    .plan-panel,
    .plan-panel.collapsed {
      width: auto;
    }

    .work-area {
      min-height: 440px;
    }
  }
</style>
