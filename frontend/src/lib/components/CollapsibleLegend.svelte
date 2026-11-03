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
    /* Clear the vertical Controls stack (+ / − / fit / lock / legend) */
    margin: 0 0 196px 0;
  }

  .legend-panel :global(.legend) {
    padding: 8px 10px;
    gap: 8px 12px;
  }
</style>
