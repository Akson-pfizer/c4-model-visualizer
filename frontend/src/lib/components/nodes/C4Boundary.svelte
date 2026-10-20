<script>
  let { data, width, height } = $props();

  const LAYER_BADGE = {
    context: 'UPPER · CONTEXT (ZOOMED IN)',
    container: 'UPPER · CONTAINER (ZOOMED IN)',
    component: 'UPPER · COMPONENT (ZOOMED IN)'
  };

  let badgeText = $derived(
    LAYER_BADGE[data.upperLayer] || data.subtitle || 'UPPER LAYER BOUNDARY · ZOOMED IN'
  );

  let isInteractive = $derived(Boolean(data.targetUpperLayer && data.onNavigateUpper));

  function handleUpperClick(event) {
    if (!isInteractive) return;
    event.stopPropagation();
    data.onNavigateUpper();
  }

  function handleKeyDown(event) {
    if (!isInteractive) return;
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      event.stopPropagation();
      data.onNavigateUpper();
    }
  }
</script>

<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
<div
  class="c4-boundary layer-{data.upperLayer || 'default'}"
  class:interactive={isInteractive}
  style:width="{width}px"
  style:height="{height}px"
  role={isInteractive ? 'button' : 'group'}
  tabindex={isInteractive ? 0 : -1}
  aria-label={isInteractive
    ? `Go to upper ${data.targetUpperLayer} layer (${data.label})`
    : data.label}
  title={isInteractive
    ? `Click to go up to the ${data.targetUpperLayer} layer (${data.label})`
    : data.label}
  onclick={handleUpperClick}
  onkeydown={handleKeyDown}
>
  <div class="c4-boundary__pill">
    <span class="c4-boundary__zoom-icon">⤢</span>
    <span class="c4-boundary__badge">{badgeText}</span>
    {#if isInteractive}
      <span class="c4-boundary__up-cta">↑ Click → {data.targetUpperLayer}</span>
    {/if}
  </div>

  <div class="c4-boundary__header">
    <div class="c4-boundary__title-row">
      <span class="c4-boundary__label">{data.label}</span>
      {#if data.subtitle}
        <span class="c4-boundary__subtitle">{data.subtitle}</span>
      {/if}
    </div>
    {#if data.description}
      <p class="c4-boundary__desc">{data.description}</p>
    {/if}
  </div>
</div>

<style>
  .c4-boundary {
    position: relative;
    border: 2px dashed rgba(37, 99, 235, 0.52);
    border-radius: 16px;
    background: rgba(239, 246, 255, 0.12);
    box-shadow: inset 0 0 0 1px rgba(147, 197, 253, 0.22);
    box-sizing: border-box;
    pointer-events: none;
    transition:
      border-color 0.15s ease,
      background-color 0.15s ease,
      box-shadow 0.15s ease;
  }

  .c4-boundary.interactive {
    pointer-events: auto;
    cursor: pointer;
  }

  .c4-boundary.interactive:hover {
    border-color: rgba(29, 78, 216, 0.85);
    background: rgba(219, 234, 254, 0.22);
    box-shadow:
      0 0 0 3px rgba(59, 130, 246, 0.15),
      inset 0 0 0 1px rgba(96, 165, 250, 0.35);
  }

  .c4-boundary.layer-context {
    border-color: rgba(29, 78, 216, 0.55);
    background: rgba(219, 234, 254, 0.11);
  }

  .c4-boundary.layer-container {
    border-color: rgba(37, 99, 235, 0.58);
    background: rgba(224, 242, 254, 0.12);
  }

  .c4-boundary.layer-component {
    border-color: rgba(13, 148, 136, 0.55);
    background: rgba(204, 251, 241, 0.11);
  }

  .c4-boundary.layer-component.interactive:hover {
    border-color: rgba(13, 148, 136, 0.88);
    background: rgba(204, 251, 241, 0.22);
    box-shadow:
      0 0 0 3px rgba(20, 184, 166, 0.16),
      inset 0 0 0 1px rgba(45, 212, 191, 0.35);
  }

  .c4-boundary__pill {
    position: absolute;
    top: -12px;
    left: 16px;
    max-width: calc(100% - 32px);
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 2px 10px;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    color: var(--blue-800, #1e40af);
    background: var(--surface, #ffffff);
    border: 1.5px solid rgba(37, 99, 235, 0.45);
    border-radius: 999px;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
  }

  .c4-boundary.interactive:hover .c4-boundary__pill {
    background: #eff6ff;
    border-color: rgba(29, 78, 216, 0.8);
  }

  .c4-boundary.layer-component .c4-boundary__pill {
    color: #0f766e;
    border-color: rgba(13, 148, 136, 0.45);
  }

  .c4-boundary__up-cta {
    margin-left: 4px;
    padding-left: 6px;
    border-left: 1px solid rgba(37, 99, 235, 0.3);
    font-size: 9px;
    color: var(--blue-700, #1d4ed8);
  }

  .c4-boundary.layer-component .c4-boundary__up-cta {
    border-left-color: rgba(13, 148, 136, 0.3);
    color: #0f766e;
  }

  .c4-boundary__zoom-icon {
    font-size: 11px;
    line-height: 1;
  }

  .c4-boundary__header {
    padding: 14px 18px 8px;
    border-bottom: 1px dashed rgba(148, 163, 184, 0.35);
    background: rgba(255, 255, 255, 0.42);
    border-radius: 14px 14px 0 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .c4-boundary__title-row {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 10px;
    flex-wrap: wrap;
  }

  .c4-boundary__label {
    font-size: 13px;
    font-weight: 700;
    color: var(--text, #0f172a);
    letter-spacing: -0.01em;
  }

  .c4-boundary__subtitle {
    font-size: 10px;
    font-family: var(--mono, monospace);
    color: var(--text-muted, #475569);
    background: rgba(241, 245, 249, 0.85);
    padding: 1px 7px;
    border-radius: 6px;
    border: 1px solid rgba(203, 213, 225, 0.7);
  }

  .c4-boundary__desc {
    margin: 0;
    font-size: 10.5px;
    line-height: 1.3;
    color: var(--text-muted, #475569);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
</style>
