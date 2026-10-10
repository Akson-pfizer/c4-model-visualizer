<script>
  import { Handle, Position } from '@xyflow/svelte';
  import { kindMeta } from '../../c4Kinds.js';

  let { data, selected } = $props();
  let meta = $derived(kindMeta(data.kind));
</script>

<div
  class="c4-node shape-{meta.shape}"
  class:selected
  style:--node-bg={meta.bg}
  style:--node-fg={meta.fg}
  style:--node-border={meta.border}
>
  <Handle type="target" position={Position.Left} />
  <Handle type="target" position={Position.Top} id="top" />

  <span class="c4-node__stereotype">«{meta.stereotype}»</span>
  <span class="c4-node__name">{data.name}</span>
  {#if data.technology}
    <span class="c4-node__tech">[{data.technology}]</span>
  {/if}
  <p class="c4-node__desc">{data.description}</p>

  <Handle type="source" position={Position.Right} />
  <Handle type="source" position={Position.Bottom} id="bottom" />
</div>

<style>
  .c4-node {
    width: 220px;
    height: 150px;
    padding: 12px 14px;
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
    transition: box-shadow 0.15s ease, transform 0.15s ease;
  }

  .c4-node:hover {
    box-shadow: var(--shadow-md);
  }

  .c4-node.selected {
    box-shadow: 0 0 0 3px var(--accent-soft), var(--shadow-md);
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
    font-size: 10px;
    letter-spacing: 0.03em;
    opacity: 0.85;
  }

  .c4-node__name {
    font-size: 14px;
    font-weight: 700;
    line-height: 1.25;
  }

  .c4-node__tech {
    font-size: 10.5px;
    font-family: var(--mono);
    opacity: 0.85;
  }

  .c4-node__desc {
    margin-top: 6px;
    font-size: 11px;
    line-height: 1.35;
    opacity: 0.92;
  }
</style>
