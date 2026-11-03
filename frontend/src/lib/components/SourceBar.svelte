<script>
  import { DEFAULT_AGENT_ROSTER, validateSource } from '../sourceValidation.js';
  import { getCachedModels, loadLlmHubModels } from '../llmhubModels.js';

  let {
    source = '',
    analyzing = false,
    error = null,
    activeRepoName = 'No repository loaded',
    agents = [],
    onAnalyze,
    onStop,
    onResetDemo
  } = $props();

  const seed = getCachedModels();
  let inputVal = $state('');
  /** @type {'local' | 'github'} */
  let sourceType = $state('local');
  let touched = $state(false);
  let showAgents = $state(false);
  let useLlm = $state(false);
  /** @type {string[]} */
  let modelOptions = $state(seed?.options ?? []);
  let selectedModel = $state(seed?.preferred ?? '');
  let modelStatus = $state(seed?.status ?? 'Loading LLMHub models…');

  $effect(() => {
    if (source) {
      inputVal = source;
    }
  });

  $effect(() => {
    let cancelled = false;
    loadLlmHubModels().then((cached) => {
      if (cancelled) return;
      modelOptions = cached.options;
      if (!selectedModel || !cached.options.includes(selectedModel)) {
        selectedModel = cached.preferred;
      }
      modelStatus = cached.status;
    });
    return () => {
      cancelled = true;
    };
  });

  let validation = $derived(validateSource(inputVal, sourceType));
  let showValidationError = $derived((touched || inputVal.trim().length > 0) && !validation.valid);
  let displayAgents = $derived(agents.length > 0 ? agents : DEFAULT_AGENT_ROSTER);

  /**
   * Compact agent blurbs for the strip cards — full text stays on title hover.
   * @param {string} raw
   * @param {number} [maxLen]
   */
  function condenseSummary(raw, maxLen = 110) {
    let text = String(raw || '').replace(/\s+/g, ' ').trim();
    if (!text) return 'No summary.';

    // Drop the long hierarchy sermon that often trails supervisor reports.
    text = text
      .replace(/\s*Yes—each node should have exactly one valid parent[\s\S]*$/i, '')
      .replace(/\s*preserving a consistent Context→Container→Component→[\s\S]*$/i, '')
      .trim();

    const metrics = text.match(/(\d+)\s*nodes?.*?(\d+)\s*edges?/i);
    const first = text.split(/(?<=[.!?])\s+/)[0] || text;
    let base = first.length <= maxLen ? first : `${first.slice(0, maxLen - 1).trimEnd()}…`;
    if (metrics && !/nodes?/i.test(base)) {
      base = `${base.replace(/\.*$/, '')} · ${metrics[1]}n/${metrics[2]}e`;
    }
    return base;
  }

  /** @param {string} role */
  function shortRole(role) {
    const text = String(role || '').trim();
    if (text.length <= 42) return text;
    return `${text.slice(0, 40).trimEnd()}…`;
  }

  function submit(event) {
    event.preventDefault();
    touched = true;
    if (!validation.valid || analyzing) return;
    onAnalyze?.(inputVal.trim(), sourceType, {
      use_llm: useLlm,
      model: useLlm ? selectedModel || null : null
    });
  }

  function handleReset() {
    touched = false;
    inputVal = '';
    useLlm = false;
    onResetDemo?.();
  }
</script>

<div class="source-bar-wrapper" aria-label="Source code repository controls">
  <form class="source-top-div" onsubmit={submit} novalidate>
    <div class="source-section source-section--path">
      <label class="source-section__label" for="repo-source-input">
        1 · Source Path
      </label>
      <div class="source-section__field">
        <input
          id="repo-source-input"
          type="text"
          class="source-section__input"
          class:invalid={showValidationError}
          class:valid={inputVal.trim().length > 0 && validation.valid}
          placeholder={sourceType === 'local'
            ? '/Users/.../repo  or  ./folder'
            : 'https://github.com/owner/repo'}
          bind:value={inputVal}
          oninput={() => (touched = true)}
          aria-invalid={showValidationError}
          aria-describedby="source-validation-msg"
          disabled={analyzing}
        />
        <span
          id="source-validation-msg"
          class="source-section__validation"
          class:is-error={showValidationError}
          class:is-valid={inputVal.trim().length > 0 && validation.valid}
        >
          {validation.message}
        </span>
      </div>
    </div>

    <div class="source-section source-section--type">
      <label class="source-section__label" for="repo-source-type">
        2 · Source Type
      </label>
      <div class="source-section__select-wrap">
        <select
          id="repo-source-type"
          class="source-section__select"
          bind:value={sourceType}
          onchange={() => (touched = true)}
          disabled={analyzing}
        >
          <option value="local">Local</option>
          <option value="github">Github</option>
        </select>
      </div>
    </div>

    <div class="source-section source-section--llm">
      <label class="source-section__label" for="repo-llm-model">
        3 · LLMHub
      </label>
      <div class="source-section__llm-row">
        <label class="source-section__toggle">
          <input
            type="checkbox"
            bind:checked={useLlm}
            disabled={analyzing || modelOptions.length === 0}
          />
          <span>Use LLM</span>
        </label>
        <select
          id="repo-llm-model"
          class="source-section__select"
          bind:value={selectedModel}
          disabled={analyzing || !useLlm || modelOptions.length === 0}
          aria-label="LLMHub model"
        >
          {#if modelOptions.length === 0}
            <option value="">No models in .env</option>
          {:else}
            {#each modelOptions as mid (mid)}
              <option value={mid}>{mid}</option>
            {/each}
          {/if}
        </select>
      </div>
      <span class="source-section__hint">{modelStatus}</span>
    </div>

    <div class="source-section source-section--actions">
      <span class="source-section__label">4 · Actions</span>
      <div class="source-section__buttons">
        {#if analyzing}
          <button
            type="button"
            class="source-bar__stop"
            onclick={() => onStop?.()}
            aria-label="Stop analysis"
          >
            Stop
          </button>
        {:else}
          <button
            type="submit"
            class="source-bar__submit"
            disabled={!validation.valid}
          >
            Analyze
          </button>
        {/if}
        <button
          type="button"
          class="source-bar__reset"
          disabled={analyzing}
          onclick={handleReset}
        >
          Clear
        </button>
      </div>
    </div>
  </form>

  <div class="source-bar__meta">
    <span class="source-bar__active">
      Active Model: <strong>{activeRepoName}</strong>
    </span>

    <button
      type="button"
      class="source-bar__agents-toggle"
      aria-expanded={showAgents}
      onclick={() => (showAgents = !showAgents)}
    >
      {agents.length > 0
        ? `Multi-Agent Pipeline (${agents.length} agents ✓)`
        : 'Multi-Agent Pipeline: 1 Manager · 1 Supervisor · 4 Layer Subagents'}
      <span>{showAgents ? '▴' : '▾'}</span>
    </button>
  </div>

  {#if error}
    <p class="source-bar__error" role="alert">{error}</p>
  {/if}

  {#if showAgents}
    <div class="agent-strip" aria-label="Multi-agent hierarchy status">
      {#each displayAgents as agent (agent.agent_id)}
        <div class="agent-card" title={agent.summary || agent.role}>
          <div class="agent-card__top">
            <span class="agent-card__id">{agent.agent_id}</span>
            {#if agent.layer}
              <span class="agent-card__layer">{agent.layer}</span>
            {/if}
          </div>
          <span class="agent-card__role">{shortRole(agent.role)}</span>
          <p class="agent-card__summary">{condenseSummary(agent.summary)}</p>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .source-bar-wrapper {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 10px 24px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
  }

  .source-top-div {
    display: grid;
    grid-template-columns: minmax(240px, 1.2fr) 150px minmax(220px, 1fr) auto;
    align-items: start;
    gap: 14px;
    padding: 10px 14px;
    background: var(--surface-muted);
    border: 1px solid var(--border);
    border-radius: 12px;
  }

  .source-section {
    display: flex;
    flex-direction: column;
    gap: 4px;
    min-width: 0;
  }

  .source-section--type,
  .source-section--llm,
  .source-section--actions {
    padding-left: 14px;
    border-left: 1px solid var(--border);
  }

  .source-section__llm-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .source-section__toggle {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 12.5px;
    font-weight: 700;
    color: var(--text);
    white-space: nowrap;
    cursor: pointer;
  }

  .source-section__hint {
    font-size: 10.5px;
    color: var(--text-faint);
  }

  @media (max-width: 960px) {
    .source-top-div {
      grid-template-columns: 1fr;
    }

    .source-section--type,
    .source-section--llm,
    .source-section--actions {
      padding-left: 0;
      border-left: none;
      padding-top: 8px;
      border-top: 1px solid var(--border);
    }
  }

  .source-section__label {
    font-size: 10.5px;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: var(--text-muted);
  }

  .source-section__field {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .source-section__input {
    width: 100%;
    padding: 7px 12px;
    border: 1.5px solid var(--border-strong);
    border-radius: 9px;
    background: var(--surface);
    color: var(--text);
    font-size: 12.5px;
    font-family: var(--mono);
  }

  .source-section__input:focus {
    outline: 2px solid var(--blue-200);
    border-color: var(--blue-600);
  }

  .source-section__input.invalid {
    border-color: #dc2626;
    background: #fffafa;
  }

  .source-section__input.valid {
    border-color: var(--blue-500);
  }

  .source-section__validation {
    font-size: 11px;
    color: var(--text-faint);
  }

  .source-section__validation.is-error {
    color: #dc2626;
    font-weight: 600;
  }

  .source-section__validation.is-valid {
    color: var(--blue-700);
    font-weight: 600;
  }

  .source-section__select-wrap {
    display: flex;
  }

  .source-section__select {
    width: 100%;
    padding: 7px 12px;
    border: 1.5px solid var(--border-strong);
    border-radius: 9px;
    background: var(--surface);
    color: var(--text);
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
  }

  .source-section__select:focus {
    outline: 2px solid var(--blue-200);
    border-color: var(--blue-600);
  }

  .source-section__buttons {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .source-bar__submit {
    padding: 7px 16px;
    border: none;
    border-radius: 9px;
    background: var(--blue-700);
    color: #fff;
    font-size: 12.5px;
    font-weight: 700;
    cursor: pointer;
    white-space: nowrap;
  }

  .source-bar__submit:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }

  .source-bar__stop {
    padding: 7px 16px;
    border: none;
    border-radius: 9px;
    background: #b91c1c;
    color: #fff;
    font-size: 12.5px;
    font-weight: 700;
    cursor: pointer;
    white-space: nowrap;
  }

  .source-bar__stop:hover {
    background: #991b1b;
  }

  .source-bar__reset {
    padding: 7px 13px;
    border: 1px solid var(--border-strong);
    border-radius: 9px;
    background: var(--surface);
    color: var(--blue-700);
    font-size: 12.5px;
    font-weight: 600;
    cursor: pointer;
    white-space: nowrap;
  }

  .source-bar__reset:hover {
    border-color: var(--blue-500);
    background: var(--blue-50);
  }

  .source-bar__meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    flex-wrap: wrap;
    font-size: 12px;
    color: var(--text-muted);
  }

  .source-bar__agents-toggle {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 10px;
    border: 1px solid var(--blue-200);
    border-radius: 999px;
    background: var(--blue-50);
    color: var(--blue-700);
    font-size: 11.5px;
    font-weight: 600;
    cursor: pointer;
  }

  .source-bar__error {
    margin: 0;
    padding: 6px 10px;
    border-radius: 8px;
    background: #fef2f2;
    border: 1px solid #fecaca;
    color: #b91c1c;
    font-size: 12px;
  }

  .agent-strip {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 168px), 1fr));
    gap: 8px;
    padding-top: 4px;
    width: 100%;
    min-width: 0;
  }

  .agent-card {
    min-width: 0;
    max-width: 100%;
    padding: 8px 10px;
    border-radius: 10px;
    border: 1px solid var(--border);
    background: var(--surface-muted);
    display: flex;
    flex-direction: column;
    gap: 3px;
    overflow: hidden;
  }

  .agent-card__top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
    min-width: 0;
  }

  .agent-card__id {
    font-family: var(--mono);
    font-size: 11px;
    font-weight: 700;
    color: var(--blue-700);
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .agent-card__layer {
    flex-shrink: 0;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    padding: 1px 6px;
    border-radius: 999px;
    background: var(--blue-50);
    color: var(--blue-700);
    border: 1px solid var(--blue-200);
  }

  .agent-card__role {
    font-size: 11px;
    font-weight: 700;
    color: var(--text);
    line-height: 1.25;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .agent-card__summary {
    margin: 0;
    font-size: 10.5px;
    line-height: 1.3;
    color: var(--text-muted);
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
    word-break: break-word;
  }

  @media (max-width: 720px) {
    .agent-strip {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 860px) {
    .source-top-div {
      grid-template-columns: 1fr;
    }

    .source-section--type,
    .source-section--actions {
      padding-left: 0;
      border-left: none;
      padding-top: 8px;
      border-top: 1px solid var(--border);
    }
  }
</style>
