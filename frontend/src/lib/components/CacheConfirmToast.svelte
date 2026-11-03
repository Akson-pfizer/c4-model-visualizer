<script>
  import { onDestroy, onMount } from 'svelte';

  /**
   * Top-right confirm toast for reopening a previously analyzed source.
   * Auto-uses cache when the timer expires.
   */
  let {
    title = 'Already analyzed',
    detail = 'A cached model is available for this source.',
    durationSec = 8,
    onUseCache,
    onReanalyze,
    onDismiss
  } = $props();

  let remaining = $state(durationSec);
  /** @type {ReturnType<typeof setInterval> | undefined} */
  let tick;

  function clearTick() {
    if (tick) clearInterval(tick);
    tick = undefined;
  }

  function useCache() {
    clearTick();
    onUseCache?.();
  }

  function reanalyze() {
    clearTick();
    onReanalyze?.();
  }

  function dismiss() {
    clearTick();
    onDismiss?.();
  }

  onMount(() => {
    remaining = durationSec;
    tick = setInterval(() => {
      if (remaining <= 1) {
        clearTick();
        onUseCache?.();
        return;
      }
      remaining -= 1;
    }, 1000);
  });

  onDestroy(clearTick);
</script>

<div
  class="cache-toast"
  role="alertdialog"
  aria-labelledby="cache-toast-title"
  aria-describedby="cache-toast-detail"
>
  <div class="cache-toast__header">
    <div class="cache-toast__copy">
      <p id="cache-toast-title" class="cache-toast__title">{title}</p>
      <p id="cache-toast-detail" class="cache-toast__detail">{detail}</p>
    </div>
    <p class="cache-toast__count" aria-live="polite">{remaining}s</p>
  </div>

  <div class="cache-toast__actions">
    <button type="button" class="cache-toast__btn cache-toast__btn--primary" onclick={useCache}>
      Use cache
    </button>
    <button type="button" class="cache-toast__btn cache-toast__btn--ghost" onclick={reanalyze}>
      Re-analyze
    </button>
    <button
      type="button"
      class="cache-toast__dismiss"
      onclick={dismiss}
      aria-label="Dismiss notification"
    >
      ×
    </button>
  </div>

  <div
    class="cache-toast__track"
    aria-hidden="true"
    style={`--toast-duration: ${durationSec}s`}
  >
    <span class="cache-toast__bar"></span>
  </div>
</div>

<style>
  .cache-toast {
    position: fixed;
    top: 16px;
    right: 16px;
    z-index: 60;
    width: min(380px, calc(100vw - 32px));
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 14px 14px 10px;
    background: var(--surface);
    color: var(--text);
    border: 1px solid var(--blue-300);
    border-right: 4px solid var(--blue-700);
    border-radius: 12px;
    box-shadow: var(--shadow-lg);
  }

  .cache-toast__header {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 10px;
    align-items: start;
  }

  .cache-toast__title {
    margin: 0;
    font-size: 14px;
    font-weight: 700;
  }

  .cache-toast__detail {
    margin: 4px 0 0;
    font-size: 12px;
    line-height: 1.4;
    color: var(--text-muted);
  }

  .cache-toast__count {
    margin: 0;
    font-size: 20px;
    font-weight: 700;
    color: var(--blue-700);
    font-variant-numeric: tabular-nums;
    line-height: 1;
  }

  .cache-toast__actions {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .cache-toast__btn {
    padding: 6px 12px;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
  }

  .cache-toast__btn--primary {
    border: none;
    background: var(--blue-700);
    color: #fff;
  }

  .cache-toast__btn--primary:hover {
    background: var(--blue-800, #1e40af);
  }

  .cache-toast__btn--ghost {
    border: 1px solid var(--border-strong);
    background: var(--surface);
    color: var(--blue-700);
  }

  .cache-toast__btn--ghost:hover {
    border-color: var(--blue-500);
    background: var(--blue-50);
  }

  .cache-toast__dismiss {
    margin-left: auto;
    width: 28px;
    height: 28px;
    border: none;
    border-radius: 8px;
    background: transparent;
    color: var(--text-muted);
    font-size: 18px;
    line-height: 1;
    cursor: pointer;
  }

  .cache-toast__dismiss:hover {
    background: var(--surface-muted);
    color: var(--text);
  }

  .cache-toast__track {
    height: 3px;
    border-radius: 999px;
    background: var(--blue-100);
    overflow: hidden;
  }

  .cache-toast__bar {
    display: block;
    height: 100%;
    width: 100%;
    background: var(--blue-600);
    transform-origin: left center;
    animation: cache-toast-countdown var(--toast-duration, 8s) linear forwards;
  }

  @keyframes cache-toast-countdown {
    from {
      transform: scaleX(1);
    }
    to {
      transform: scaleX(0);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .cache-toast__bar {
      animation: none;
    }
  }
</style>
