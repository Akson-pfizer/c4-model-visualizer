<script>
  import Legend from './Legend.svelte';

  /** Floating legend body shown above the Controls stack. */
  let {
    legend = [],
    activeKinds = null,
    interactive = false,
    onToggle
  } = $props();
</script>

{#if legend?.length}
  <div class="legend-panel">
    <Legend {legend} {activeKinds} {interactive} {onToggle} />
  </div>
{/if}

<style>
  .legend-panel {
    max-width: min(420px, calc(100vw - 80px));
    /* Clear the vertical Controls stack (+ / − / fit / pan / legend) */
    margin: 0 0 196px 0;
    pointer-events: auto;
  }

  /* The bottom margin makes the hosting Panel span over the Controls and the
     canvas; let clicks and pan drags fall through everywhere but the legend. */
  :global(.svelte-flow__panel:has(> .legend-panel)) {
    pointer-events: none;
  }

  .legend-panel :global(.legend) {
    padding: 8px 10px;
    gap: 8px 12px;
  }
</style>
