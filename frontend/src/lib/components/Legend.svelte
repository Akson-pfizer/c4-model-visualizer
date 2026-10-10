<script>
  import { kindMeta } from '../c4Kinds.js';

  let { legend = [] } = $props();
</script>

<ul class="legend" aria-label="Diagram key">
  {#each legend as item (item.kind)}
    {@const meta = kindMeta(item.kind)}
    <li class="legend__item">
      <span
        class="legend__swatch shape-{meta.shape}"
        style:--node-bg={meta.bg}
        style:--node-border={meta.border}
      ></span>
      <span class="legend__label">{item.label}</span>
    </li>
  {/each}
</ul>

<style>
  .legend {
    list-style: none;
    margin: 0;
    padding: 10px 14px;
    display: flex;
    flex-wrap: wrap;
    gap: 10px 18px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    box-shadow: var(--shadow-sm);
  }

  .legend__item {
    display: flex;
    align-items: center;
    gap: 7px;
  }

  .legend__swatch {
    display: inline-block;
    width: 14px;
    height: 14px;
    border-radius: 4px;
    background: var(--node-bg);
    border: 1.5px solid var(--node-border);
    flex-shrink: 0;
  }

  .legend__swatch.shape-pill {
    border-radius: 999px;
  }

  .legend__swatch.shape-rect-dashed {
    border-style: dashed;
  }

  .legend__label {
    font-size: 12px;
    color: var(--text-muted);
  }
</style>
