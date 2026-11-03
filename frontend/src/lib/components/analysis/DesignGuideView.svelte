<script>
  /**
   * Design Guide tab — upload guideline docs used as the Code Analysis bible / citations.
   */
  import { formatFriendlyError } from '../../analysisCatalog.js';

  let uploading = $state(false);
  let notice = $state('');
  /** @type {{ filename?: string, bytes?: number, uploaded_at?: string, citations?: string[], excerpt_preview?: string } | null} */
  let guide = $state(null);
  let active = $state(false);

  async function refresh() {
    try {
      const res = await fetch('/api/design-guide');
      const data = await res.json();
      active = Boolean(data.active);
      guide = data.guide ?? null;
    } catch (err) {
      notice = formatFriendlyError(err, 'Design Guide');
    }
  }

  $effect(() => {
    refresh();
  });

  async function onFileChange(event) {
    const input = /** @type {HTMLInputElement} */ (event.currentTarget);
    const file = input.files?.[0];
    if (!file) return;
    notice = '';
    uploading = true;
    try {
      const body = new FormData();
      body.append('file', file);
      const res = await fetch('/api/design-guide', { method: 'POST', body });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      active = true;
      guide = data.guide ?? null;
      notice = `Loaded “${guide?.filename || file.name}” as the analysis bible.`;
    } catch (err) {
      notice = formatFriendlyError(err, 'Design Guide upload');
    } finally {
      uploading = false;
      input.value = '';
    }
  }

  async function clearGuide() {
    notice = '';
    try {
      await fetch('/api/design-guide', { method: 'DELETE' });
      active = false;
      guide = null;
      notice = 'Design guide cleared.';
    } catch (err) {
      notice = formatFriendlyError(err, 'Design Guide');
    }
  }
</script>

<div class="dg">
  <header class="dg-header">
    <div>
      <h1>Design Guide</h1>
      <p>
        Upload design / coding guideline documentation. Code Analysis treats it as the
        <strong>bible</strong> for best practices and attaches citations on findings.
      </p>
    </div>
    <div class="dg-actions">
      <label class="dg-upload">
        <input
          type="file"
          accept=".md,.txt,.pdf,.docx,.html,.json,text/plain,text/markdown,application/pdf"
          disabled={uploading}
          onchange={onFileChange}
        />
        {uploading ? 'Uploading…' : 'Upload guide'}
      </label>
      {#if active}
        <button type="button" class="dg-clear" onclick={clearGuide}>Remove</button>
      {/if}
    </div>
  </header>

  {#if notice}
    <output class="dg-notice">{notice}</output>
  {/if}

  {#if active && guide}
    <section class="dg-card" aria-label="Active design guide">
      <h2>{guide.filename}</h2>
      <p class="dg-meta">
        {(guide.bytes ?? 0).toLocaleString()} bytes
        {#if guide.uploaded_at}
          · uploaded {new Date(guide.uploaded_at).toLocaleString()}
        {/if}
      </p>
      {#if guide.excerpt_preview}
        <h3>Preview</h3>
        <pre class="dg-excerpt">{guide.excerpt_preview}</pre>
      {/if}
      {#if guide.citations?.length}
        <h3>Citation anchors</h3>
        <ul class="dg-cites">
          {#each guide.citations as cite, i (i)}
            <li>{cite}</li>
          {/each}
        </ul>
      {/if}
    </section>
  {:else}
    <section class="dg-empty">
      <p>No design guide uploaded yet. Add a PDF, Markdown, or text guideline to ground analysis.</p>
    </section>
  {/if}
</div>

<style>
  .dg {
    height: 100%;
    overflow: auto;
    padding: 20px;
    background: linear-gradient(180deg, #f7fbff 0%, var(--surface-muted) 45%, var(--canvas-bg) 100%);
  }

  .dg-header {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 16px;
  }

  .dg-header h1 {
    font-size: 1.35rem;
    color: var(--pfizer-blue-90);
  }

  .dg-header p {
    margin: 6px 0 0;
    max-width: 40rem;
    color: var(--text-muted);
    font-size: 0.92rem;
  }

  .dg-actions {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  .dg-upload {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    height: 40px;
    padding: 0 16px;
    border-radius: 8px;
    background: var(--pfizer-blue-70);
    color: #fff;
    font-weight: 700;
    cursor: pointer;
  }

  .dg-upload input {
    display: none;
  }

  .dg-clear {
    height: 40px;
    padding: 0 14px;
    border-radius: 8px;
    border: 1px solid var(--border-strong);
    background: var(--surface);
    cursor: pointer;
  }

  .dg-notice {
    display: block;
    margin-bottom: 12px;
    padding: 10px 12px;
    border-radius: 8px;
    border: 1px solid var(--border);
    background: #eff6ff;
    color: var(--pfizer-blue-90);
  }

  .dg-card,
  .dg-empty {
    border: 1px solid var(--border);
    border-radius: 12px;
    background: var(--surface);
    padding: 16px;
  }

  .dg-meta {
    color: var(--text-muted);
    font-size: 0.85rem;
  }

  .dg-card h3 {
    margin: 14px 0 6px;
    font-size: 0.9rem;
  }

  .dg-excerpt {
    margin: 0;
    padding: 12px;
    border-radius: 8px;
    background: var(--surface-muted);
    white-space: pre-wrap;
    font-family: var(--mono);
    font-size: 0.78rem;
    max-height: 220px;
    overflow: auto;
  }

  .dg-cites {
    margin: 0;
    padding-left: 1.1rem;
    color: var(--text);
    font-size: 0.85rem;
  }
</style>
