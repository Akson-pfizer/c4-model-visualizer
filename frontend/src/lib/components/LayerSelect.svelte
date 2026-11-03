<script>
  import { LAYERS } from '../diagramData.js';

  let { value, onChange, idPrefix = 'layer', disabled = false } = $props();

  let open = $state(false);
  let activeIndex = $state(0);
  let buttonEl = $state();
  let listEl = $state();

  let current = $derived(LAYERS.find((l) => l.id === value) ?? LAYERS[0]);

  $effect(() => {
    if (disabled && open) {
      open = false;
    }
  });

  function openList() {
    if (disabled) return;
    activeIndex = LAYERS.findIndex((l) => l.id === value);
    if (activeIndex < 0) activeIndex = 0;
    open = true;
  }

  function closeList({ focusButton = true } = {}) {
    open = false;
    if (focusButton) buttonEl?.focus();
  }

  function selectLayer(layer) {
    if (disabled) return;
    onChange(layer.id);
    closeList();
  }

  function onButtonClick() {
    if (disabled) return;
    if (open) {
      closeList();
    } else {
      openList();
    }
  }

  function onButtonKeydown(event) {
    if (disabled) return;
    if (['ArrowDown', 'ArrowUp', 'Enter', ' '].includes(event.key) && !open) {
      event.preventDefault();
      openList();
      return;
    }
    if (!open) return;

    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault();
        activeIndex = (activeIndex + 1) % LAYERS.length;
        break;
      case 'ArrowUp':
        event.preventDefault();
        activeIndex = (activeIndex - 1 + LAYERS.length) % LAYERS.length;
        break;
      case 'Home':
        event.preventDefault();
        activeIndex = 0;
        break;
      case 'End':
        event.preventDefault();
        activeIndex = LAYERS.length - 1;
        break;
      case 'Enter':
      case ' ':
        event.preventDefault();
        selectLayer(LAYERS[activeIndex]);
        break;
      case 'Escape':
        event.preventDefault();
        closeList();
        break;
    }
  }

  function handleWindowClick(event) {
    if (!open) return;
    if (buttonEl?.contains(event.target) || listEl?.contains(event.target)) return;
    closeList({ focusButton: false });
  }
</script>

<svelte:window onclick={handleWindowClick} />

<div class="layer-select">
  <button
    type="button"
    bind:this={buttonEl}
    class="layer-select__button"
    role="combobox"
    aria-haspopup="listbox"
    aria-expanded={open}
    aria-disabled={disabled}
    {disabled}
    title={disabled ? 'Layer selection is disabled in Tree view' : undefined}
    aria-controls="{idPrefix}-listbox"
    aria-activedescendant={open ? `${idPrefix}-option-${LAYERS[activeIndex].id}` : undefined}
    onclick={onButtonClick}
    onkeydown={onButtonKeydown}
  >
    <span class="layer-select__eyebrow">C4 Layer</span>
    <span class="layer-select__value">{current.label}</span>
    <svg class="layer-select__chevron" class:flipped={open} viewBox="0 0 12 8" aria-hidden="true">
      <path d="M1 1.5L6 6.5L11 1.5" stroke="currentColor" stroke-width="1.6" fill="none" stroke-linecap="round" stroke-linejoin="round" />
    </svg>
  </button>

  {#if open}
    <ul
      id="{idPrefix}-listbox"
      role="listbox"
      bind:this={listEl}
      class="layer-select__list"
    >
      {#each LAYERS as layer, i (layer.id)}
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <!-- aria-activedescendant pattern: options are never individually focused,
             all keyboard handling lives on the combobox button above -->
        <li
          id={`${idPrefix}-option-${layer.id}`}
          role="option"
          aria-selected={layer.id === value}
          class="layer-select__option"
          class:active={i === activeIndex}
          class:current={layer.id === value}
          onmouseenter={() => (activeIndex = i)}
          onclick={() => selectLayer(layer)}
        >
          <span class="layer-select__option-label">{layer.label}</span>
          <span class="layer-select__option-hint">{layer.description}</span>
        </li>
      {/each}
    </ul>
  {/if}
</div>

<style>
  .layer-select {
    position: relative;
  }

  .layer-select__button {
    display: inline-flex;
    flex-direction: row;
    align-items: center;
    gap: 6px;
    min-width: 0;
    padding: 3px 28px 3px 10px;
    background: var(--surface);
    border: 1px solid var(--border-strong);
    border-radius: 8px;
    box-shadow: none;
    cursor: pointer;
    position: relative;
    transition: border-color 0.15s ease, background 0.15s ease;
  }

  .layer-select__button:hover:not(:disabled) {
    border-color: var(--blue-500, var(--accent));
    background: var(--blue-50, var(--accent-soft));
  }

  .layer-select__button:disabled {
    opacity: 0.52;
    cursor: not-allowed;
    background: var(--surface-muted);
    box-shadow: none;
  }

  .layer-select__eyebrow {
    font-size: 10px;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--text-faint);
    white-space: nowrap;
  }

  .layer-select__eyebrow::after {
    content: '·';
    margin-left: 6px;
    color: var(--border-strong);
  }

  .layer-select__value {
    font-size: 12.5px;
    font-weight: 700;
    color: var(--text);
    white-space: nowrap;
  }

  .layer-select__chevron {
    position: absolute;
    right: 9px;
    top: 50%;
    width: 10px;
    height: 7px;
    transform: translateY(-50%);
    color: var(--accent);
    transition: transform 0.18s ease;
  }

  .layer-select__chevron.flipped {
    transform: translateY(-50%) rotate(180deg);
  }

  .layer-select__list {
    position: absolute;
    top: calc(100% + 8px);
    right: 0;
    min-width: 230px;
    list-style: none;
    margin: 0;
    padding: 6px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    box-shadow: var(--shadow-lg);
    z-index: 30;
  }

  .layer-select__option {
    display: flex;
    flex-direction: column;
    padding: 8px 10px;
    border-radius: 8px;
    cursor: pointer;
  }

  .layer-select__option.active {
    background: var(--accent-soft);
  }

  .layer-select__option.current .layer-select__option-label::after {
    content: ' ✓';
    color: var(--accent-strong);
  }

  .layer-select__option-label {
    font-size: 13px;
    font-weight: 600;
    color: var(--text);
  }

  .layer-select__option-hint {
    font-size: 11px;
    color: var(--text-faint);
  }
</style>
