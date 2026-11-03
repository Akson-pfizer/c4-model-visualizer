<script>
  import { onDestroy, onMount } from 'svelte';
  import { fade } from 'svelte/transition';
  import AppHeader from './lib/components/AppHeader.svelte';
  import SourceBar from './lib/components/SourceBar.svelte';
  import LayerSelect from './lib/components/LayerSelect.svelte';
  import DiagramCanvas from './lib/components/DiagramCanvas.svelte';
  import HierarchyTreeCanvas from './lib/components/HierarchyTreeCanvas.svelte';
  import DetailPanel from './lib/components/DetailPanel.svelte';
  import PfizerLoader from './lib/components/PfizerLoader.svelte';
  import KeyboardShortcutsModal from './lib/components/KeyboardShortcutsModal.svelte';
  import CatalogPage from './lib/components/CatalogPage.svelte';
  import BuildRepo from './lib/components/build/BuildRepo.svelte';
  import CodeAnalysisView from './lib/components/analysis/CodeAnalysisView.svelte';
  import ReferenceDocsView from './lib/components/docs/ReferenceDocsView.svelte';
  import { formatFriendlyError } from './lib/analysisCatalog.js';
  import {
    EMPTY_RAW_BY_LAYER,
    LAYER_ORDER,
    buildHierarchyFromLayers,
    getLayer,
    getNextLayerId,
    getPrevLayerId
  } from './lib/diagramData.js';
  import { matchShortcutCommand } from './lib/keyboardShortcuts.js';
  import { fetchProfile, getProfile } from './lib/projectCatalog.js';
  import {
    navigateToView,
    titleForView,
    viewFromPath
  } from './lib/appRoute.js';

  const TABS = [
    { id: 'read', label: 'Visualizer' },
    { id: 'build', label: 'Developer' },
    { id: 'analysis', label: 'Code Analysis' },
    { id: 'docs', label: 'Reference Docs' }
  ];

  const MIN_LOADER_MS = 900;

  let tab = $state('read');
  /** @type {Record<string, HTMLButtonElement | undefined>} */
  let tabButtons = $state({});

  let selectedLayerId = $state('context');
  let viewMode = $state('layer'); // 'layer' | 'tree'
  let selectedNode = $state.raw(null);
  let focusedParentNode = $state(null);
  // Idle until Analyze succeeds — no canvas mount / no fake loader flash.
  let loading = $state(false);
  let loadGeneration = $state(0);
  let loaderStartedAt = Date.now();

  // Undo / Redo navigation stack for Visualizer layer & drill-down transitions
  let navPastStack = $state.raw([]);
  let navFutureStack = $state.raw([]);
  let shortcutsOpen = $state(false);
  /** @type {'catalog' | 'studio'} — Catalog is `/`; Studio is `/studio`. */
  let appView = $state(viewFromPath());
  let profileName = $state(getProfile().display_name);
  let shortcutFeedback = $state(null);
  let buildRepoRef = $state();

  // Repository source & multi-agent model state
  let activeSource = $state('');
  let activeRepoName = $state('No repository loaded');
  let analyzingSource = $state(false);
  let sourceError = $state(null);
  let agentReports = $state.raw([]);
  // $state.raw: diagram payloads are large; deep proxies make SvelteFlow lag.
  let rawByLayer = $state.raw(EMPTY_RAW_BY_LAYER);
  let customHierarchy = $state.raw(null);
  let sourceRevision = $state(0);
  /** @type {AbortController | null} */
  let analyzeAbort = null;
  let analyzeJobId = $state(/** @type {string | null} */ (null));

  let hasAnalyzed = $derived(Boolean(activeSource.trim()));
  let layer = $derived(
    getLayer(selectedLayerId, rawByLayer, focusedParentNode?.id ?? null)
  );
  // Only build the cross-layer tree when Tree view or Developer tab needs it.
  let hierarchy = $derived.by(() => {
    if (!hasAnalyzed) return [];
    if (customHierarchy) return customHierarchy;
    if (viewMode !== 'tree' && tab !== 'build') return [];
    return buildHierarchyFromLayers(rawByLayer);
  });

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
  /** @type {ReturnType<typeof setTimeout> | undefined} */
  let feedbackTimer;

  function showShortcutBadge(message) {
    if (!message) return;
    shortcutFeedback = message;
    clearTimeout(feedbackTimer);
    feedbackTimer = setTimeout(() => {
      shortcutFeedback = null;
    }, 1800);
  }

  function pushNavHistory() {
    const snap = {
      selectedLayerId,
      viewMode,
      focusedParentNode: focusedParentNode ? { ...focusedParentNode } : null
    };
    navPastStack = [...navPastStack.slice(-29), snap];
    navFutureStack = [];
  }

  function undoNavigation() {
    if (navPastStack.length === 0) return false;
    const current = {
      selectedLayerId,
      viewMode,
      focusedParentNode: focusedParentNode ? { ...focusedParentNode } : null
    };
    const prev = navPastStack[navPastStack.length - 1];
    navPastStack = navPastStack.slice(0, -1);
    navFutureStack = [...navFutureStack, current];

    triggerLoader();
    selectedLayerId = prev.selectedLayerId;
    viewMode = prev.viewMode;
    focusedParentNode = prev.focusedParentNode;
    selectedNode = null;
    return true;
  }

  function redoNavigation() {
    if (navFutureStack.length === 0) return false;
    const current = {
      selectedLayerId,
      viewMode,
      focusedParentNode: focusedParentNode ? { ...focusedParentNode } : null
    };
    const next = navFutureStack[navFutureStack.length - 1];
    navFutureStack = navFutureStack.slice(0, -1);
    navPastStack = [...navPastStack, current];

    triggerLoader();
    selectedLayerId = next.selectedLayerId;
    viewMode = next.viewMode;
    focusedParentNode = next.focusedParentNode;
    selectedNode = null;
    return true;
  }

  function triggerLoader() {
    clearTimeout(hideTimer);
    loadGeneration += 1;
    loaderStartedAt = Date.now();
    loading = true;
  }

  function handleLayerChange(id) {
    if (id === selectedLayerId && viewMode === 'layer' && !focusedParentNode) return;
    pushNavHistory();
    triggerLoader();
    viewMode = 'layer';
    selectedLayerId = id;
    focusedParentNode = null;
    selectedNode = null;
  }

  function handleViewModeChange(mode) {
    if (mode === viewMode) return;
    pushNavHistory();
    triggerLoader();
    viewMode = mode;
    selectedNode = null;
  }

  function handleNodeDoubleClick(node) {
    if (!node) return;
    const sourceLayer = node.data?.layer || selectedLayerId;
    const nextLayerId = getNextLayerId(sourceLayer);
    if (!nextLayerId) return;

    pushNavHistory();
    triggerLoader();
    viewMode = 'layer';
    selectedLayerId = nextLayerId;
    focusedParentNode = {
      id: node.data?.rawId || node.id,
      name: node.data?.name || node.id,
      layer: sourceLayer
    };
    selectedNode = null;
  }

  function clearFocusedDrillDown() {
    if (!focusedParentNode) return;
    pushNavHistory();
    triggerLoader();
    focusedParentNode = null;
    selectedNode = null;
  }

  function handleBoundaryClick(boundaryNode) {
    if (!boundaryNode) return;
    const targetUpperLayer =
      boundaryNode.data?.targetUpperLayer || getPrevLayerId(selectedLayerId);
    if (!targetUpperLayer || targetUpperLayer === selectedLayerId) return;

    const sourceNodeId = boundaryNode.data?.sourceNodeId ?? null;
    const upperLayerData = getLayer(targetUpperLayer, rawByLayer, null);
    const matchingUpperNode = sourceNodeId
      ? upperLayerData.elementNodes.find((n) => n.id === sourceNodeId)
      : null;

    pushNavHistory();
    triggerLoader();
    viewMode = 'layer';
    selectedLayerId = targetUpperLayer;
    focusedParentNode = null;
    selectedNode = matchingUpperNode ?? null;
  }

  function copySelectedNodeSummary() {
    if (!selectedNode) return false;
    const summary = {
      id: selectedNode.id,
      layer: selectedLayerId,
      name: selectedNode.data?.name,
      kind: selectedNode.data?.kind,
      technology: selectedNode.data?.technology,
      description: selectedNode.data?.description
    };
    try {
      navigator.clipboard?.writeText(JSON.stringify(summary, null, 2));
    } catch {
      // Clipboard API fallback
    }
    return true;
  }

  function handleGlobalKeydown(event) {
    const cmd = matchShortcutCommand(event);
    if (!cmd) return;

    if (cmd === 'toggle-help') {
      event.preventDefault();
      shortcutsOpen = !shortcutsOpen;
      return;
    }

    if (shortcutsOpen) {
      if (cmd === 'escape') {
        shortcutsOpen = false;
      }
      return;
    }

    // Canvas / layer shortcuts stay locked until Analyze completes.
    if (!hasAnalyzed && (tab === 'read' || tab === 'build')) {
      return;
    }

    // Layer number keys 1..4 work in Visualizer & Developer tabs
    if (cmd.startsWith('layer-') && ['1', '2', '3', '4'].includes(cmd.slice(-1))) {
      const idx = Number(cmd.slice(-1)) - 1;
      const targetLayer = LAYER_ORDER[idx];
      if (targetLayer && (tab === 'read' || tab === 'build')) {
        event.preventDefault();
        handleLayerChange(targetLayer);
        showShortcutBadge(`Switched to ${targetLayer} layer`);
      }
      return;
    }

    if (cmd === 'layer-up' && (tab === 'read' || tab === 'build')) {
      const prevLayer = getPrevLayerId(selectedLayerId);
      if (prevLayer) {
        event.preventDefault();
        handleLayerChange(prevLayer);
        showShortcutBadge(`Up to ${prevLayer} layer`);
      }
      return;
    }

    if (cmd === 'layer-down' && (tab === 'read' || tab === 'build')) {
      const nextLayer = getNextLayerId(selectedLayerId);
      if (nextLayer) {
        event.preventDefault();
        handleLayerChange(nextLayer);
        showShortcutBadge(`Down to ${nextLayer} layer`);
      }
      return;
    }

    if (tab === 'build') {
      const handledMsg = buildRepoRef?.handleShortcutCommand?.(cmd);
      if (handledMsg) {
        event.preventDefault();
        showShortcutBadge(handledMsg);
      }
      return;
    }

    if (tab === 'read') {
      if (cmd === 'undo') {
        if (undoNavigation()) {
          event.preventDefault();
          showShortcutBadge('Undid layer navigation (⌘Z / Ctrl+Z)');
        }
      } else if (cmd === 'redo') {
        if (redoNavigation()) {
          event.preventDefault();
          showShortcutBadge('Redid layer navigation (⌘Y / Ctrl+Y)');
        }
      } else if (cmd === 'copy') {
        if (copySelectedNodeSummary()) {
          event.preventDefault();
          showShortcutBadge(`Copied "${selectedNode.data?.name}" details (⌘C / Ctrl+C)`);
        }
      } else if (cmd === 'drill-down' && selectedNode) {
        event.preventDefault();
        handleNodeDoubleClick(selectedNode);
        showShortcutBadge(`Zoomed into ${selectedNode.data?.name}`);
      } else if (cmd === 'toggle-tree') {
        event.preventDefault();
        handleViewModeChange(viewMode === 'tree' ? 'layer' : 'tree');
        showShortcutBadge(`Switched to ${viewMode === 'tree' ? 'Tree' : 'Layer'} view`);
      } else if (cmd === 'escape') {
        if (selectedNode) {
          event.preventDefault();
          selectedNode = null;
          showShortcutBadge('Cleared selection (Esc)');
        } else if (focusedParentNode) {
          event.preventDefault();
          clearFocusedDrillDown();
          showShortcutBadge('Reset zoomed-in focus (Esc)');
        }
      }
    }
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
    if (!node) {
      selectedNode = null;
      return;
    }
    // Detach from SvelteFlow's reactive node graph so the detail panel
    // doesn't subscribe to per-frame position updates while dragging.
    const data = {};
    for (const [k, v] of Object.entries(node.data ?? {})) {
      if (typeof v !== 'function') data[k] = v;
    }
    selectedNode = {
      id: node.id,
      type: node.type,
      parentId: node.parentId,
      data
    };
  }

  async function analyzeRepositorySource(
    sourceInput,
    selectedType = 'local',
    llmOptions = { use_llm: false, model: null }
  ) {
    if (analyzeAbort) {
      analyzeAbort.abort();
    }
    const controller = new AbortController();
    analyzeAbort = controller;
    const jobId =
      typeof crypto !== 'undefined' && crypto.randomUUID
        ? crypto.randomUUID()
        : `job-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
    analyzeJobId = jobId;
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
          use_llm: Boolean(llmOptions?.use_llm),
          model: llmOptions?.model || null,
          job_id: jobId
        }),
        signal: controller.signal
      });

      if (!response.ok) {
        const errBody = await response.json().catch(() => ({}));
        throw new Error(errBody.detail || `Backend returned status ${response.status}`);
      }

      const payload = await response.json();
      if (controller.signal.aborted) return;
      applyAnalyzedModel(payload);
      // Full payload is persisted by the backend into the Architect Catalog DB.
    } catch (err) {
      if (controller.signal.aborted || (err instanceof Error && err.name === 'AbortError')) {
        sourceError = 'Repository Analysis stopped.';
      } else {
        sourceError = formatFriendlyError(err, 'Repository Analysis');
      }
      loading = false;
    } finally {
      if (analyzeAbort === controller) {
        analyzeAbort = null;
      }
      if (analyzeJobId === jobId) {
        analyzeJobId = null;
      }
      analyzingSource = false;
    }
  }

  async function stopAnalysis() {
    const jobId = analyzeJobId;
    if (analyzeAbort) {
      analyzeAbort.abort();
    }
    analyzingSource = false;
    loading = false;
    sourceError = 'Repository Analysis stopped.';
    if (jobId) {
      try {
        await fetch('/api/c4/cancel', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ job_id: jobId })
        });
      } catch {
        // UI already stopped; backend cancel is best-effort.
      }
    }
  }

  function applyAnalyzedModel(payload) {
    rawByLayer = payload.layers;
    customHierarchy = payload.hierarchy;
    agentReports = payload.agents ?? [];
    activeSource = payload.source;
    activeRepoName = `${payload.repo_name} (${payload.source_type})`;
    sourceRevision += 1;
    focusedParentNode = null;
    selectedNode = null;
    navPastStack = [];
    navFutureStack = [];
    viewMode = 'layer';
    selectedLayerId = 'context';
    tab = 'read';
    triggerLoader();
  }

  function openCachedCatalogProject(result) {
    const payload = result?.model;
    if (!payload?.layers) {
      sourceError = 'Cached catalog entry is missing diagram data.';
      return;
    }
    sourceError = null;
    applyAnalyzedModel(payload);
    setAppView('studio');
    showShortcutBadge(`Opened ${payload.repo_name} from catalog`);
  }

  function resetToEmptyWorkspace() {
    if (analyzingSource) {
      stopAnalysis();
    }
    sourceError = null;
    loading = false;
    rawByLayer = EMPTY_RAW_BY_LAYER;
    customHierarchy = null;
    agentReports = [];
    activeSource = '';
    activeRepoName = 'No repository loaded';
    sourceRevision += 1;
    focusedParentNode = null;
    selectedNode = null;
    navPastStack = [];
    navFutureStack = [];
    viewMode = 'layer';
    selectedLayerId = 'context';
  }

  function setAppView(view, { replace = false } = {}) {
    if (appView !== view) appView = view;
    navigateToView(view, { replace });
    document.title = titleForView(view);
  }

  function openCatalogPage() {
    setAppView('catalog');
    fetchProfile().then((p) => {
      profileName = p.display_name;
    });
  }

  function openStudio() {
    setAppView('studio');
  }

  function handlePopState() {
    const next = viewFromPath();
    appView = next;
    document.title = titleForView(next);
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

  onMount(() => {
    // Normalize unknown paths (e.g. /catalog) onto the canonical slug.
    setAppView(viewFromPath(), { replace: true });
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  });

  onDestroy(() => {
    clearTimeout(hideTimer);
    clearTimeout(feedbackTimer);
    if (analyzeAbort) {
      analyzeAbort.abort();
    }
  });
</script>

<svelte:window onkeydown={handleGlobalKeydown} />

<AppHeader
  {profileName}
  appView={appView}
  onOpenShortcuts={() => (shortcutsOpen = true)}
  onOpenCatalog={openCatalogPage}
  onOpenStudio={openStudio}
/>

{#if appView === 'catalog'}
  <CatalogPage
    onOpenProject={openCachedCatalogProject}
    onProfileChange={(name) => (profileName = name)}
  />
{:else}
  <SourceBar
    source={activeSource}
    analyzing={analyzingSource}
    error={sourceError}
    {activeRepoName}
    agents={agentReports}
    onAnalyze={analyzeRepositorySource}
    onStop={stopAnalysis}
    onResetDemo={resetToEmptyWorkspace}
  />

  <div class="app-tabs-bar">
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

    {#if shortcutFeedback}
      <output class="shortcut-toast" aria-live="polite">
        ⌨ {shortcutFeedback}
      </output>
    {/if}
  </div>

  <div class="app-panels">
    <div class="app-panel" role="tabpanel" id="panel-read" aria-labelledby="tab-read" hidden={tab !== 'read'}>
      {#if tab === 'read'}
        <main class="app-main" aria-busy={loading}>
          <div class="layer-stage">
            <div class="layer-view">
              <section
                class="read-area"
                class:read-area--inactive={!hasAnalyzed}
                aria-label="Interactive diagram area"
              >
              <header class="read-area__bar">
                <p class="read-area__hint">
                  {#if !hasAnalyzed}
                    <strong>Visualizer idle</strong> · Analyze a repository to unlock the C4 canvas
                  {:else if viewMode === 'tree'}
                    <strong>Hierarchy Tree View</strong> · Context → Container → Component → Code Class Modules
                  {:else if focusedParentNode && layer.focusParentId}
                    <strong>{layer.title} layer</strong> · Zoomed into <strong>{focusedParentNode.name}</strong> ({focusedParentNode.layer})
                  {:else}
                    <strong>{layer.title} layer</strong> · {layer.subtitle}
                  {/if}
                </p>
                <div class="read-area__actions">
                  <div class="nav-history-strip" role="group" aria-label="Layer navigation undo and redo">
                    <button
                      type="button"
                      class="nav-history-btn"
                      disabled={!hasAnalyzed || navPastStack.length === 0}
                      title="Undo layer navigation (⌘Z / Ctrl+Z)"
                      onclick={() => {
                        if (undoNavigation()) showShortcutBadge('Undid layer navigation');
                      }}
                    >
                      ↶ Undo
                    </button>
                    <button
                      type="button"
                      class="nav-history-btn"
                      disabled={!hasAnalyzed || navFutureStack.length === 0}
                      title="Redo layer navigation (⌘Y / Ctrl+Y)"
                      onclick={() => {
                        if (redoNavigation()) showShortcutBadge('Redid layer navigation');
                      }}
                    >
                      ↷ Redo
                    </button>
                  </div>
                  {#if hasAnalyzed && focusedParentNode && layer.focusParentId && viewMode === 'layer'}
                    <button
                      type="button"
                      class="focus-reset-btn"
                      onclick={clearFocusedDrillDown}
                      title="Show all elements in the {layer.title} layer (Esc)"
                    >
                      ✕ Show All {layer.title}s
                    </button>
                  {/if}
                  <div class="view-toggle" role="group" aria-label="Diagram visualization mode">
                    <button
                      type="button"
                      class="view-toggle__btn"
                      class:active={viewMode === 'layer'}
                      aria-pressed={viewMode === 'layer'}
                      disabled={!hasAnalyzed}
                      onclick={() => handleViewModeChange('layer')}
                    >
                      Layer
                    </button>
                    <button
                      type="button"
                      class="view-toggle__btn"
                      class:active={viewMode === 'tree'}
                      aria-pressed={viewMode === 'tree'}
                      disabled={!hasAnalyzed}
                      onclick={() => handleViewModeChange('tree')}
                    >
                      Tree
                    </button>
                  </div>
                  <LayerSelect
                    idPrefix="read-layer"
                    value={selectedLayerId}
                    disabled={!hasAnalyzed || viewMode === 'tree'}
                    onChange={handleLayerChange}
                  />
                </div>
              </header>
              <div class="read-area__canvas">
                {#if hasAnalyzed}
                  {#key `${selectedLayerId}-${viewMode}-${sourceRevision}-${focusedParentNode?.id ?? 'all'}`}
                    {#if viewMode === 'tree'}
                      <HierarchyTreeCanvas
                        {hierarchy}
                        {loadGeneration}
                        onNodeSelect={handleNodeSelect}
                        onNodeDoubleClick={handleNodeDoubleClick}
                        onReady={handleDiagramReady}
                      />
                    {:else}
                      <DiagramCanvas
                        {layer}
                        {loadGeneration}
                        onNodeSelect={handleNodeSelect}
                        onNodeDoubleClick={handleNodeDoubleClick}
                        onBoundaryClick={handleBoundaryClick}
                        onReady={handleDiagramReady}
                      />
                    {/if}
                  {/key}
                {:else}
                  <div class="canvas-idle" role="status">
                    <p class="canvas-idle__eyebrow">C4 canvas locked</p>
                    <h2 class="canvas-idle__title">Analyze a repository first</h2>
                    <p class="canvas-idle__body">
                      Enter a local path or GitHub URL above, then press Analyze.
                      The Visualizer stays inactive until the multi-agent run finishes.
                    </p>
                  </div>
                {/if}
              </div>
            </section>
            <DetailPanel
              {layer}
              selectedNode={hasAnalyzed ? selectedNode : null}
              {activeSource}
              onDrillDown={handleNodeDoubleClick}
              onNavigateUpper={handleBoundaryClick}
              onClose={() => (selectedNode = null)}
            />
          </div>
          {#if loading || analyzingSource}
            <div class="layer-loader" out:fade={{ duration: 180 }}>
              <PfizerLoader label={loaderLabel} />
            </div>
          {/if}
        </div>
      </main>
    {/if}
  </div>

  <div class="app-panel" role="tabpanel" id="panel-build" aria-labelledby="tab-build" hidden={tab !== 'build'}>
    {#if tab === 'build'}
      <BuildRepo
        bind:this={buildRepoRef}
        active={hasAnalyzed}
        layerId={selectedLayerId}
        {rawByLayer}
        {hierarchy}
        {sourceRevision}
        onLayerChange={(id) => {
          selectedLayerId = id;
          selectedNode = null;
        }}
      />
    {/if}
  </div>

  <div class="app-panel" role="tabpanel" id="panel-analysis" aria-labelledby="tab-analysis" hidden={tab !== 'analysis'}>
    {#if tab === 'analysis'}
      <CodeAnalysisView {activeSource} />
    {/if}
  </div>

  <div class="app-panel" role="tabpanel" id="panel-docs" aria-labelledby="tab-docs" hidden={tab !== 'docs'}>
    {#if tab === 'docs'}
      <ReferenceDocsView {activeSource} />
    {/if}
  </div>
</div>
{/if}

<KeyboardShortcutsModal open={shortcutsOpen} onClose={() => (shortcutsOpen = false)} />

<style>
  .app-tabs-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 24px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
  }

  .app-tabs {
    display: flex;
    gap: 4px;
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

  .shortcut-toast {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 10px;
    border-radius: 999px;
    background: var(--blue-50);
    border: 1px solid var(--blue-200);
    color: var(--blue-700);
    font-size: 11.5px;
    font-weight: 700;
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

  .nav-history-strip {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    padding: 2px;
    border-radius: 8px;
    background: var(--surface-muted);
    border: 1px solid var(--border);
  }

  .nav-history-btn {
    padding: 4px 8px;
    border: none;
    border-radius: 6px;
    background: transparent;
    color: var(--text-muted);
    font-size: 11.5px;
    font-weight: 700;
    cursor: pointer;
  }

  .nav-history-btn:hover:not(:disabled) {
    background: var(--surface);
    color: var(--blue-700);
  }

  .nav-history-btn:disabled {
    opacity: 0.42;
    cursor: not-allowed;
  }

  .focus-reset-btn {
    padding: 5px 10px;
    font-size: 11.5px;
    font-weight: 700;
    color: var(--blue-700);
    background: var(--accent-soft);
    border: 1px solid var(--blue-200);
    border-radius: 8px;
    cursor: pointer;
  }

  .focus-reset-btn:hover {
    background: var(--blue-200);
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

  .read-area--inactive {
    background: color-mix(in srgb, var(--canvas-bg) 70%, #dbe4f0);
  }

  .read-area__canvas :global(.canvas) {
    border: none;
    border-radius: 0;
    box-shadow: none;
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

  .view-toggle__btn:disabled {
    opacity: 0.45;
    cursor: not-allowed;
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
