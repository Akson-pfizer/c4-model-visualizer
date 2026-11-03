<script>
  import { Handle, Position } from '@xyflow/svelte';
  import { kindMeta } from '../../c4Kinds.js';

  let { data, selected } = $props();
  let meta = $derived(kindMeta(data.kind));

  /** Short tech chip — keep one readable line on the card. */
  let techLabel = $derived.by(() => {
    const raw = String(data.technology || '').trim();
    if (!raw) return '';
    return raw.length > 36 ? `${raw.slice(0, 34)}…` : raw;
  });

  /** Compact body copy — prefer first sentence / clause. */
  let shortDesc = $derived.by(() => {
    const raw = String(data.description || '').replace(/\s+/g, ' ').trim();
    if (!raw) return '';
    const cut = raw.split(/(?<=[.!?])\s+|;\s+| — | - /)[0] || raw;
    return cut.length > 88 ? `${cut.slice(0, 86)}…` : cut;
  });
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
  title={[data.name, data.technology, data.description].filter(Boolean).join('\n')}
>
  <Handle type="target" position={Position.Left} />
  <Handle type="target" position={Position.Top} id="top" />

  <span class="c4-node__stereotype">«{meta.stereotype}»</span>
  <span class="c4-node__name">{data.name}</span>
  {#if techLabel}
    <span class="c4-node__tech">[{techLabel}]</span>
  {/if}
  {#if shortDesc}
    <p class="c4-node__desc">{shortDesc}</p>
  {/if}
  {#if data.nextLayer}
    <span class="c4-node__drill-hint">↕ {data.nextLayer}</span>
  {/if}

  <Handle type="source" position={Position.Right} />
  <Handle type="source" position={Position.Bottom} id="bottom" />
</div>

<style>
  .c4-node {
    width: 200px;
    height: 118px;
    box-sizing: border-box;
    padding: 7px 10px 6px;
    border-radius: 9px;
    border: 1.5px solid var(--node-border);
    background: var(--node-bg);
    color: var(--node-fg);
    box-shadow: var(--shadow-sm);
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 1px;
    text-align: center;
    cursor: pointer;
    user-select: none;
    overflow: hidden;
  }

  .c4-node:hover {
    box-shadow: var(--shadow-md);
  }

  .c4-node.selected {
    box-shadow:
      0 0 0 2px var(--edge-hot, #0095ff),
      0 0 0 5px color-mix(in srgb, var(--edge-hot, #0095ff) 22%, transparent);
  }

  .c4-node.shape-pill {
    border-radius: 999px;
  }

  .c4-node.shape-rect-dashed {
    border-style: dashed;
  }

  .c4-node.shape-rect-accent {
    border-left-width: 4px;
  }

  .c4-node.shape-rect-code {
    border-radius: 6px;
    font-family: var(--mono);
  }

  .c4-node.shape-rect-db {
    border-radius: 9px 9px 14px 14px;
  }

  .c4-node__stereotype {
    font-size: 8.5px;
    letter-spacing: 0.02em;
    opacity: 0.78;
    line-height: 1.1;
  }

  .c4-node__name {
    font-size: 12px;
    font-weight: 750;
    line-height: 1.15;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .c4-node__tech {
    font-size: 9px;
    font-family: var(--mono);
    opacity: 0.82;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 1.15;
  }

  .c4-node__desc {
    margin: 3px 0 0;
    font-size: 9.5px;
    line-height: 1.2;
    opacity: 0.9;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .c4-node__drill-hint {
    margin-top: 2px;
    font-size: 8.5px;
    font-weight: 750;
    letter-spacing: 0.02em;
    text-transform: capitalize;
    opacity: 0.72;
    line-height: 1.1;
  }
</style>
