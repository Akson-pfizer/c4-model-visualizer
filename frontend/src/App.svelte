<script>
  import { onDestroy } from 'svelte';
  import { fade } from 'svelte/transition';
  import AppHeader from './lib/components/AppHeader.svelte';
  import SourceBar from './lib/components/SourceBar.svelte';
  import LayerSelect from './lib/components/LayerSelect.svelte';
  import DiagramCanvas from './lib/components/DiagramCanvas.svelte';
  import HierarchyTreeCanvas from './lib/components/HierarchyTreeCanvas.svelte';
  import DetailPanel from './lib/components/DetailPanel.svelte';
  import PfizerLoader from './lib/components/PfizerLoader.svelte';
  import BuildRepo from './lib/components/build/BuildRepo.svelte';
  import CodeAnalysisView from './lib/components/analysis/CodeAnalysisView.svelte';
  import { formatFriendlyError } from './lib/analysisCatalog.js';
  import {
    DEFAULT_RAW_BY_LAYER,
    buildHierarchyFromLayers,
    getLayer
  } from './lib/diagramData.js';

  const TABS = [
    { id: 'read', label: 'Visualizer' },
    { id: 'build', label: 'Developer' },
    { id: 'analysis', label: 'Code Analysis' }
  ];

  // Long enough for one full turn of the spinning "z", so the loader
  // doesn't flicker off before the diagram has fitted.
  const MIN_LOADER_MS = 900;

  let tab = $state('read');
  /** @type {Record<string, HTMLButtonElement | undefined>} */
  let tabButtons = $state({});

  let selectedLayerId = $state('context');
  let viewMode = $state('layer'); // 'layer' | 'tree'
  let selectedNode = $state(null);
  let loading = $state(true);
  let loadGeneration = $state(0);
  let loaderStartedAt = Date.now();

  // Repository source & multi-agent model state
  let activeSource = $state('');
  let activeRepoName = $state('Internet Banking System (Demo)');
  let analyzingSource = $state(false);
  let sourceError = $state(null);
  let agentReports = $state([]);
  let rawByLayer = $state(DEFAULT_RAW_BY_LAYER);
  let customHierarchy = $state(null);
  let sourceRevision = $state(0);

  let layer = $derived(getLayer(selectedLayerId, rawByLayer));
  let hierarchy = $derived(customHierarchy ?? buildHierarchyFromLayers(rawByLayer));

  /**
   * Flat guard-clause helper replacing nested ternaries (SonarQube S3358).
   */
  function getLoaderLabel(isAnalyzing, currentViewMode, layerTitle) {
    if (isAnalyzing) {
      return 'Running Manager, Supervisor & 4 Layer Subagents';
    }
    if (currentViewMode === 'tree') {
      return 'Loading C4 Hierarchy Tree';
    }
    return `Loading ${layerTitle} diagram`;
  }

  let loaderLabel = $derived(getLoaderLabel(analyzingSource, viewMode, layer.title));

  /** @type {ReturnType<typeof setTimeout> | undefined} */
  let hideTimer;

  function triggerLoader() {
    clearTimeout(hideTimer);
    loadGeneration += 1;
    loaderStartedAt = Date.now();
    loading = true;
  }

  function handleLayerChange(id) {
    if (id === selectedLayerId && viewMode === 'layer') return;
    triggerLoader();
    viewMode = 'layer';
    selectedLayerId = id;
    selectedNode = null;
  }

  function handleViewModeChange(mode) {
    if (mode === viewMode) return;
    triggerLoader();
    viewMode = mode;
    selectedNode = null;
  }

  function handleDiagramReady(generation) {
    const wait = Math.max(0, MIN_LOADER_MS - (Date.now() - loaderStartedAt));
    clearTimeout(hideTimer);
    hideTimer = setTimeout(() => {
      if (generation !== loadGeneration) return;
      loading = false;
    }, wait);
  }

  function handleNodeSelect(node) {
    selectedNode = node;
  }

  async function analyzeRepositorySource(sourceInput, selectedType = 'local') {
    sourceError = null;
    analyzingSource = true;
    triggerLoader();

    try {
      const response = await fetch('/api/c4/model', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source: sourceInput,
          source_type: selectedType,
          use_llm: false
        })
      });

      if (!response.ok) {
        const errBody = await response.json().catch(() => ({}));
        throw new Error(errBody.detail || `Backend returned status ${response.status}`);
      }

      const payload = await response.json();
      rawByLayer = payload.layers;
      customHierarchy = payload.hierarchy;
      agentReports = payload.agents ?? [];
      activeSource = payload.source;
      activeRepoName = `${payload.repo_name} (${payload.source_type})`;
      sourceRevision += 1;
      selectedNode = null;
    } catch (err) {
      sourceError = formatFriendlyError(err, 'Repository Analysis');
      loading = false;
    } finally {
      analyzingSource = false;
    }
  }

  function resetToDemoSource() {
    sourceError = null;
    triggerLoader();
    rawByLayer = DEFAULT_RAW_BY_LAYER;
    customHierarchy = null;
    agentReports = [];
    activeSource = '';
    activeRepoName = 'Internet Banking System (Demo)';
    sourceRevision += 1;
    selectedNode = null;
  }

  function selectTab(id, shouldFocus = false) {
    tab = id;
    if (shouldFocus) tabButtons[id]?.focus();
  }

  function onTabKeydown(event) {
    const index = TABS.findIndex((item) => item.id === tab);
    if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
      event.preventDefault();
      const delta = event.key === 'ArrowRight' ? 1 : -1;
      const next = TABS[(index + delta + TABS.length) % TABS.length];
      selectTab(next.id, true);
    } else if (event.key === 'Home') {
      event.preventDefault();
      selectTab(TABS[0].id, true);
    } else if (event.key === 'End') {
      event.preventDefault();
      selectTab(TABS.at(-1).id, true);
    }
  }

  onDestroy(() => clearTimeout(hideTimer));
</script>

<AppHeader />

<SourceBar
  source={activeSource}
  analyzing={analyzingSource}
  error={sourceError}
  {activeRepoName}
  agents={agentReports}
  onAnalyze={analyzeRepositorySource}
  onResetDemo={resetToDemoSource}
/>

<div class="app-tabs" role="tablist" aria-label="Repository mode">
  {#each TABS as item (item.id)}
    <button
      type="button"
      role="tab"
      id="tab-{item.id}"
      class="app-tabs__tab"
      aria-selected={tab === item.id}
      aria-controls="panel-{item.id}"
      tabindex={tab === item.id ? 0 : -1}
      bind:this={tabButtons[item.id]}
      onclick={() => selectTab(item.id)}
      onkeydown={onTabKeydown}
    >
      {item.label}
    </button>
  {/each}
</div>

<div class="app-panels">
  <div class="app-panel" role="tabpanel" id="panel-read" aria-labelledby="tab-read" hidden={tab !== 'read'}>
    <main class="app-main" aria-busy={loading}>
      <div class="layer-stage">
        <div class="layer-view">
          <section class="read-area" aria-label="Interactive diagram area">
            <header class="read-area__bar">
              <p class="read-area__hint">
                {#if viewMode === 'tree'}
                  <strong>Hierarchy Tree View</strong> · Context → Container → Component → Code Class Modules
                {:else}
                  <strong>{layer.title} layer</strong> · {layer.subtitle}
                {/if}
              </p>
              <div class="read-area__actions">
                <div class="view-toggle" role="group" aria-label="Diagram visualization mode">
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
                  idPrefix="read-layer"
                  value={selectedLayerId}
                  disabled={viewMode === 'tree'}
                  onChange={handleLayerChange}
                />
              </div>
            </header>
            <div class="read-area__canvas">
              {#key `${selectedLayerId}-${viewMode}-${sourceRevision}`}
                {#if viewMode === 'tree'}
                  <HierarchyTreeCanvas
                    {hierarchy}
                    {loadGeneration}
                    onNodeSelect={handleNodeSelect}
                    onReady={handleDiagramReady}
                  />
                {:else}
                  <DiagramCanvas
                    {layer}
                    {loadGeneration}
                    onNodeSelect={handleNodeSelect}
                    onReady={handleDiagramReady}
                  />
                {/if}
              {/key}
            </div>
          </section>
          <DetailPanel {layer} {selectedNode} onClose={() => (selectedNode = null)} />
        </div>
        {#if loading}
          <div class="layer-loader" out:fade={{ duration: 180 }}>
            <PfizerLoader label={loaderLabel} />
          </div>
        {/if}
      </div>
    </main>
  </div>

  <div class="app-panel" role="tabpanel" id="panel-build" aria-labelledby="tab-build" hidden={tab !== 'build'}>
    <BuildRepo
      active={tab === 'build'}
      layerId={selectedLayerId}
      {rawByLayer}
      {hierarchy}
      {sourceRevision}
      onLayerChange={(id) => {
        selectedLayerId = id;
        selectedNode = null;
      }}
    />
  </div>

  <div class="app-panel" role="tabpanel" id="panel-analysis" aria-labelledby="tab-analysis" hidden={tab !== 'analysis'}>
    <CodeAnalysisView {activeSource} />
  </div>
</div>

<style>
  .app-tabs {
    display: flex;
    gap: 4px;
    padding: 0 24px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
  }

  .app-tabs__tab {
    appearance: none;
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    margin-bottom: -1px;
    padding: 10px 14px;
    font-weight: 700;
    color: var(--text-muted);
    cursor: pointer;
  }

  .app-tabs__tab[aria-selected='true'] {
    color: var(--blue-700);
    border-bottom-color: var(--blue-600);
  }

  .app-panels {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }

  .app-panel {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }

  .app-panel[hidden] {
    display: none;
  }

  .app-main {
    flex: 1;
    min-height: 0;
    padding: 16px 24px 20px;
    display: flex;
  }

  .read-area {
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

  .read-area__bar {
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

  .read-area__hint {
    margin: 0;
  }

  .read-area__actions {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-shrink: 0;
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

  .read-area__canvas {
    flex: 1;
    min-height: 0;
    display: flex;
  }

  .read-area__canvas :global(.canvas) {
    border: none;
    border-radius: 0;
    box-shadow: none;
  }

  .layer-stage {
    position: relative;
    flex: 1;
    min-height: 0;
  }

  .layer-view {
    position: absolute;
    inset: 0;
    display: flex;
    gap: 18px;
  }

  .layer-loader {
    position: absolute;
    inset: 0;
    z-index: 6;
    display: flex;
    align-items: center;
    justify-content: center;
    background: color-mix(in srgb, var(--canvas-bg) 86%, white);
    border: 1px solid var(--border);
    border-radius: 14px;
  }

  @media (max-width: 860px) {
    .layer-view {
      flex-direction: column;
      overflow-y: auto;
    }
  }
</style>
