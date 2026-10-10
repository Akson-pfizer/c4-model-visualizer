<script>
  import { kindMeta } from '../c4Kinds.js';

  let { layer, selectedNode, onClose } = $props();
</script>

<aside class="panel" aria-label="Diagram details">
  {#if selectedNode}
    {@const meta = kindMeta(selectedNode.data.kind)}
    <div class="panel__header">
      <span class="panel__eyebrow">«{meta.stereotype}»</span>
      <button class="panel__close" type="button" onclick={onClose} aria-label="Clear selection">✕</button>
    </div>
    <h2 class="panel__title">{selectedNode.data.name}</h2>
    {#if selectedNode.data.technology}
      <p class="panel__tech">{selectedNode.data.technology}</p>
    {/if}
    <p class="panel__desc">{selectedNode.data.description}</p>
  {:else}
    <div class="panel__header">
      <span class="panel__eyebrow">{layer.title} layer</span>
    </div>
    <h2 class="panel__title">{layer.subtitle}</h2>
    <p class="panel__desc">{layer.description}</p>
    {#if layer.note}
      <p class="panel__note">{layer.note}</p>
    {/if}
    <p class="panel__hint">Select any box on the canvas to see its full description here.</p>
  {/if}
</aside>

<style>
  .panel {
    width: 280px;
    flex-shrink: 0;
    padding: 18px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    box-shadow: var(--shadow-sm);
    display: flex;
    flex-direction: column;
    gap: 8px;
    height: fit-content;
  }

  .panel__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .panel__eyebrow {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.03em;
    color: var(--accent-strong);
    text-transform: uppercase;
  }

  .panel__close {
    border: none;
    background: transparent;
    color: var(--text-faint);
    cursor: pointer;
    font-size: 13px;
    line-height: 1;
    padding: 4px;
    border-radius: 6px;
  }

  .panel__close:hover {
    background: var(--surface-sunken);
    color: var(--text);
  }

  .panel__title {
    font-size: 17px;
  }

  .panel__tech {
    margin: 0;
    font-family: var(--mono);
    font-size: 12px;
    color: var(--text-muted);
  }

  .panel__desc {
    font-size: 13px;
    color: var(--text-muted);
    line-height: 1.5;
  }

  .panel__note {
    font-size: 12.5px;
    line-height: 1.5;
    color: var(--accent-strong);
    background: var(--accent-soft);
    border: 1px solid var(--blue-200);
    border-radius: 8px;
    padding: 8px 10px;
  }

  .panel__hint {
    font-size: 11.5px;
    color: var(--text-faint);
    margin-top: auto;
    padding-top: 6px;
  }
</style>
