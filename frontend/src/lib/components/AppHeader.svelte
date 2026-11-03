<script>
  import OrthosMark from './OrthosMark.svelte';

  let {
    onOpenCatalog,
    onOpenStudio,
    onOpenProfile,
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
    <OrthosMark class="app-header__mark" size={24} />
    <div class="app-header__title">
      <span class="app-header__title-main">Orthos</span>
      <span class="app-header__title-sub">
        “Design is the silent ambassador of thought; code is merely its echo.”
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
    {/if}
    <button
      type="button"
      class="profile-trigger"
      title="Profile & LLMHub credentials"
      onclick={() => onOpenProfile?.()}
    >
      <span class="profile-trigger__avatar" aria-hidden="true">{initial}</span>
      <span class="profile-trigger__copy">
        <span class="profile-trigger__name">{profileName}</span>
        <span class="profile-trigger__sub">Settings</span>
      </span>
    </button>
  </div>
</header>

<style>
  .app-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 6px 20px;
    min-height: 44px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    box-shadow: none;
    flex-wrap: wrap;
  }

  .app-header__brand {
    display: flex;
    align-items: center;
    gap: 8px;
    flex: 1;
    min-width: 180px;
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
    gap: 10px;
    flex: 0 1 auto;
  }

  .studio-trigger {
    appearance: none;
    border: none;
    border-radius: 8px;
    padding: 5px 12px;
    background: linear-gradient(145deg, #1d4ed8, #2563eb);
    color: #fff;
    font-size: 12px;
    font-weight: 800;
    cursor: pointer;
    box-shadow: 0 4px 12px rgba(29, 78, 216, 0.2);
  }

  .studio-trigger:hover {
    box-shadow: 0 6px 16px rgba(29, 78, 216, 0.28);
  }

  :global(.app-header__mark) {
    width: 24px;
    height: 24px;
    flex-shrink: 0;
    display: block;
  }

  .app-header__title {
    display: flex;
    flex-direction: column;
    line-height: 1.1;
    min-width: 0;
  }

  .app-header__title-main {
    font-size: 14px;
    font-weight: 700;
    color: var(--text);
  }

  .app-header__title-sub {
    font-size: 10.5px;
    font-style: italic;
    color: var(--text-muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: min(520px, 55vw);
  }

  .profile-trigger {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 2px 8px 2px 2px;
    border: 1px solid var(--border-strong);
    border-radius: 999px;
    background: var(--surface-muted);
    color: var(--text);
    cursor: pointer;
    max-width: 180px;
  }

  .profile-trigger:hover {
    background: var(--blue-50);
    border-color: var(--blue-200);
  }

  .profile-trigger__avatar {
    width: 22px;
    height: 22px;
    border-radius: 999px;
    background: var(--blue-700);
    color: #fff;
    display: grid;
    place-items: center;
    font-size: 11px;
    font-weight: 800;
    flex-shrink: 0;
  }

  .profile-trigger__copy {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    line-height: 1.05;
    min-width: 0;
  }

  .profile-trigger__name {
    font-size: 11.5px;
    font-weight: 700;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 100px;
  }

  .profile-trigger__sub {
    font-size: 9px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  @media (max-width: 760px) {
    .app-header {
      justify-content: center;
    }

    .app-header__brand--right {
      order: 3;
      justify-content: center;
    }

    .app-header__title-sub {
      display: none;
    }
  }
</style>
