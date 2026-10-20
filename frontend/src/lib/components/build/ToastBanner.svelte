<script>
  let { name, remaining } = $props();
</script>

<div class="toast" role="status">
  <p class="sr-only">{name} plan submitted. This notice closes in 10 seconds.</p>
  <div class="toast__copy" aria-hidden="true">
    <p class="toast__title">{name} plan submitted</p>
    <p class="toast__detail">Design and implementation plan accepted.</p>
  </div>
  <p class="toast__count" aria-hidden="true">{remaining}s</p>
  <div class="toast__track" aria-hidden="true">
    <span class="toast__bar"></span>
  </div>
</div>

<style>
  .toast {
    position: fixed;
    top: 16px;
    left: 16px;
    z-index: 40;
    width: min(360px, calc(100vw - 32px));
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 4px 12px;
    padding: 12px 14px 10px;
    background: var(--surface);
    color: var(--text);
    border: 1px solid var(--blue-300);
    border-left: 4px solid var(--blue-700);
    border-radius: 12px;
    box-shadow: var(--shadow-lg);
  }

  .toast__title {
    margin: 0;
    font-size: 14px;
    font-weight: 700;
  }

  .toast__detail {
    margin: 2px 0 0;
    font-size: 12px;
    color: var(--text-muted);
  }

  .toast__count {
    margin: 0;
    font-size: 20px;
    font-weight: 700;
    color: var(--blue-700);
    font-variant-numeric: tabular-nums;
  }

  .toast__track {
    grid-column: 1 / -1;
    height: 3px;
    margin-top: 6px;
    border-radius: 999px;
    background: var(--blue-100);
    overflow: hidden;
  }

  .toast__bar {
    display: block;
    height: 100%;
    width: 100%;
    background: var(--blue-600);
    transform-origin: left center;
    animation: toast-countdown 10s linear forwards;
  }

  @keyframes toast-countdown {
    from {
      transform: scaleX(1);
    }
    to {
      transform: scaleX(0);
    }
  }

  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }
</style>
