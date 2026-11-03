<script>
  import { SvelteFlowProvider } from '@xyflow/svelte';
  import '@xyflow/svelte/dist/style.css';
  import FlowInner from './FlowInner.svelte';
  import FullscreenToggle from './FullscreenToggle.svelte';

  let {
    layer,
    onNodeSelect,
    onNodeDoubleClick,
    onBoundaryClick,
    loadGeneration,
    onReady,
    onHistoryStateChange,
    enableFullscreen = true
  } = $props();

  let shellEl = $state(/** @type {HTMLDivElement | null} */ (null));
  let flowInner = $state(/** @type {any} */ (null));

  /** @returns {boolean} */
  export function undoMove() {
    return Boolean(flowInner?.undoMove?.());
  }

  /** @returns {boolean} */
  export function redoMove() {
    return Boolean(flowInner?.redoMove?.());
  }
</script>

<div class="canvas" bind:this={shellEl} aria-label="C4 diagram canvas">
  <SvelteFlowProvider>
    <FlowInner
      bind:this={flowInner}
      {layer}
      {onNodeSelect}
      {onNodeDoubleClick}
      {onBoundaryClick}
      {loadGeneration}
      {onReady}
      {onHistoryStateChange}
    />
  </SvelteFlowProvider>
  {#if enableFullscreen}
    <div class="canvas__fs">
      <FullscreenToggle target={shellEl} />
    </div>
  {/if}
</div>

<style>
  .canvas {
    position: relative;
    flex: 1;
    min-width: 0;
    height: 100%;
    border: 1px solid var(--border);
    border-radius: 14px;
    overflow: hidden;
    background: var(--canvas-bg);
    box-shadow: var(--shadow-sm);
  }

  .canvas:fullscreen {
    border-radius: 0;
    border: none;
    width: 100vw;
    height: 100vh;
    background: var(--canvas-bg, #f4f7fb);
  }

  .canvas__fs {
    position: absolute;
    right: 12px;
    bottom: 12px;
    z-index: 6;
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
