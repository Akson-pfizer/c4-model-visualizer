<script>
  import { formatFriendlyError } from '../../analysisCatalog.js';

  let { activeSource = '' } = $props();

  /** @type {'auto' | 'sphinx' | 'typedoc' | 'markdown'} */
  let docsStyle = $state('auto');
  let loading = $state(false);
  let generating = $state(false);
  let error = $state(/** @type {string | null} */ (null));
  let notice = $state(/** @type {string | null} */ (null));
  let preview = $state(/** @type {any | null} */ (null));
  let selectedModule = $state(/** @type {string | null} */ (null));
  let query = $state('');
  let lastSource = $state('');

  let modules = $derived(preview?.modules ?? []);
  let filteredModules = $derived.by(() => {
    const q = query.trim().toLowerCase();
    if (!q) return modules;
    return modules
      .map((mod) => {
        const symbols = (mod.symbols || []).filter((s) => {
          const hay = `${s.name} ${s.kind} ${s.signature} ${s.file_path}`.toLowerCase();
          return hay.includes(q) || String(mod.module).toLowerCase().includes(q);
        });
        return { ...mod, symbols, symbol_count: symbols.length };
      })
      .filter((mod) => mod.symbol_count > 0 || String(mod.module).toLowerCase().includes(q));
  });

  let activeModule = $derived.by(() => {
    if (!filteredModules.length) return null;
    return (
      filteredModules.find((m) => m.module === selectedModule) ?? filteredModules[0]
    );
  });

  let langEntries = $derived(
    Object.entries(preview?.language_counts || {}).sort((a, b) => b[1] - a[1])
  );

  async function loadPreview() {
    const source = activeSource.trim();
    if (!source) {
      preview = null;
      error = 'Analyze a local repository in Orthos Studio first, then open Reference Docs.';
      return;
    }
    loading = true;
    error = null;
    notice = null;
    try {
      const res = await fetch('/api/docs/reference/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source, style: docsStyle })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || `Preview failed (${res.status})`);
      }
      preview = data;
      lastSource = source;
      selectedModule = data.modules?.[0]?.module ?? null;
    } catch (err) {
      preview = null;
      error = formatFriendlyError(err, 'Reference Docs');
    } finally {
      loading = false;
    }
  }

  async function generateDocs() {
    const source = activeSource.trim();
    if (!source) {
      error = 'Analyze a local repository first.';
      return;
    }
    generating = true;
    error = null;
    notice = null;
    try {
      const res = await fetch('/api/docs/reference', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source, style: docsStyle })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || `Generate failed (${res.status})`);
      }
      preview = {
        ...(preview || {}),
        ...data,
        modules: data.modules || preview?.modules || []
      };
      notice =
        `${data.style_label}: ${data.symbol_count} symbols → ${data.index_file}` +
        (data.build_hint ? `\nBuild: ${data.build_hint}` : '');
      if (data.modules?.[0]?.module) {
        selectedModule = data.modules[0].module;
      }
    } catch (err) {
      error = formatFriendlyError(err, 'Reference Docs');
    } finally {
      generating = false;
    }
  }

  $effect(() => {
    const source = activeSource.trim();
    if (source && source !== lastSource) {
      loadPreview();
    } else if (!source) {
      preview = null;
      lastSource = '';
    }
  });
</script>

<div class="docs-view" aria-label="Code-layer reference documentation">
  <header class="docs-view__bar">
    <div class="docs-view__intro">
      <p class="docs-view__eyebrow">Code layer · Reference documentation</p>
      <h1 class="docs-view__title">
        {#if preview?.style === 'sphinx'}
          Sphinx API Reference
        {:else if preview?.style === 'typedoc'}
          TypeDoc / JSDoc Reference
        {:else if preview?.style === 'markdown'}
          Markdown API Reference
        {:else}
          Reference Docs
        {/if}
      </h1>
      <p class="docs-view__sub">
        Language-aware docs from the analyzed repository — Sphinx for Python, TypeDoc for JS/TS, Markdown otherwise.
      </p>
    </div>

    <div class="docs-view__controls">
      <label class="docs-view__field">
        <span>Style</span>
        <select bind:value={docsStyle} disabled={loading || generating}>
          <option value="auto">Auto (from language mix)</option>
          <option value="sphinx">Sphinx (Python)</option>
          <option value="typedoc">TypeDoc / JSDoc</option>
          <option value="markdown">Markdown</option>
        </select>
      </label>
      <button
        type="button"
        class="docs-view__btn docs-view__btn--ghost"
        disabled={loading || generating || !activeSource.trim()}
        onclick={loadPreview}
      >
        {loading ? 'Scanning…' : 'Refresh inventory'}
      </button>
      <button
        type="button"
        class="docs-view__btn"
        disabled={generating || loading || !activeSource.trim()}
        onclick={generateDocs}
      >
        {generating ? 'Writing files…' : 'Generate docs'}
      </button>
    </div>
  </header>

  {#if error}
    <p class="docs-view__alert docs-view__alert--err" role="alert">{error}</p>
  {/if}
  {#if notice}
    <p class="docs-view__alert docs-view__alert--ok">{notice}</p>
  {/if}

  {#if !activeSource.trim()}
    <div class="docs-view__empty">
      <strong>No repository loaded</strong>
      <p>Run Analyze in Orthos Studio, then return here to browse code-layer reference docs.</p>
    </div>
  {:else if loading && !preview}
    <div class="docs-view__empty">
      <strong>Scanning code layer…</strong>
      <p>Detecting language mix and indexing classes, interfaces, and functions.</p>
    </div>
  {:else if preview}
    <div class="docs-view__meta">
      <span class="docs-view__pill">{preview.style_label}</span>
      <span>{preview.symbol_count} symbols</span>
      <span>{preview.file_count ?? 0} files</span>
      <span>{modules.length} modules</span>
      {#each langEntries as [lang, count] (lang)}
        <span class="docs-view__lang">{lang} · {count}</span>
      {/each}
    </div>

    <div class="docs-shell">
      <aside class="docs-nav" aria-label="Modules">
        <label class="docs-nav__search">
          <span class="visually-hidden">Search symbols</span>
          <input type="search" placeholder="Search modules & symbols…" bind:value={query} />
        </label>
        <ul class="docs-nav__list">
          {#each filteredModules as mod (mod.module)}
            <li>
              <button
                type="button"
                class="docs-nav__item"
                class:active={activeModule?.module === mod.module}
                onclick={() => (selectedModule = mod.module)}
              >
                <code>{mod.module}</code>
                <span>{mod.symbol_count}</span>
              </button>
            </li>
          {/each}
        </ul>
      </aside>

      <section class="docs-main" aria-label="Symbol reference">
        {#if activeModule}
          <header class="docs-main__head">
            <h2><code>{activeModule.module}</code></h2>
            <p>{activeModule.symbol_count} symbols in this module</p>
          </header>
          <div class="docs-symbols">
            {#each activeModule.symbols as sym (sym.name + sym.file_path + sym.kind)}
              <article class="docs-symbol">
                <div class="docs-symbol__top">
                  <span class="docs-symbol__kind">{sym.kind}</span>
                  {#if sym.language}
                    <span class="docs-symbol__lang">{sym.language}</span>
                  {/if}
                </div>
                <h3 class="docs-symbol__name">{sym.name}</h3>
                {#if sym.signature}
                  <pre class="docs-symbol__sig">{sym.signature}</pre>
                {/if}
                {#if sym.docstring}
                  <p class="docs-symbol__doc">{sym.docstring}</p>
                {/if}
                <p class="docs-symbol__file">
                  <code>{sym.file_path}{sym.lineno ? `:${sym.lineno}` : ''}</code>
                </p>
              </article>
            {/each}
          </div>
        {:else}
          <div class="docs-view__empty docs-view__empty--inset">
            <strong>No matching symbols</strong>
            <p>Try a different search or refresh the inventory.</p>
          </div>
        {/if}
      </section>
    </div>
  {/if}
</div>

<style>
  .docs-view {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 16px 24px 20px;
    background:
      radial-gradient(ellipse 70% 40% at 0% 0%, color-mix(in srgb, #dbeafe 50%, transparent), transparent),
      var(--canvas-bg, #f4f7fb);
    overflow: hidden;
  }

  .docs-view__bar {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 16px;
    flex-wrap: wrap;
  }

  .docs-view__eyebrow {
    margin: 0 0 2px;
    font-size: 11px;
    font-weight: 750;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    color: var(--text-faint);
  }

  .docs-view__title {
    margin: 0;
    font-size: 22px;
    font-weight: 800;
    color: var(--text);
  }

  .docs-view__sub {
    margin: 4px 0 0;
    max-width: 560px;
    font-size: 13px;
    color: var(--text-muted);
    line-height: 1.4;
  }

  .docs-view__controls {
    display: flex;
    align-items: end;
    gap: 8px;
    flex-wrap: wrap;
  }

  .docs-view__field {
    display: flex;
    flex-direction: column;
    gap: 4px;
    font-size: 11px;
    font-weight: 700;
    color: var(--text-muted);
  }

  .docs-view__field select {
    min-width: 200px;
    padding: 8px 10px;
    border-radius: 9px;
    border: 1.5px solid var(--border-strong);
    background: var(--surface);
    font-size: 13px;
  }

  .docs-view__btn {
    appearance: none;
    border: none;
    border-radius: 9px;
    padding: 9px 14px;
    background: var(--blue-700);
    color: #fff;
    font-weight: 750;
    font-size: 13px;
    cursor: pointer;
  }

  .docs-view__btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .docs-view__btn--ghost {
    background: var(--surface);
    color: var(--blue-700);
    border: 1px solid var(--border-strong);
  }

  .docs-view__alert {
    margin: 0;
    padding: 8px 12px;
    border-radius: 10px;
    font-size: 12.5px;
    white-space: pre-wrap;
  }

  .docs-view__alert--err {
    background: #fef2f2;
    border: 1px solid #fecaca;
    color: #b91c1c;
  }

  .docs-view__alert--ok {
    background: #ecfdf5;
    border: 1px solid #a7f3d0;
    color: #047857;
  }

  .docs-view__empty {
    margin: 24px auto;
    padding: 36px 24px;
    max-width: 480px;
    text-align: center;
    border: 1px dashed var(--border-strong);
    border-radius: 16px;
    background: color-mix(in srgb, var(--surface) 85%, transparent);
  }

  .docs-view__empty--inset {
    margin: 40px auto;
  }

  .docs-view__empty strong {
    display: block;
    margin-bottom: 6px;
    font-size: 16px;
  }

  .docs-view__empty p {
    margin: 0;
    color: var(--text-muted);
    font-size: 13px;
    line-height: 1.4;
  }

  .docs-view__meta {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
    font-size: 12px;
    color: var(--text-muted);
  }

  .docs-view__pill,
  .docs-view__lang {
    padding: 3px 8px;
    border-radius: 999px;
    background: var(--blue-50, #eff6ff);
    color: var(--blue-700);
    font-weight: 700;
    font-size: 11px;
  }

  .docs-view__lang {
    background: var(--surface);
    border: 1px solid var(--border);
    color: var(--text-muted);
  }

  .docs-shell {
    flex: 1;
    min-height: 0;
    display: grid;
    grid-template-columns: minmax(200px, 260px) 1fr;
    gap: 12px;
    overflow: hidden;
  }

  .docs-nav,
  .docs-main {
    min-height: 0;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    box-shadow: var(--shadow-sm);
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }

  .docs-nav__search {
    padding: 10px;
    border-bottom: 1px solid var(--border);
  }

  .docs-nav__search input {
    width: 100%;
    padding: 8px 10px;
    border-radius: 8px;
    border: 1px solid var(--border-strong);
    font-size: 12.5px;
  }

  .docs-nav__list {
    list-style: none;
    margin: 0;
    padding: 6px;
    overflow: auto;
    flex: 1;
  }

  .docs-nav__item {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding: 8px 10px;
    border: none;
    border-radius: 8px;
    background: transparent;
    cursor: pointer;
    text-align: left;
    color: var(--text);
    font-size: 12px;
  }

  .docs-nav__item code {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 11.5px;
  }

  .docs-nav__item span {
    flex-shrink: 0;
    color: var(--text-faint);
    font-weight: 700;
    font-size: 11px;
  }

  .docs-nav__item:hover,
  .docs-nav__item.active {
    background: var(--blue-50, #eff6ff);
  }

  .docs-nav__item.active {
    color: var(--blue-700);
  }

  .docs-main__head {
    padding: 14px 16px 10px;
    border-bottom: 1px solid var(--border);
  }

  .docs-main__head h2 {
    margin: 0;
    font-size: 16px;
  }

  .docs-main__head p {
    margin: 4px 0 0;
    font-size: 12px;
    color: var(--text-muted);
  }

  .docs-symbols {
    flex: 1;
    overflow: auto;
    padding: 12px 16px 20px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .docs-symbol {
    padding: 12px 14px;
    border: 1px solid var(--border);
    border-radius: 12px;
    background: color-mix(in srgb, var(--canvas-bg, #f4f7fb) 55%, white);
  }

  .docs-symbol__top {
    display: flex;
    gap: 6px;
    margin-bottom: 4px;
  }

  .docs-symbol__kind,
  .docs-symbol__lang {
    font-size: 10px;
    font-weight: 750;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    padding: 2px 7px;
    border-radius: 999px;
    background: var(--blue-50, #eff6ff);
    color: var(--blue-700);
  }

  .docs-symbol__lang {
    background: var(--surface);
    border: 1px solid var(--border);
    color: var(--text-muted);
  }

  .docs-symbol__name {
    margin: 0;
    font-size: 15px;
    font-weight: 800;
    font-family: var(--mono, ui-monospace, monospace);
  }

  .docs-symbol__sig {
    margin: 8px 0 0;
    padding: 8px 10px;
    border-radius: 8px;
    background: #0f172a;
    color: #e2e8f0;
    font-size: 11.5px;
    overflow-x: auto;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .docs-symbol__doc {
    margin: 8px 0 0;
    font-size: 12.5px;
    line-height: 1.4;
    color: var(--text-muted);
  }

  .docs-symbol__file {
    margin: 8px 0 0;
    font-size: 11px;
    color: var(--text-faint);
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

  @media (max-width: 860px) {
    .docs-shell {
      grid-template-columns: 1fr;
    }

    .docs-nav {
      max-height: 220px;
    }
  }
</style>
