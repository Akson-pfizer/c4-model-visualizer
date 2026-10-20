<script>
  import { Handle, Position } from '@xyflow/svelte';
  import { kindMeta } from '../../c4Kinds.js';

  let { data, selected } = $props();
  let meta = $derived(kindMeta(data.kind));
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
  class="c4-node shape-{meta.shape}"
  class:selected
  class:drillable={Boolean(data.nextLayer)}
  style:--node-bg={meta.bg}
  style:--node-fg={meta.fg}
  style:--node-border={meta.border}
  ondblclick={(event) => {
    if (data.onDrillDown) {
      event.stopPropagation();
      data.onDrillDown();
    }
  }}
  title={data.nextLayer
    ? `Double-click to zoom into the ${data.nextLayer} layer for "${data.name}"`
    : data.name}
>
  <Handle type="target" position={Position.Left} />
  <Handle type="target" position={Position.Top} id="top" />

  <span class="c4-node__stereotype">«{meta.stereotype}»</span>
  <span class="c4-node__name">{data.name}</span>
  {#if data.technology}
    <span class="c4-node__tech">[{data.technology}]</span>
  {/if}
  <p class="c4-node__desc">{data.description}</p>
  {#if data.nextLayer}
    <span class="c4-node__drill-hint">⤢ Double-click → {data.nextLayer}</span>
  {/if}

  <Handle type="source" position={Position.Right} />
  <Handle type="source" position={Position.Bottom} id="bottom" />
</div>

<style>
  .c4-node {
    width: 220px;
    height: 150px;
    padding: 10px 12px;
    border-radius: 10px;
    border: 1.5px solid var(--node-border);
    background: var(--node-bg);
    color: var(--node-fg);
    box-shadow: var(--shadow-sm);
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 2px;
    text-align: center;
    cursor: pointer;
    user-select: none;
    transition:
      box-shadow 0.15s ease,
      transform 0.15s ease;
  }

  .c4-node:hover {
    box-shadow: var(--shadow-md);
  }

  .c4-node.selected {
    box-shadow:
      0 0 0 3px var(--accent-soft),
      var(--shadow-md);
    transform: translateY(-1px);
  }

  .c4-node.shape-pill {
    border-radius: 999px;
  }

  .c4-node.shape-rect-dashed {
    border-style: dashed;
  }

  .c4-node.shape-rect-accent {
    border-left-width: 5px;
  }

  .c4-node.shape-rect-code {
    border-radius: 6px;
    font-family: var(--mono);
  }

  .c4-node.shape-rect-db {
    border-radius: 10px 10px 16px 16px;
  }

  .c4-node__stereotype {
    font-size: 9.5px;
    letter-spacing: 0.03em;
    opacity: 0.85;
  }

  .c4-node__name {
    font-size: 13.5px;
    font-weight: 700;
    line-height: 1.22;
  }

  .c4-node__tech {
    font-size: 10px;
    font-family: var(--mono);
    opacity: 0.85;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .c4-node__desc {
    margin-top: 4px;
    font-size: 10.5px;
    line-height: 1.3;
    opacity: 0.92;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .c4-node__drill-hint {
    margin-top: 3px;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.03em;
    text-transform: uppercase;
    opacity: 0.78;
  }
</style>
