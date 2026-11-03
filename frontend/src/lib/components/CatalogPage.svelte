<script>
  import { onMount } from 'svelte';
  import {
    clearCatalog,
    fetchProfile,
    formatRelativeOpened,
    formatViewedAt,
    getProfile,
    listCatalog,
    openCatalogEntry,
    removeCatalogEntry,
    updateProfile
  } from '../projectCatalog.js';

  let {
    onOpenProject,
    onProfileChange
  } = $props();

  let profile = $state(getProfile());
  let entries = $state(/** @type {import('../projectCatalog.js').CatalogEntry[]} */ ([]));
  let query = $state('');
  let loading = $state(true);
  let error = $state(/** @type {string | null} */ (null));
  let openingId = $state(/** @type {string | null} */ (null));
  let editingName = $state(false);
  let nameDraft = $state(getProfile().display_name);

  async function refresh(search = query) {
    loading = true;
    error = null;
    try {
      const [listed, remoteProfile] = await Promise.all([
        listCatalog(search),
        fetchProfile()
      ]);
      entries = listed;
      profile = remoteProfile;
      nameDraft = remoteProfile.display_name;
      onProfileChange?.(remoteProfile.display_name);
    } catch (err) {
      error = err instanceof Error ? err.message : 'Could not load catalog';
      entries = [];
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    refresh('');
  });

  let filtered = $derived(entries);

  async function handleSearch(event) {
    event.preventDefault();
    await refresh(query);
  }

  async function saveName() {
    const next = await updateProfile({ display_name: nameDraft });
    profile = next;
    nameDraft = next.display_name;
    editingName = false;
    onProfileChange?.(next.display_name);
  }

  async function handleOpen(entry) {
    if (openingId) return;
    openingId = entry.id;
    error = null;
    try {
      const result = await openCatalogEntry(entry.id);
      onOpenProject?.(result);
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to open repository';
    } finally {
      openingId = null;
    }
  }

  async function handleRemove(id, event) {
    event.stopPropagation();
    try {
      await removeCatalogEntry(id);
      entries = entries.filter((e) => e.id !== id);
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to remove entry';
    }
  }

  async function handleClear() {
    if (!entries.length) return;
    if (!confirm('Clear all analyzed repositories from the catalog database?')) return;
    try {
      await clearCatalog();
      entries = [];
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to clear catalog';
    }
  }
</script>

<div class="catalog-page">
  <header class="catalog-page__hero">
    <div class="catalog-page__identity">
      <div class="catalog-page__avatar" aria-hidden="true">
        {(profile.display_name || 'A').slice(0, 1).toUpperCase()}
      </div>
      <div>
        <p class="catalog-page__eyebrow">Architect Catalog · Landing</p>
        {#if editingName}
          <form
            class="catalog-page__name-form"
            onsubmit={(e) => {
              e.preventDefault();
              saveName();
            }}
          >
            <input
              class="catalog-page__name-input"
              bind:value={nameDraft}
              maxlength="48"
              aria-label="Display name"
            />
            <button type="submit" class="catalog-page__name-save">Save</button>
            <button
              type="button"
              class="catalog-page__name-cancel"
              onclick={() => {
                editingName = false;
                nameDraft = profile.display_name;
              }}
            >
              Cancel
            </button>
          </form>
        {:else}
          <h1 class="catalog-page__title">
            {profile.display_name}
            <button
              type="button"
              class="catalog-page__edit"
              onclick={() => (editingName = true)}
            >
              Edit
            </button>
          </h1>
        {/if}
        <p class="catalog-page__meta">
          {entries.length} analyzed
          {entries.length === 1 ? 'repository' : 'repositories'} stored in the database —
          reopen without re-running agents
        </p>
      </div>
    </div>

    <form class="catalog-page__toolbar" onsubmit={handleSearch}>
      <label class="catalog-page__search">
        <span class="visually-hidden">Search catalog</span>
        <input
          type="search"
          placeholder="Search repositories…"
          bind:value={query}
        />
      </label>
      <button type="submit" class="catalog-page__search-btn">Search</button>
      <button
        type="button"
        class="catalog-page__clear"
        disabled={!entries.length}
        onclick={handleClear}
      >
        Clear catalog
      </button>
    </form>
  </header>

  {#if error}
    <p class="catalog-page__error" role="alert">{error}</p>
  {/if}

  <div class="catalog-page__body">
    {#if loading}
      <div class="catalog-page__empty">
        <strong>Loading catalog…</strong>
        <p>Fetching analyzed repositories from the database.</p>
      </div>
    {:else if filtered.length === 0}
      <div class="catalog-page__empty">
        <strong>No repositories yet</strong>
        <p>
          Use <strong>Orthos Studio</strong> in the nav bar to analyze a local path or GitHub URL.
          Each successful run is saved here with its full C4 model so you can reopen instantly.
        </p>
      </div>
    {:else}
      <ul class="repo-grid" aria-label="Analyzed repositories">
        {#each filtered as entry (entry.id)}
          <li>
            <article
              class="repo-card"
              class:repo-card--busy={openingId === entry.id}
            >
              <button
                type="button"
                class="repo-card__hit"
                disabled={Boolean(openingId)}
                onclick={() => handleOpen(entry)}
                aria-label="Open {entry.display_name}"
              >
                <div class="repo-card__shine" aria-hidden="true"></div>
                <div class="repo-card__top">
                  <span class="repo-card__type">{entry.source_type}</span>
                  {#if entry.style}
                    <span class="repo-card__style">{entry.style}</span>
                  {/if}
                </div>
                <h2 class="repo-card__name">{entry.display_name}</h2>
                <code class="repo-card__source" title={entry.source}>{entry.source}</code>
                <div class="repo-card__stats">
                  <span class="repo-card__opened">{formatRelativeOpened(entry.last_opened_at)}</span>
                  <span>Analyzed {formatViewedAt(entry.last_analyzed_at)}</span>
                  <span>Opened {entry.view_count}×</span>
                  {#if entry.node_count != null}
                    <span>{entry.node_count} nodes · {entry.edge_count ?? 0} edges</span>
                  {/if}
                </div>
                <span class="repo-card__cta">
                  {openingId === entry.id ? 'Opening…' : 'Open cached model →'}
                </span>
              </button>
              <button
                type="button"
                class="repo-card__remove"
                title="Remove from catalog"
                onclick={(e) => handleRemove(entry.id, e)}
              >
                Remove
              </button>
            </article>
          </li>
        {/each}
      </ul>
    {/if}
  </div>
</div>

<style>
  .catalog-page {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    background:
      radial-gradient(ellipse 80% 50% at 10% -10%, color-mix(in srgb, #93c5fd 35%, transparent), transparent),
      radial-gradient(ellipse 60% 40% at 90% 0%, color-mix(in srgb, #bfdbfe 28%, transparent), transparent),
      var(--canvas-bg, #f4f7fb);
    overflow: auto;
  }

  .catalog-page__hero {
    display: flex;
    flex-direction: column;
    gap: 18px;
    padding: 22px 28px 8px;
    max-width: 1180px;
    width: 100%;
    margin: 0 auto;
  }

  .catalog-page__identity {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .catalog-page__avatar {
    width: 56px;
    height: 56px;
    border-radius: 16px;
    display: grid;
    place-items: center;
    background: linear-gradient(145deg, #1d4ed8, #2563eb);
    color: #fff;
    font-size: 22px;
    font-weight: 800;
    box-shadow: 0 10px 24px rgba(29, 78, 216, 0.28);
  }

  .catalog-page__eyebrow {
    margin: 0 0 2px;
    font-size: 11px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-faint);
    font-weight: 700;
  }

  .catalog-page__title {
    margin: 0;
    font-size: 28px;
    font-weight: 800;
    color: var(--text);
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .catalog-page__edit {
    appearance: none;
    border: none;
    background: var(--blue-50, #eff6ff);
    color: var(--blue-700);
    font-size: 11px;
    font-weight: 700;
    padding: 3px 8px;
    border-radius: 6px;
    cursor: pointer;
  }

  .catalog-page__meta {
    margin: 4px 0 0;
    color: var(--text-muted);
    font-size: 13.5px;
  }

  .catalog-page__name-form {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  .catalog-page__name-input {
    font-size: 18px;
    font-weight: 700;
    padding: 6px 10px;
    border-radius: 8px;
    border: 1.5px solid var(--border-strong);
  }

  .catalog-page__name-save,
  .catalog-page__name-cancel {
    appearance: none;
    border: none;
    border-radius: 8px;
    padding: 6px 10px;
    font-weight: 700;
    cursor: pointer;
  }

  .catalog-page__name-save {
    background: var(--blue-700);
    color: #fff;
  }

  .catalog-page__name-cancel {
    background: var(--surface-muted);
    color: var(--text-muted);
  }

  .catalog-page__toolbar {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    align-items: center;
  }

  .catalog-page__search {
    flex: 1;
    min-width: 220px;
  }

  .catalog-page__search input {
    width: 100%;
    padding: 10px 14px;
    border-radius: 12px;
    border: 1.5px solid var(--border-strong);
    background: var(--surface);
    font-size: 14px;
  }

  .catalog-page__search-btn,
  .catalog-page__clear {
    appearance: none;
    border: none;
    border-radius: 10px;
    padding: 10px 14px;
    font-weight: 700;
    cursor: pointer;
  }

  .catalog-page__search-btn {
    background: var(--blue-700);
    color: #fff;
  }

  .catalog-page__clear {
    background: var(--surface);
    border: 1px solid var(--border);
    color: var(--text-muted);
  }

  .catalog-page__clear:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  .catalog-page__error {
    max-width: 1180px;
    width: 100%;
    margin: 8px auto 0;
    padding: 0 28px;
    color: #b91c1c;
    font-weight: 600;
    font-size: 13px;
  }

  .catalog-page__body {
    flex: 1;
    max-width: 1180px;
    width: 100%;
    margin: 0 auto;
    padding: 18px 28px 36px;
  }

  .catalog-page__empty {
    padding: 48px 24px;
    text-align: center;
    border: 1px dashed var(--border-strong);
    border-radius: 18px;
    background: color-mix(in srgb, var(--surface) 80%, transparent);
  }

  .catalog-page__empty strong {
    display: block;
    font-size: 18px;
    color: var(--text);
    margin-bottom: 8px;
  }

  .catalog-page__empty p {
    margin: 0 auto;
    max-width: 460px;
    color: var(--text-muted);
    line-height: 1.45;
  }

  .repo-grid {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 18px;
  }

  .repo-card {
    position: relative;
    height: 100%;
  }

  .repo-card__hit {
    position: relative;
    isolation: isolate;
    overflow: hidden;
    width: 100%;
    height: 100%;
    text-align: left;
    appearance: none;
    border: 1px solid var(--border);
    border-radius: 18px;
    background: linear-gradient(165deg, #ffffff 0%, #f8fbff 100%);
    padding: 18px 18px 52px;
    cursor: pointer;
    box-shadow: 0 8px 20px rgba(15, 23, 42, 0.04);
    transition:
      transform 0.22s cubic-bezier(0.22, 1, 0.36, 1),
      box-shadow 0.22s ease,
      border-color 0.22s ease;
  }

  .repo-card__shine {
    position: absolute;
    inset: -40% auto auto -30%;
    width: 70%;
    height: 70%;
    background: radial-gradient(circle, rgba(147, 197, 253, 0.35), transparent 65%);
    opacity: 0;
    transition: opacity 0.25s ease, transform 0.35s ease;
    pointer-events: none;
    z-index: 0;
  }

  .repo-card__hit:hover:not(:disabled),
  .repo-card__hit:focus-visible:not(:disabled) {
    transform: translateY(-6px) scale(1.015);
    border-color: color-mix(in srgb, var(--blue-500, #3b82f6) 55%, var(--border));
    box-shadow:
      0 18px 36px rgba(29, 78, 216, 0.14),
      0 2px 0 rgba(255, 255, 255, 0.8) inset;
  }

  .repo-card__hit:hover:not(:disabled) .repo-card__shine,
  .repo-card__hit:focus-visible:not(:disabled) .repo-card__shine {
    opacity: 1;
    transform: translate(18%, 12%);
  }

  .repo-card__hit:hover:not(:disabled) .repo-card__cta,
  .repo-card__hit:focus-visible:not(:disabled) .repo-card__cta {
    color: var(--blue-700);
    letter-spacing: 0.02em;
  }

  .repo-card--busy .repo-card__hit {
    opacity: 0.72;
  }

  .repo-card__top,
  .repo-card__name,
  .repo-card__source,
  .repo-card__stats,
  .repo-card__cta {
    position: relative;
    z-index: 1;
  }

  .repo-card__top {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    margin-bottom: 10px;
  }

  .repo-card__type,
  .repo-card__style {
    font-size: 10.5px;
    font-weight: 750;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    padding: 3px 8px;
    border-radius: 999px;
    background: var(--blue-50, #eff6ff);
    color: var(--blue-700);
  }

  .repo-card__style {
    background: #ecfdf5;
    color: #047857;
  }

  .repo-card__name {
    margin: 0 0 8px;
    font-size: 18px;
    font-weight: 800;
    color: var(--text);
  }

  .repo-card__source {
    display: block;
    font-size: 11.5px;
    color: var(--text-faint);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-bottom: 12px;
  }

  .repo-card__stats {
    display: flex;
    flex-direction: column;
    gap: 4px;
    font-size: 12px;
    color: var(--text-muted);
  }

  .repo-card__opened {
    font-weight: 750;
    color: var(--blue-700);
  }

  .repo-card__cta {
    display: inline-block;
    margin-top: 14px;
    font-size: 12.5px;
    font-weight: 750;
    color: var(--text-muted);
    transition: color 0.2s ease, letter-spacing 0.2s ease;
  }

  .repo-card__remove {
    position: absolute;
    right: 12px;
    bottom: 12px;
    z-index: 2;
    appearance: none;
    border: 1px solid var(--border);
    background: var(--surface);
    color: var(--text-muted);
    font-size: 11px;
    font-weight: 700;
    padding: 5px 9px;
    border-radius: 8px;
    cursor: pointer;
    opacity: 0;
    transform: translateY(4px);
    transition: opacity 0.18s ease, transform 0.18s ease, color 0.15s ease;
  }

  .repo-card:hover .repo-card__remove,
  .repo-card:focus-within .repo-card__remove {
    opacity: 1;
    transform: translateY(0);
  }

  .repo-card__remove:hover {
    color: #b91c1c;
    border-color: #fecaca;
  }

  .visually-hidden {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    border: 0;
  }

  @media (max-width: 720px) {
    .catalog-page__hero,
    .catalog-page__body,
    .catalog-page__error {
      padding-left: 16px;
      padding-right: 16px;
    }

    .catalog-page__title {
      font-size: 22px;
    }
  }
</style>
