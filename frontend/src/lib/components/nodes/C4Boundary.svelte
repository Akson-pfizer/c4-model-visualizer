<script>
  let { data, width, height } = $props();
</script>

<div
  class="c4-boundary layer-{data.upperLayer || 'default'}"
  style:width="{width}px"
  style:height="{height}px"
  role="group"
  aria-label={data.label}
>
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
    border: none;
    border-radius: 16px;
    background: transparent;
    box-sizing: border-box;
    pointer-events: none;
  }

  .c4-boundary.layer-context,
  .c4-boundary.layer-container,
  .c4-boundary.layer-component {
    background: transparent;
  }

  .c4-boundary__header {
    padding: 10px 14px 6px;
    background: transparent;
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
