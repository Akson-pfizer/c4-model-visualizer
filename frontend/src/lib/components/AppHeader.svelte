<script>
  let { onOpenShortcuts } = $props();
</script>

<header class="app-header">
  <div class="app-header__brand">
    <svg class="app-header__mark" viewBox="0 0 32 32" aria-hidden="true">
      <rect width="32" height="32" rx="7" fill="#1D4ED8" />
      <rect x="5" y="5" width="9" height="9" rx="2" fill="#EFF6FF" />
      <rect x="18" y="5" width="9" height="9" rx="2" fill="#BFDBFE" />
      <rect x="5" y="18" width="9" height="9" rx="2" fill="#93C5FD" />
      <rect x="18" y="18" width="9" height="9" rx="2" fill="#60A5FA" />
    </svg>
    <div class="app-header__title">
      <span class="app-header__title-main">C4 modelling</span>
      <span class="app-header__title-sub">
        “Design is the silent ambassador of thought; code is merely its echo.”
      </span>
    </div>
  </div>

  <div class="app-header__brand app-header__brand--right">
    <button
      type="button"
      class="shortcuts-trigger"
      title="Keyboard Shortcuts for macOS (⌘) & Windows (Ctrl) — press ? or Ctrl+/"
      onclick={() => onOpenShortcuts?.()}
    >
      <span class="shortcuts-trigger__kbd">⌘ / Ctrl</span>
      <span>Shortcuts (?)</span>
    </button>
    <!-- Placeholder wordmark: swap for the official Pfizer logo asset from internal brand resources. -->
    <span class="pfizer-mark" aria-label="Pfizer">
      <span class="pfizer-mark__dot" aria-hidden="true"></span>
      Pfizer
    </span>
  </div>
</header>

<style>
  .app-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 12px 24px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    box-shadow: var(--shadow-sm);
    flex-wrap: wrap;
  }

  .app-header__brand {
    display: flex;
    align-items: center;
    gap: 10px;
    flex: 1;
    min-width: 200px;
  }

  .app-header__brand--right {
    justify-content: flex-end;
    gap: 14px;
  }

  .app-header__mark {
    width: 30px;
    height: 30px;
    flex-shrink: 0;
  }

  .app-header__title {
    display: flex;
    flex-direction: column;
    line-height: 1.15;
  }

  .app-header__title-main {
    font-size: 15px;
    font-weight: 700;
    color: var(--text);
  }

  .app-header__title-sub {
    font-size: 11.5px;
    font-style: italic;
    color: var(--text-muted);
  }

  .shortcuts-trigger {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 10px;
    border: 1px solid var(--border-strong);
    border-radius: 8px;
    background: var(--surface-muted);
    color: var(--text);
    font-size: 11.5px;
    font-weight: 700;
    cursor: pointer;
  }

  .shortcuts-trigger:hover {
    background: var(--blue-50);
    border-color: var(--blue-200);
    color: var(--blue-700);
  }

  .shortcuts-trigger__kbd {
    padding: 1px 6px;
    border-radius: 5px;
    font-family: var(--mono);
    font-size: 10.5px;
    background: var(--surface);
    border: 1px solid var(--border);
    color: var(--blue-700);
  }

  .pfizer-mark {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 17px;
    font-weight: 700;
    color: var(--blue-700);
    letter-spacing: -0.01em;
  }

  .pfizer-mark__dot {
    width: 9px;
    height: 9px;
    border-radius: 999px;
    background: var(--blue-700);
    display: inline-block;
  }

  @media (max-width: 760px) {
    .app-header {
      justify-content: center;
    }

    .app-header__brand--right {
      order: 3;
      justify-content: center;
    }
  }
</style>
