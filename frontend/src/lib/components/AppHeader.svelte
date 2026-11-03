<script>
  let {
    onOpenShortcuts,
    onOpenCatalog,
    onOpenStudio,
    profileName = 'Architect',
    appView = 'catalog'
  } = $props();

  let initial = $derived((profileName || 'A').slice(0, 1).toUpperCase());
  let onCatalog = $derived(appView === 'catalog');
</script>

<header class="app-header">
  <button
    type="button"
    class="app-header__brand app-header__brand-btn"
    title="Go to Architect Catalog"
    onclick={() => onOpenCatalog?.()}
  >
    <svg class="app-header__mark" viewBox="0 0 32 32" aria-hidden="true">
      <rect width="32" height="32" rx="7" fill="#1D4ED8" />
      <rect x="5" y="5" width="9" height="9" rx="2" fill="#EFF6FF" />
      <rect x="18" y="5" width="9" height="9" rx="2" fill="#BFDBFE" />
      <rect x="5" y="18" width="9" height="9" rx="2" fill="#93C5FD" />
      <rect x="18" y="18" width="9" height="9" rx="2" fill="#60A5FA" />
    </svg>
    <div class="app-header__title">
      <span class="app-header__title-main">Orthos</span>
      <span class="app-header__title-sub">
        {#if onCatalog}
          Architect Catalog — pick a repo or open Orthos Studio
        {:else}
          Orthos Studio — analyze, visualize, and refine architecture
        {/if}
      </span>
    </div>
  </button>

  <div class="app-header__brand app-header__brand--right">
    {#if onCatalog}
      <button
        type="button"
        class="studio-trigger"
        title="Open Orthos Studio analyzer"
        onclick={() => onOpenStudio?.()}
      >
        Orthos Studio
      </button>
    {:else}
      <button
        type="button"
        class="shortcuts-trigger"
        title="Keyboard Shortcuts for macOS (⌘) & Windows (Ctrl) — press ? or Ctrl+/"
        onclick={() => onOpenShortcuts?.()}
      >
        <span class="shortcuts-trigger__kbd">⌘ / Ctrl</span>
        <span>Shortcuts (?)</span>
      </button>
      <button
        type="button"
        class="profile-trigger"
        title="Back to Architect Catalog"
        onclick={() => onOpenCatalog?.()}
      >
        <span class="profile-trigger__avatar" aria-hidden="true">{initial}</span>
        <span class="profile-trigger__copy">
          <span class="profile-trigger__name">{profileName}</span>
          <span class="profile-trigger__sub">Catalog</span>
        </span>
      </button>
    {/if}
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

  .app-header__brand-btn {
    appearance: none;
    border: none;
    background: transparent;
    padding: 0;
    text-align: left;
    cursor: pointer;
  }

  .app-header__brand-btn:hover .app-header__title-main {
    color: var(--blue-700);
  }

  .app-header__brand--right {
    justify-content: flex-end;
    gap: 14px;
  }

  .studio-trigger {
    appearance: none;
    border: none;
    border-radius: 10px;
    padding: 8px 16px;
    background: linear-gradient(145deg, #1d4ed8, #2563eb);
    color: #fff;
    font-size: 13px;
    font-weight: 800;
    cursor: pointer;
    box-shadow: 0 8px 18px rgba(29, 78, 216, 0.24);
    transition: transform 0.18s ease, box-shadow 0.18s ease;
  }

  .studio-trigger:hover {
    transform: translateY(-1px);
    box-shadow: 0 12px 24px rgba(29, 78, 216, 0.32);
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

  .profile-trigger {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 4px 10px 4px 4px;
    border: 1px solid var(--border-strong);
    border-radius: 999px;
    background: var(--surface-muted);
    color: var(--text);
    cursor: pointer;
    max-width: 200px;
  }

  .profile-trigger:hover {
    background: var(--blue-50);
    border-color: var(--blue-200);
  }

  .profile-trigger__avatar {
    width: 26px;
    height: 26px;
    border-radius: 999px;
    background: var(--blue-700);
    color: #fff;
    display: grid;
    place-items: center;
    font-size: 12px;
    font-weight: 800;
    flex-shrink: 0;
  }

  .profile-trigger__copy {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    line-height: 1.1;
    min-width: 0;
  }

  .profile-trigger__name {
    font-size: 12px;
    font-weight: 700;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 120px;
  }

  .profile-trigger__sub {
    font-size: 10px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
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
