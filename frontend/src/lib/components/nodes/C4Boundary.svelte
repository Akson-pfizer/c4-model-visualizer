<script>
  let { data, width, height } = $props();
</script>

<div class="c4-boundary" style:width="{width}px" style:height="{height}px" aria-hidden="true">
  <span class="c4-boundary__label">{data.label}</span>
</div>

<style>
  .c4-boundary {
    position: relative;
    border: 1.5px dashed var(--border-strong);
    border-radius: 14px;
    background: color-mix(in srgb, var(--surface-muted) 70%, transparent);
    box-sizing: border-box;
  }

  .c4-boundary__label {
    position: absolute;
    top: -11px;
    left: 16px;
    padding: 1px 10px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.02em;
    color: var(--text-muted);
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 999px;
  }
</style>
