<script>
  import ShapeIcon from './ShapeIcon.svelte';

  let {
    shapes = [],
    arrows = [],
    activeArrowId = 'uses',
    collapsed = false,
    onToggleCollapse,
    onDragStart,
    onAdd
  } = $props();
</script>

<aside class="palette" class:collapsed aria-label="Design components">
  <div class="palette__bar">
    {#if !collapsed}
      <span class="palette__title">Components</span>
    {/if}
    <button
      type="button"
      class="palette__toggle"
      aria-expanded={!collapsed}
      aria-controls="palette-body"
      aria-label={collapsed ? 'Expand components panel' : 'Collapse components panel'}
      onclick={onToggleCollapse}
    >
      {collapsed ? '»' : '«'}
    </button>
  </div>

  <div id="palette-body" class="palette__body" hidden={collapsed}>
    <div class="palette__group">
      <h2>Shapes</h2>
      <ul>
        {#each shapes as component (component.id)}
          <li
            class="palette__item"
            draggable="true"
            ondragstart={(event) => onDragStart?.(event, component)}
          >
            <span class="palette__icon" aria-hidden="true">
              <ShapeIcon id={component.id} />
            </span>
            <div class="palette__text">
              <span class="palette__name">{component.name}</span>
              <span class="palette__kind">Drag to work area</span>
            </div>
            <button
              type="button"
              class="palette__add"
              aria-label="Add {component.name} to work area"
              onclick={() => onAdd?.(component)}
            >
              +
            </button>
          </li>
        {/each}
      </ul>
    </div>

    <div class="palette__group">
      <h2>Arrows</h2>
      <ul>
        {#each arrows as component (component.id)}
          <li
            class="palette__item"
            class:active-arrow={activeArrowId === component.id}
            draggable="true"
            ondragstart={(event) => onDragStart?.(event, component)}
          >
            <span class="palette__icon" aria-hidden="true">
              <ShapeIcon id={component.id} />
            </span>
            <div class="palette__text">
              <span class="palette__name">{component.name}</span>
              <span class="palette__kind">Drag or connect</span>
            </div>
            <button
              type="button"
              class="palette__add"
              aria-label="Add {component.name} arrow to work area"
              onclick={() => onAdd?.(component)}
            >
              +
            </button>
          </li>
        {/each}
      </ul>
    </div>
  </div>
</aside>

<style>
  .palette {
    width: 280px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    min-height: 0;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    box-shadow: var(--shadow-sm);
    transition: width 0.16s ease;
  }

  .palette.collapsed {
    width: 52px;
  }

  .palette__bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 10px 10px 14px;
    border-bottom: 1px solid var(--border);
  }

  .palette.collapsed .palette__bar {
    justify-content: center;
    padding: 10px 6px;
    border-bottom: none;
  }

  .palette__title {
    font-size: 13px;
    font-weight: 700;
  }

  .palette__toggle {
    width: 30px;
    height: 30px;
    flex-shrink: 0;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--surface-muted);
    color: var(--blue-700);
    font-weight: 700;
    cursor: pointer;
  }

  .palette__body {
    overflow: auto;
    padding: 12px;
  }

  .palette__body[hidden] {
    display: none;
  }

  .palette__group + .palette__group {
    margin-top: 16px;
    padding-top: 12px;
    border-top: 1px solid var(--border);
  }

  h2 {
    margin: 0 0 8px;
    font-size: 11px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--text-faint);
  }

  .palette ul {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .palette__item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 4px;
    border: 1px solid transparent;
    border-radius: 10px;
    cursor: grab;
  }

  .palette__item:hover {
    background: var(--surface-muted);
    border-color: var(--border);
  }

  .palette__item.active-arrow {
    background: var(--blue-50);
    border-color: var(--blue-200);
  }

  .palette__icon {
    width: 42px;
    height: 42px;
    flex-shrink: 0;
    display: grid;
    place-items: center;
    border: 1px solid var(--border-strong);
    border-radius: 10px;
    background: var(--blue-50);
    color: var(--blue-700);
  }

  .palette__text {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  .palette__name {
    font-size: 13.5px;
    font-weight: 700;
  }

  .palette__kind {
    font-size: 11px;
    color: var(--text-faint);
  }

  .palette__add {
    width: 26px;
    height: 26px;
    flex-shrink: 0;
    border: 1px solid var(--border);
    border-radius: 7px;
    background: var(--surface);
    color: var(--text-muted);
    font-weight: 700;
    cursor: pointer;
  }

  .palette__add:hover {
    border-color: var(--blue-500);
    color: var(--blue-700);
  }

  @media (max-width: 960px) {
    .palette,
    .palette.collapsed {
      width: auto;
    }
  }
</style>
