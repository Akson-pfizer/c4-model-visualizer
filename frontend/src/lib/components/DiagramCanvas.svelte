<script>
  import { SvelteFlowProvider } from '@xyflow/svelte';
  import '@xyflow/svelte/dist/style.css';
  import FlowInner from './FlowInner.svelte';

  let { layer, onNodeSelect } = $props();
</script>

<div class="canvas">
  <SvelteFlowProvider>
    <FlowInner {layer} {onNodeSelect} />
  </SvelteFlowProvider>
</div>

<style>
  .canvas {
    flex: 1;
    min-width: 0;
    height: 100%;
    border: 1px solid var(--border);
    border-radius: 14px;
    overflow: hidden;
    background: var(--canvas-bg);
    box-shadow: var(--shadow-sm);
  }

  :global(.svelte-flow) {
    background: var(--canvas-bg);
  }

  :global(.svelte-flow__controls) {
    box-shadow: var(--shadow-sm);
    border-radius: 10px;
    overflow: hidden;
  }

  :global(.svelte-flow__controls-button) {
    background: var(--surface);
    border-bottom: 1px solid var(--border);
  }

  :global(.svelte-flow__minimap) {
    border-radius: 10px;
    overflow: hidden;
    box-shadow: var(--shadow-sm);
  }
</style>
