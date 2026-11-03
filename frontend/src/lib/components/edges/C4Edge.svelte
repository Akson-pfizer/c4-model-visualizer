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
    markerStart,
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
  let strokeStyle = $derived(
    data?.style === 'dashed'
      ? 'stroke: var(--border-strong); stroke-width: 1.5; stroke-dasharray: 5 4;'
      : 'stroke: var(--border-strong); stroke-width: 1.5;'
  );
</script>

<BaseEdge {id} {path} style={strokeStyle} {markerStart} {markerEnd} />

{#if label}
  {@const short =
    String(label).length > 42 ? `${String(label).slice(0, 40).trimEnd()}…` : label}
  <EdgeLabel x={labelX} y={labelY}>
    <div class="c4-edge-label" title={label}>
      <span class="c4-edge-label__text">{short}</span>
      {#if data?.technology}
        <span class="c4-edge-label__tech">[{data.technology}]</span>
      {/if}
    </div>
  </EdgeLabel>
{/if}

<style>
  .c4-edge-label {
    max-width: 132px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 5px;
    padding: 1px 6px;
    font-size: 9.5px;
    line-height: 1.2;
    color: var(--text);
    box-shadow: var(--shadow-sm);
    text-align: center;
  }

  .c4-edge-label__text {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    word-break: break-word;
  }

  .c4-edge-label__tech {
    display: block;
    font-family: var(--mono);
    font-size: 8.5px;
    color: var(--text-muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
</style>
