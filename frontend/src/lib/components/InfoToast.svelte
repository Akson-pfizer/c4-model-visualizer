<script>
  import { onDestroy, onMount } from 'svelte';

  /**
   * Top-right timed notification with a countdown slider.
   * @typedef {'info' | 'success' | 'warn' | 'error'} ToastTone
   */
  let {
    title = 'Notice',
    detail = '',
    tone = /** @type {ToastTone} */ ('info'),
    durationSec = 10,
    onClose
  } = $props();

  let remaining = $state(durationSec);
  /** @type {ReturnType<typeof setInterval> | undefined} */
  let tick;

  function clearTick() {
    if (tick) clearInterval(tick);
    tick = undefined;
  }

  function dismiss() {
    clearTick();
    onClose?.();
  }

  onMount(() => {
    remaining = durationSec;
    tick = setInterval(() => {
      if (remaining <= 1) {
        dismiss();
        return;
      }
      remaining -= 1;
    }, 1000);
  });

  onDestroy(clearTick);
</script>

<div
  class="info-toast"
  class:tone-info={tone === 'info'}
  class:tone-success={tone === 'success'}
  class:tone-warn={tone === 'warn'}
  class:tone-error={tone === 'error'}
  role="status"
  aria-live="polite"
  style={`--toast-duration: ${durationSec}s`}
>
  <div class="info-toast__header">
    <div class="info-toast__copy">
      <p class="info-toast__title">{title}</p>
      {#if detail}
        <p class="info-toast__detail">{detail}</p>
      {/if}
    </div>
    <p class="info-toast__count">{remaining}s</p>
    <button type="button" class="info-toast__close" onclick={dismiss} aria-label="Dismiss">
      ×
    </button>
  </div>
  <div class="info-toast__track" aria-hidden="true">
    <span class="info-toast__bar"></span>
  </div>
</div>

<style>
  .info-toast {
    position: fixed;
    top: 16px;
    right: 16px;
    z-index: 70;
    width: min(360px, calc(100vw - 32px));
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 12px 12px 8px;
    background: var(--surface);
    color: var(--text);
    border: 1px solid #86efac;
    border-right: 4px solid #16a34a;
    border-radius: 12px;
    box-shadow: var(--shadow-lg);
  }

  .info-toast.tone-success {
    border-color: #86efac;
    border-right-color: #16a34a;
  }

  .info-toast.tone-info {
    border-color: #86efac;
    border-right-color: #059669;
  }

  .info-toast.tone-warn {
    border-color: #fcd34d;
    border-right-color: #d97706;
  }

  .info-toast.tone-error {
    border-color: #fca5a5;
    border-right-color: #dc2626;
  }

  .info-toast__header {
    display: grid;
    grid-template-columns: 1fr auto auto;
    gap: 8px;
    align-items: start;
  }

  .info-toast__title {
    margin: 0;
    font-size: 13px;
    font-weight: 700;
  }

  .info-toast__detail {
    margin: 3px 0 0;
    font-size: 12px;
    line-height: 1.35;
    color: var(--text-muted);
  }

  .info-toast__count {
    margin: 0;
    font-size: 18px;
    font-weight: 700;
    color: #15803d;
    font-variant-numeric: tabular-nums;
    line-height: 1;
  }

  .tone-warn .info-toast__count {
    color: #b45309;
  }

  .tone-error .info-toast__count {
    color: #b91c1c;
  }

  .info-toast__close {
    width: 24px;
    height: 24px;
    border: none;
    border-radius: 6px;
    background: transparent;
    color: var(--text-muted);
    font-size: 16px;
    line-height: 1;
    cursor: pointer;
  }

  .info-toast__track {
    height: 3px;
    border-radius: 999px;
    background: #dcfce7;
    overflow: hidden;
  }

  .tone-warn .info-toast__track {
    background: #fef3c7;
  }

  .tone-error .info-toast__track {
    background: #fee2e2;
  }

  .info-toast__bar {
    display: block;
    height: 100%;
    width: 100%;
    background: #16a34a;
    transform-origin: left center;
    animation: info-toast-countdown var(--toast-duration, 10s) linear forwards;
  }

  .tone-warn .info-toast__bar {
    background: #d97706;
  }

  .tone-error .info-toast__bar {
    background: #dc2626;
  }

  @keyframes info-toast-countdown {
    from {
      transform: scaleX(1);
    }
    to {
      transform: scaleX(0);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .info-toast__bar {
      animation: none;
    }
  }
</style>
