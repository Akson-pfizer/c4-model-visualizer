<script>
  import { fade } from 'svelte/transition';
  import AppHeader from './lib/components/AppHeader.svelte';
  import DiagramCanvas from './lib/components/DiagramCanvas.svelte';
  import DetailPanel from './lib/components/DetailPanel.svelte';
  import { getLayer } from './lib/diagramData.js';

  let selectedLayerId = $state('context');
  let selectedNode = $state(null);

  let layer = $derived(getLayer(selectedLayerId));

  function handleLayerChange(id) {
    selectedLayerId = id;
    selectedNode = null;
  }

  function handleNodeSelect(node) {
    selectedNode = node;
  }
</script>

<AppHeader layer={selectedLayerId} onChange={handleLayerChange} />

<main class="app-main">
  <div class="layer-stage">
    {#key selectedLayerId}
      <div class="layer-view" in:fade={{ duration: 260, delay: 120 }} out:fade={{ duration: 160 }}>
        <DiagramCanvas {layer} onNodeSelect={handleNodeSelect} />
        <DetailPanel {layer} {selectedNode} onClose={() => (selectedNode = null)} />
      </div>
    {/key}
  </div>
</main>

<style>
  .app-main {
    flex: 1;
    min-height: 0;
    padding: 20px 24px;
    display: flex;
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

  @media (max-width: 860px) {
    .layer-view {
      flex-direction: column;
      overflow-y: auto;
    }
  }
</style>
