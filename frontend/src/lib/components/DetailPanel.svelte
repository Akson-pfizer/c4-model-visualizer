<script>
  import { kindMeta } from '../c4Kinds.js';

  let {
    layer,
    selectedNode,
    onDrillDown,
    onNavigateUpper,
    onClose
  } = $props();

  let collapsed = $state(false);

  let boundaryNodes = $derived(
    (layer?.nodes ?? []).filter((n) => n.type === 'c4Boundary')
  );

  let parentBoundary = $derived.by(() => {
    if (!selectedNode?.parentId) return null;
    return boundaryNodes.find((b) => b.id === selectedNode.parentId) ?? null;
  });

  let collapsedLabel = $derived.by(() => {
    if (selectedNode?.data?.name) return selectedNode.data.name;
    return layer?.subtitle || layer?.title || 'Details';
  });

  function toggleCollapsed() {
    collapsed = !collapsed;
  }
</script>

<aside class="panel" class:panel--collapsed={collapsed} aria-label="Diagram details">
  <div class="panel__chrome">
    {#if !collapsed}
      <div class="panel__header">
        {#if selectedNode}
          {@const meta = kindMeta(selectedNode.data.kind)}
          <span class="panel__eyebrow">«{meta.stereotype}»</span>
        {:else}
          <span class="panel__eyebrow">{layer.title} layer</span>
        {/if}
        <div class="panel__chrome-actions">
          <button
            class="panel__collapse"
            type="button"
            onclick={toggleCollapsed}
            aria-expanded={!collapsed}
            aria-label="Collapse details"
            title="Collapse"
          >
            ›
          </button>
          {#if selectedNode && onClose}
            <button class="panel__close" type="button" onclick={onClose} aria-label="Clear selection"
              >✕</button
            >
          {/if}
        </div>
      </div>
    {:else}
      <button
        type="button"
        class="panel__expand"
        onclick={toggleCollapsed}
        aria-expanded="false"
        aria-label="Expand details"
        title={collapsedLabel}
      >
        <span class="panel__expand-chevron">‹</span>
        <span class="panel__expand-label">{collapsedLabel}</span>
      </button>
    {/if}
  </div>

  {#if !collapsed}
    {#if selectedNode}
      <h2 class="panel__title">{selectedNode.data.name}</h2>
      {#if selectedNode.data.technology}
        <p class="panel__tech">{selectedNode.data.technology}</p>
      {/if}
      <p class="panel__desc">{selectedNode.data.description}</p>

      {#if parentBoundary}
        <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
        <div
          class="panel__upper-box"
          class:clickable={Boolean(parentBoundary.data.targetUpperLayer && onNavigateUpper)}
          role={parentBoundary.data.targetUpperLayer && onNavigateUpper ? 'button' : undefined}
          tabindex={parentBoundary.data.targetUpperLayer && onNavigateUpper ? 0 : -1}
          title={parentBoundary.data.targetUpperLayer
            ? `Click to go up to the ${parentBoundary.data.targetUpperLayer} layer`
            : undefined}
          onclick={() => {
            if (parentBoundary.data.targetUpperLayer && onNavigateUpper) {
              onNavigateUpper(parentBoundary);
            }
          }}
          onkeydown={(e) => {
            if (
              (e.key === 'Enter' || e.key === ' ') &&
              parentBoundary.data.targetUpperLayer &&
              onNavigateUpper
            ) {
              e.preventDefault();
              onNavigateUpper(parentBoundary);
            }
          }}
        >
          <span class="panel__upper-badge">
            ⤢ Zoomed Inside Upper Layer ({parentBoundary.data.upperLayer || 'Parent'})
            {#if parentBoundary.data.targetUpperLayer}
              · ↑ Click to go up
            {/if}
          </span>
          <strong class="panel__upper-title">{parentBoundary.data.label}</strong>
          {#if parentBoundary.data.subtitle}
            <span class="panel__upper-sub">{parentBoundary.data.subtitle}</span>
          {/if}
          {#if parentBoundary.data.description}
            <p class="panel__upper-desc">{parentBoundary.data.description}</p>
          {/if}
        </div>
      {/if}

      {#if selectedNode.data.nextLayer && onDrillDown}
        <button
          type="button"
          class="panel__drill-btn"
          onclick={() => onDrillDown(selectedNode)}
        >
          ⤢ Zoom into {selectedNode.data.nextLayer} layer →
        </button>
      {/if}
    {:else}
      <h2 class="panel__title">{layer.subtitle}</h2>
      <p class="panel__desc">{layer.description}</p>
      {#if layer.note}
        <p class="panel__note">{layer.note}</p>
      {/if}

      {#if boundaryNodes.length > 0}
        <div class="panel__boundaries">
          <span class="panel__boundaries-title">
            ⤢ Zoomed-In Transparent Boundaries ({boundaryNodes.length})
          </span>
          <ul class="panel__boundaries-list">
            {#each boundaryNodes as b (b.id)}
              <li class="panel__boundary-item">
                {#if b.data.targetUpperLayer && onNavigateUpper}
                  <button
                    type="button"
                    class="panel__boundary-btn"
                    title="Click to go up to the {b.data.targetUpperLayer} layer ({b.data.label})"
                    onclick={() => onNavigateUpper(b)}
                  >
                    <span class="panel__boundary-name">
                      {b.data.label}
                      <span class="panel__boundary-up">↑ {b.data.targetUpperLayer}</span>
                    </span>
                    {#if b.data.subtitle}
                      <span class="panel__boundary-meta">{b.data.subtitle}</span>
                    {/if}
                  </button>
                {:else}
                  <span class="panel__boundary-name">{b.data.label}</span>
                  {#if b.data.subtitle}
                    <span class="panel__boundary-meta">{b.data.subtitle}</span>
                  {/if}
                {/if}
              </li>
            {/each}
          </ul>
        </div>
      {/if}

      <p class="panel__hint">
        Select any box on the canvas to see its full description and upper-layer parent here.
      </p>
    {/if}
  {/if}
</aside>

<style>
  .panel {
    width: 290px;
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
    max-height: 100%;
    overflow-y: auto;
    transition: width 0.18s ease;
  }

  .panel--collapsed {
    width: 44px;
    padding: 10px 6px;
    align-items: center;
    overflow: hidden;
  }

  .panel__chrome {
    flex-shrink: 0;
  }

  .panel__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .panel__chrome-actions {
    display: inline-flex;
    align-items: center;
    gap: 2px;
  }

  .panel__eyebrow {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.03em;
    color: var(--accent-strong);
    text-transform: uppercase;
  }

  .panel__collapse,
  .panel__close {
    border: none;
    background: transparent;
    color: var(--text-faint);
    cursor: pointer;
    font-size: 14px;
    line-height: 1;
    padding: 4px 6px;
    border-radius: 6px;
  }

  .panel__collapse:hover,
  .panel__close:hover {
    background: var(--surface-sunken);
    color: var(--text);
  }

  .panel__expand {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    width: 100%;
    border: none;
    background: transparent;
    cursor: pointer;
    padding: 4px 0;
    color: var(--blue-700);
  }

  .panel__expand-chevron {
    font-size: 16px;
    font-weight: 700;
  }

  .panel__expand-label {
    writing-mode: vertical-rl;
    transform: rotate(180deg);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.04em;
    max-height: 220px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .panel__title {
    font-size: 16.5px;
    line-height: 1.25;
  }

  .panel__tech {
    margin: 0;
    font-family: var(--mono);
    font-size: 11.5px;
    color: var(--text-muted);
    overflow-wrap: anywhere;
  }

  .panel__desc {
    font-size: 12.5px;
    color: var(--text-muted);
    line-height: 1.5;
  }

  .panel__note {
    font-size: 12px;
    line-height: 1.45;
    color: var(--accent-strong);
    background: var(--accent-soft);
    border: 1px solid var(--blue-200);
    border-radius: 8px;
    padding: 8px 10px;
  }

  .panel__upper-box {
    margin-top: 6px;
    padding: 10px 12px;
    border-radius: 10px;
    border: 1.5px dashed rgba(37, 99, 235, 0.45);
    background: rgba(239, 246, 255, 0.45);
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  .panel__upper-box.clickable {
    cursor: pointer;
    transition:
      background-color 0.15s ease,
      border-color 0.15s ease;
  }

  .panel__upper-box.clickable:hover {
    background: rgba(219, 234, 254, 0.75);
    border-color: rgba(29, 78, 216, 0.8);
  }

  .panel__upper-badge {
    font-size: 9.5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--blue-700);
  }

  .panel__upper-title {
    font-size: 12.5px;
    color: var(--text);
  }

  .panel__upper-sub {
    font-size: 10.5px;
    font-family: var(--mono);
    color: var(--text-muted);
  }

  .panel__upper-desc {
    margin: 2px 0 0;
    font-size: 11.5px;
    line-height: 1.4;
    color: var(--text-muted);
  }

  .panel__drill-btn {
    margin-top: 6px;
    padding: 8px 12px;
    font-size: 12px;
    font-weight: 700;
    color: #ffffff;
    background: var(--accent-strong);
    border: none;
    border-radius: 8px;
    cursor: pointer;
    text-align: center;
  }

  .panel__drill-btn:hover {
    background: var(--blue-700);
  }

  .panel__boundaries {
    margin-top: 4px;
    padding: 10px 12px;
    border-radius: 10px;
    border: 1px dashed var(--border-strong);
    background: var(--surface-sunken);
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .panel__boundaries-title {
    font-size: 10.5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--blue-700);
  }

  .panel__boundaries-list {
    margin: 0;
    padding: 0;
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .panel__boundary-item {
    display: flex;
    flex-direction: column;
    gap: 1px;
    padding-bottom: 5px;
    border-bottom: 1px solid var(--border);
  }

  .panel__boundary-btn {
    display: flex;
    flex-direction: column;
    gap: 1px;
    width: 100%;
    padding: 4px 6px;
    border: none;
    border-radius: 6px;
    background: transparent;
    text-align: left;
    cursor: pointer;
  }

  .panel__boundary-btn:hover {
    background: rgba(219, 234, 254, 0.6);
  }

  .panel__boundary-up {
    font-size: 9.5px;
    font-weight: 700;
    text-transform: uppercase;
    color: var(--blue-700);
    margin-left: 4px;
  }

  .panel__boundary-item:last-child {
    padding-bottom: 0;
    border-bottom: none;
  }

  .panel__boundary-name {
    font-size: 12px;
    font-weight: 600;
    color: var(--text);
  }

  .panel__boundary-meta {
    font-size: 10.5px;
    font-family: var(--mono);
    color: var(--text-muted);
  }

  .panel__hint {
    font-size: 11.5px;
    color: var(--text-faint);
    margin-top: auto;
    padding-top: 6px;
  }
</style>
