<script>
  import { BaseEdge, EdgeLabel, getSmoothStepPath } from '@xyflow/svelte';

  let {
    id,
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    label,
    data,
    markerEnd
  } = $props();

  let [path, labelX, labelY] = $derived(
    getSmoothStepPath({
      sourceX,
      sourceY,
      targetX,
      targetY,
      sourcePosition,
      targetPosition,
      borderRadius: 8
    })
  );
</script>

<BaseEdge {id} {path} style="stroke: var(--border-strong); stroke-width: 1.5;" {markerEnd} />

{#if label}
  <EdgeLabel x={labelX} y={labelY}>
    <div class="c4-edge-label">
      <span class="c4-edge-label__text">{label}</span>
      {#if data?.technology}
        <span class="c4-edge-label__tech">[{data.technology}]</span>
      {/if}
    </div>
  </EdgeLabel>
{/if}

<style>
  .c4-edge-label {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 10.5px;
    line-height: 1.3;
    color: var(--text);
    box-shadow: var(--shadow-sm);
    text-align: center;
    white-space: nowrap;
  }

  .c4-edge-label__tech {
    display: block;
    font-family: var(--mono);
    font-size: 9.5px;
    color: var(--text-muted);
  }
</style>
