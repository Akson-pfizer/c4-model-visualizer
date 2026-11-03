<script>
  import { kindMeta } from '../c4Kinds.js';

  let {
    legend = [],
    /** @type {Set<string> | null} kinds currently shown — null means all on */
    activeKinds = null,
    interactive = false,
    onToggle
  } = $props();

  function isActive(kind) {
    if (!activeKinds) return true;
    return activeKinds.has(kind);
  }

  function handleToggle(kind) {
    if (!interactive) return;
    onToggle?.(kind);
  }
</script>

<ul class="legend" class:legend--interactive={interactive} aria-label="Diagram key">
  {#each legend as item (item.kind)}
    {@const meta = kindMeta(item.kind)}
    {@const on = isActive(item.kind)}
    <li class="legend__item">
      {#if interactive}
        <label class="legend__toggle" class:legend__toggle--off={!on}>
          <input
            type="checkbox"
            checked={on}
            onchange={() => handleToggle(item.kind)}
          />
          <span
            class="legend__swatch shape-{meta.shape}"
            style:--node-bg={meta.bg}
            style:--node-border={meta.border}
            aria-hidden="true"
          ></span>
          <span class="legend__label">{item.label}</span>
        </label>
      {:else}
        <span
          class="legend__swatch shape-{meta.shape}"
          style:--node-bg={meta.bg}
          style:--node-border={meta.border}
        ></span>
        <span class="legend__label">{item.label}</span>
      {/if}
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

  .legend__toggle {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    cursor: pointer;
    user-select: none;
  }

  .legend__toggle input {
    width: 14px;
    height: 14px;
    margin: 0;
    accent-color: var(--blue-700);
    cursor: pointer;
  }

  .legend__toggle--off {
    opacity: 0.42;
  }

  .legend__toggle--off .legend__swatch {
    filter: grayscale(0.8);
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
    font-weight: 600;
  }

  .legend__toggle:hover .legend__label {
    color: var(--text);
  }
</style>
