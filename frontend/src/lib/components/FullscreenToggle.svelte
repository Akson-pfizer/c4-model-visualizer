<script>
  /**
   * Fullscreen control for a diagram shell element.
   * Pass the element that should enter fullscreen (usually the canvas wrapper).
   */
  let { target = null } = $props();

  let isFullscreen = $state(false);

  function syncState() {
    const active = document.fullscreenElement;
    isFullscreen = Boolean(target && active === target);
  }

  $effect(() => {
    document.addEventListener('fullscreenchange', syncState);
    return () => document.removeEventListener('fullscreenchange', syncState);
  });

  async function toggle() {
    if (!target) return;
    try {
      if (document.fullscreenElement === target) {
        await document.exitFullscreen();
      } else if (!document.fullscreenElement) {
        await target.requestFullscreen();
      } else {
        await document.exitFullscreen();
        await target.requestFullscreen();
      }
    } catch (err) {
      console.warn('[Fullscreen] unavailable:', err);
    }
  }
</script>

<button
  type="button"
  class="fs-toggle"
  class:active={isFullscreen}
  onclick={toggle}
  title={isFullscreen ? 'Exit full screen (Esc)' : 'Full screen'}
  aria-label={isFullscreen ? 'Exit full screen' : 'Enter full screen'}
  aria-pressed={isFullscreen}
>
  {#if isFullscreen}
    <!-- Exit full screen: corners inward -->
    <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
      <path
        fill="currentColor"
        d="M8 3H6v3H3v2h5V3zm10 0h-2v5h5V6h-3V3zM8 16H3v2h3v3h2v-5zm8 0v5h2v-3h3v-2h-5z"
      />
    </svg>
  {:else}
    <!-- Enter full screen: corners outward -->
    <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
      <path
        fill="currentColor"
        d="M3 3h7v2H5v5H3V3zm11 0h7v7h-2V5h-5V3zM3 14h2v5h5v2H3v-7zm16 0h2v7h-7v-2h5v-5z"
      />
    </svg>
  {/if}
</button>

<style>
  .fs-toggle {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    padding: 0;
    border: 1px solid var(--border-strong, #c5d4e8);
    border-radius: 8px;
    background: var(--surface, #fff);
    color: var(--blue-700, #1d4ed8);
    cursor: pointer;
    box-shadow: var(--shadow-sm, 0 1px 2px rgba(15, 23, 42, 0.08));
  }

  .fs-toggle:hover {
    background: var(--blue-50, #eff6ff);
    border-color: var(--blue-500, #3b82f6);
  }

  .fs-toggle.active {
    background: var(--blue-700, #1d4ed8);
    border-color: var(--blue-700, #1d4ed8);
    color: #fff;
  }
</style>
