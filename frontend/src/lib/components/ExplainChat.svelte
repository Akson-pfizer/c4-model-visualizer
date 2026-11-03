<script>
  /**
   * Explain chat — attaches the selected C4 component and streams compact / deep
   * explanations into a scrollable message thread via LLMHub.
   */
  let {
    selectedNode = null,
    open = $bindable(false),
    layersContext = null,
    currentLayerId = '',
    model = ''
  } = $props();

  /** @typedef {{ id: string, role: 'user' | 'assistant' | 'system', text: string, mode?: string }} ChatMessage */

  const COLLAPSE_CHARS = 280;

  let busy = $state(false);
  let error = $state(/** @type {string | null} */ (null));
  let messages = $state(/** @type {ChatMessage[]} */ ([]));
  let lastNodeId = $state(/** @type {string | null} */ (null));
  let threadEl = $state(/** @type {HTMLDivElement | null} */ (null));
  let draft = $state('');
  /** @type {Set<string>} */
  let expandedIds = $state(new Set());

  let attached = $derived.by(() => {
    if (!selectedNode?.data) return null;
    return {
      id: selectedNode.id,
      name: selectedNode.data.name || selectedNode.id,
      kind: selectedNode.data.kind || '',
      layer: selectedNode.data.layer || currentLayerId || '',
      technology: selectedNode.data.technology || '',
      description: selectedNode.data.description || ''
    };
  });

  $effect(() => {
    const id = attached?.id ?? null;
    if (id !== lastNodeId) {
      lastNodeId = id;
      messages = [];
      error = null;
      draft = '';
      expandedIds = new Set();
    }
  });

  $effect(() => {
    messages;
    if (!threadEl) return;
    requestAnimationFrame(() => {
      if (threadEl) threadEl.scrollTop = threadEl.scrollHeight;
    });
  });

  function toggle() {
    open = !open;
  }

  function pushMessage(role, text, mode) {
    const msg = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      role,
      text,
      mode
    };
    messages = [...messages, msg];
    return msg;
  }

  /**
   * Lightweight formatting: paragraphs + **bold**.
   * @param {string} text
   */
  function formatBlocks(text) {
    const cleaned = String(text || '')
      .replace(/\r\n/g, '\n')
      .replace(/\n{3,}/g, '\n\n')
      .trim();
    return cleaned
      .split(/\n\n+/)
      .map((block) => block.trim())
      .filter(Boolean)
      .map((block) => {
        /** @type {{ type: 'text' | 'bold', value: string }[]} */
        const parts = [];
        const re = /\*\*(.+?)\*\*/g;
        let last = 0;
        let match;
        while ((match = re.exec(block)) !== null) {
          if (match.index > last) {
            parts.push({ type: 'text', value: block.slice(last, match.index) });
          }
          parts.push({ type: 'bold', value: match[1] });
          last = match.index + match[0].length;
        }
        if (last < block.length) {
          parts.push({ type: 'text', value: block.slice(last) });
        }
        return parts.length ? parts : [{ type: 'text', value: block }];
      });
  }

  function isLong(text) {
    return String(text || '').trim().length > COLLAPSE_CHARS;
  }

  function isExpanded(id) {
    return expandedIds.has(id);
  }

  function toggleExpand(id) {
    const next = new Set(expandedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    expandedIds = next;
  }

  /**
   * @param {'compact' | 'deep'} mode
   * @param {string} [userPrompt]
   */
  async function askExplain(mode, userPrompt) {
    if (!attached) {
      error = 'Select a component on the canvas first.';
      return;
    }
    const prompt =
      userPrompt?.trim() ||
      (mode === 'deep'
        ? `Deep-explain ${attached.name} using the full C4 architecture context.`
        : `Explain ${attached.name} briefly.`);

    busy = true;
    error = null;
    pushMessage('user', prompt, mode);

    try {
      const res = await fetch('/api/explain/component', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...attached,
          mode,
          model: model || undefined,
          layers_context: mode === 'deep' ? layersContext : undefined
        })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || `Explain failed (${res.status})`);
      }
      const text = String(data.explanation || '').trim() || 'No explanation returned.';
      pushMessage('assistant', text, mode);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Could not explain component';
      error = msg;
      pushMessage('system', msg);
    } finally {
      busy = false;
    }
  }

  function submitDraft() {
    const text = draft.trim();
    if (!text || busy || !attached) return;
    draft = '';
    const deep =
      /\bdeep\b/i.test(text) || /\bin depth\b/i.test(text) || /\bdetailed\b/i.test(text);
    askExplain(deep ? 'deep' : 'compact', text);
  }

  function onDraftKeydown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      submitDraft();
    }
  }
</script>

<div class="explain-dock">
  {#if open}
    <section class="explain-panel" aria-label="Explain component chat">
      <header class="explain-panel__head">
        <div>
          <p class="explain-panel__eyebrow">Explain</p>
          <h2 class="explain-panel__title">Component chat</h2>
        </div>
        <button type="button" class="explain-panel__close" onclick={toggle} aria-label="Collapse explain">
          ✕
        </button>
      </header>

      <div class="explain-panel__attach">
        {#if attached}
          <span class="explain-panel__chip">Attached</span>
          <strong title={attached.name}>{attached.name}</strong>
          <span
            class="explain-panel__meta"
            title={[attached.kind, attached.layer, attached.technology].filter(Boolean).join(' · ')}
          >
            {[attached.kind, attached.layer, attached.technology].filter(Boolean).join(' · ')}
          </span>
        {:else}
          <span class="explain-panel__empty">No component selected — click a box on the canvas.</span>
        {/if}
      </div>

      <div class="explain-panel__thread" bind:this={threadEl} aria-live="polite">
        {#if messages.length === 0 && !busy}
          <p class="explain-panel__hint">
            Chat about the attached component. Use <strong>Explain</strong> for a short answer, or
            <strong>Deep explain</strong> for full architecture context.
          </p>
        {/if}
        {#each messages as msg (msg.id)}
          {@const long = msg.role === 'assistant' && isLong(msg.text)}
          {@const openBubble = !long || isExpanded(msg.id)}
          {@const blocks = formatBlocks(msg.text)}
          <div
            class="explain-bubble"
            class:explain-bubble--user={msg.role === 'user'}
            class:explain-bubble--assistant={msg.role === 'assistant'}
            class:explain-bubble--system={msg.role === 'system'}
            class:explain-bubble--deep={msg.mode === 'deep' && msg.role === 'assistant'}
            class:explain-bubble--collapsed={long && !openBubble}
          >
            {#if msg.role === 'assistant' && msg.mode}
              <span class="explain-bubble__tag">{msg.mode === 'deep' ? 'Deep' : 'Brief'}</span>
            {/if}
            {#if msg.role === 'assistant'}
              <div class="explain-bubble__body">
                {#each blocks as parts, i (i)}
                  <p class="explain-bubble__p">
                    {#each parts as part, j (j)}
                      {#if part.type === 'bold'}
                        <strong>{part.value}</strong>
                      {:else}
                        {part.value}
                      {/if}
                    {/each}
                  </p>
                {/each}
              </div>
              {#if long}
                <button
                  type="button"
                  class="explain-bubble__more"
                  onclick={() => toggleExpand(msg.id)}
                >
                  {openBubble ? 'Less' : 'More…'}
                </button>
              {/if}
            {:else}
              <p class="explain-bubble__text">{msg.text}</p>
            {/if}
          </div>
        {/each}
        {#if busy}
          <p class="explain-panel__status">Asking LLMHub…</p>
        {/if}
      </div>

      {#if error && !busy}
        <p class="explain-panel__error" role="alert">{error}</p>
      {/if}

      <footer class="explain-panel__foot">
        <input
          class="explain-panel__input"
          type="text"
          placeholder={attached ? 'Ask a follow-up…' : 'Select a component first'}
          bind:value={draft}
          disabled={busy || !attached}
          onkeydown={onDraftKeydown}
          aria-label="Explain chat message"
        />
        <div class="explain-panel__actions">
          <button
            type="button"
            class="explain-panel__ask explain-panel__ask--ghost"
            disabled={busy || !attached}
            onclick={() => askExplain('compact')}
          >
            Explain
          </button>
          <button
            type="button"
            class="explain-panel__ask"
            disabled={busy || !attached}
            onclick={() => askExplain('deep')}
            title="Uses all C4 layer context for an in-depth explanation"
          >
            {busy ? '…' : 'Deep explain'}
          </button>
        </div>
      </footer>
    </section>
  {/if}

  <button
    type="button"
    class="explain-fab"
    class:active={open}
    title="explain"
    aria-label="Explain"
    aria-expanded={open}
    onclick={toggle}
  >
    <span class="explain-fab__glow" aria-hidden="true"></span>
    <svg class="explain-fab__star" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path
        fill="currentColor"
        d="M12 1.5l1.35 7.05L20.5 10l-7.15 1.45L12 18.5l-1.35-7.05L3.5 10l7.15-1.45L12 1.5z"
      />
      <circle cx="12" cy="10" r="2.1" fill="currentColor" opacity="0.95" />
      <circle cx="12" cy="10" r="0.85" fill="#fff" opacity="0.9" />
    </svg>
  </button>
</div>

<style>
  .explain-dock {
    position: fixed;
    right: 18px;
    bottom: 66px;
    z-index: 56;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 10px;
  }

  .explain-fab {
    position: relative;
    width: 40px;
    height: 40px;
    display: grid;
    place-items: center;
    border: 1px solid color-mix(in srgb, #60a5fa 55%, var(--border-strong));
    border-radius: 999px;
    background: radial-gradient(circle at 40% 35%, #eff6ff 0%, #dbeafe 45%, #bfdbfe 100%);
    color: #1d4ed8;
    box-shadow:
      0 0 0 2px rgba(147, 197, 253, 0.35),
      0 0 14px rgba(59, 130, 246, 0.45),
      var(--shadow-lg);
    cursor: pointer;
    overflow: visible;
  }

  .explain-fab__glow {
    position: absolute;
    inset: -4px;
    border-radius: 999px;
    background: radial-gradient(circle, rgba(96, 165, 250, 0.55), transparent 68%);
    animation: explain-glow 1.8s ease-in-out infinite;
    pointer-events: none;
  }

  .explain-fab__star {
    position: relative;
    z-index: 1;
    filter: drop-shadow(0 0 4px rgba(255, 255, 255, 0.85));
  }

  .explain-fab:hover,
  .explain-fab.active {
    background: radial-gradient(circle at 40% 35%, #3b82f6 0%, #1d4ed8 70%);
    border-color: #1d4ed8;
    color: #fff;
    box-shadow:
      0 0 0 3px rgba(147, 197, 253, 0.45),
      0 0 20px rgba(37, 99, 235, 0.65),
      var(--shadow-lg);
  }

  @keyframes explain-glow {
    0%,
    100% {
      opacity: 0.45;
      transform: scale(0.92);
    }
    50% {
      opacity: 1;
      transform: scale(1.12);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .explain-fab__glow {
      animation: none;
      opacity: 0.7;
    }
  }

  .explain-panel {
    width: min(360px, calc(100vw - 36px));
    max-height: min(520px, calc(100vh - 120px));
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 12px;
    border: 1px solid var(--blue-200);
    border-radius: 14px;
    background: var(--surface);
    box-shadow: var(--shadow-lg);
  }

  .explain-panel__head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 8px;
    flex-shrink: 0;
  }

  .explain-panel__eyebrow {
    margin: 0;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: var(--blue-700);
  }

  .explain-panel__title {
    margin: 2px 0 0;
    font-size: 14px;
  }

  .explain-panel__close {
    width: 26px;
    height: 26px;
    border: 1px solid var(--border);
    border-radius: 7px;
    background: var(--surface-muted);
    color: var(--text-muted);
    cursor: pointer;
  }

  .explain-panel__attach {
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 8px 10px;
    border-radius: 10px;
    background: var(--blue-50);
    border: 1px solid var(--blue-200);
    max-height: 92px;
    overflow: auto;
    flex-shrink: 0;
  }

  .explain-panel__chip {
    width: fit-content;
    font-size: 9.5px;
    font-weight: 800;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--blue-700);
  }

  .explain-panel__attach strong {
    font-size: 13px;
    overflow-wrap: anywhere;
  }

  .explain-panel__meta,
  .explain-panel__empty,
  .explain-panel__hint,
  .explain-panel__status {
    font-size: 11.5px;
    color: var(--text-muted);
    line-height: 1.35;
  }

  .explain-panel__meta {
    overflow-wrap: anywhere;
    word-break: break-word;
  }

  .explain-panel__thread {
    flex: 1;
    min-height: 120px;
    max-height: 280px;
    overflow-y: auto;
    overflow-x: hidden;
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 4px 2px;
  }

  .explain-bubble {
    max-width: 94%;
    padding: 8px 10px;
    border-radius: 12px;
    font-size: 12.5px;
    line-height: 1.45;
  }

  .explain-bubble--user {
    align-self: flex-end;
    background: var(--blue-700);
    color: #fff;
    border-bottom-right-radius: 4px;
  }

  .explain-bubble--assistant {
    align-self: flex-start;
    background: var(--surface-muted);
    border: 1px solid var(--border);
    color: var(--text);
    border-bottom-left-radius: 4px;
  }

  .explain-bubble--deep {
    border-color: var(--pfizer-cyan-50, #0095ff);
    background: color-mix(in srgb, var(--pfizer-blue-10, #e8f2ff) 70%, white);
  }

  .explain-bubble--system {
    align-self: stretch;
    background: #fef2f2;
    border: 1px solid #fecaca;
    color: #b91c1c;
    font-size: 12px;
  }

  .explain-bubble--collapsed .explain-bubble__body {
    max-height: 5.8em;
    overflow: hidden;
    mask-image: linear-gradient(to bottom, #000 55%, transparent 100%);
  }

  .explain-bubble__tag {
    display: inline-block;
    margin-bottom: 4px;
    font-size: 9.5px;
    font-weight: 800;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--blue-700);
  }

  .explain-bubble__body {
    display: flex;
    flex-direction: column;
    gap: 0.55em;
  }

  .explain-bubble__p {
    margin: 0;
    overflow-wrap: anywhere;
  }

  .explain-bubble__text {
    margin: 0;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }

  .explain-bubble__more {
    margin-top: 6px;
    padding: 0;
    border: none;
    background: transparent;
    color: var(--blue-700);
    font-size: 11.5px;
    font-weight: 750;
    cursor: pointer;
    text-decoration: underline;
    text-underline-offset: 2px;
  }

  .explain-panel__error {
    margin: 0;
    font-size: 12px;
    color: #b91c1c;
    flex-shrink: 0;
  }

  .explain-panel__foot {
    display: flex;
    flex-direction: column;
    gap: 8px;
    flex-shrink: 0;
  }

  .explain-panel__input {
    width: 100%;
    padding: 7px 10px;
    border: 1.5px solid var(--blue-200);
    border-radius: 9px;
    background: var(--surface);
    color: var(--text);
    font-size: 12.5px;
  }

  .explain-panel__input:focus {
    outline: 2px solid var(--blue-200);
    border-color: var(--blue-600);
  }

  .explain-panel__actions {
    display: flex;
    justify-content: flex-end;
    gap: 6px;
  }

  .explain-panel__ask {
    padding: 6px 12px;
    border: none;
    border-radius: 8px;
    background: var(--blue-700);
    color: #fff;
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
    white-space: nowrap;
  }

  .explain-panel__ask--ghost {
    background: var(--surface);
    color: var(--blue-700);
    border: 1px solid var(--border-strong);
  }

  .explain-panel__ask:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }
</style>
