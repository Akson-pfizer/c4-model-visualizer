<script>
  import { validateSource } from '../sourceValidation.js';
  import { getCachedModels, loadLlmHubModels } from '../llmhubModels.js';
  import InfoToast from './InfoToast.svelte';

  let {
    source = '',
    analyzing = false,
    error = null,
    selectedModel = $bindable(''),
    onAnalyze,
    onStop,
    onResetDemo
  } = $props();

  const seed = getCachedModels();
  let inputVal = $state('');
  /** @type {'local' | 'github'} */
  let sourceType = $state('local');
  let touched = $state(false);
  /** @type {string[]} */
  let modelOptions = $state(seed?.options ?? []);
  if (!selectedModel && seed?.preferred) {
    selectedModel = seed.preferred;
  }
  let modelStatus = $state(seed?.status ?? 'Loading LLMHub models…');
  /** @type {'online' | 'offline' | 'error' | 'local' | 'loading'} */
  let statusKind = $state(seed?.statusKind ?? 'loading');
  /** @type {{ id: number, title: string, detail: string, tone: 'info' | 'success' | 'warn' | 'error' } | null} */
  let actionToast = $state(null);

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
      statusKind = cached.statusKind;
    });
    return () => {
      cancelled = true;
    };
  });

  let validation = $derived(validateSource(inputVal, sourceType));
  let showValidationError = $derived((touched || inputVal.trim().length > 0) && !validation.valid);
  let pathPlaceholder = $derived(
    sourceType === 'local'
      ? 'Enter a local directory path (e.g. /Users/.../repo or ./project)'
      : 'Enter a GitHub repository URL (e.g. https://github.com/owner/repo)'
  );

  function notify(title, detail = '', tone = /** @type {'info'} */ ('info')) {
    actionToast = { id: Date.now(), title, detail, tone };
  }

  function submit(event) {
    event.preventDefault();
    touched = true;
    if (!validation.valid || analyzing) return;
    notify(
      'Analysis started',
      `Running multi-agent pipeline with ${selectedModel || 'LLMHub'}.`,
      'info'
    );
    onAnalyze?.(inputVal.trim(), sourceType, {
      use_llm: true,
      model: selectedModel || null
    });
  }

  function handleReset() {
    touched = false;
    inputVal = '';
    notify('Source cleared', 'Path reset.', 'success');
    onResetDemo?.();
  }

  function handleStop() {
    notify('Analysis stopped', 'The running job was cancelled.', 'warn');
    onStop?.();
  }
</script>

<!-- source-bar -->
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
          placeholder={pathPlaceholder}
          bind:value={inputVal}
          oninput={() => (touched = true)}
          aria-invalid={showValidationError}
          aria-describedby={showValidationError ? 'source-validation-msg' : undefined}
          disabled={analyzing}
        />
        {#if showValidationError}
          <span id="source-validation-msg" class="source-section__validation is-error">
            {validation.message}
          </span>
        {/if}
      </div>
    </div>

    <div class="source-section source-section--type">
      <label class="source-section__label" for="repo-source-type">
        2 · Source Type
      </label>
      <div class="source-section__select-wrap">
        <select
          id="repo-source-type"
          class="source-section__select source-section__select--type"
          bind:value={sourceType}
          onchange={() => (touched = true)}
          disabled={analyzing}
        >
          <option value="local">Local</option>
          <option value="github" disabled>Github</option>
        </select>
      </div>
    </div>

    <div class="source-section source-section--llm">
      <div class="source-section__label-row">
        <label class="source-section__label" for="repo-llm-model">3 · LLMHub</label>
        <span class="hub-status" title={modelStatus}>
          <span
            class="hub-dot"
            class:is-online={statusKind === 'online'}
            class:is-local={statusKind === 'local'}
            class:is-offline={statusKind === 'offline' || statusKind === 'loading'}
            class:is-error={statusKind === 'error'}
            aria-label={modelStatus}
            role="img"
          ></span>
          <span class="hub-status__tip" role="tooltip">{modelStatus}</span>
        </span>
      </div>
      <div class="source-section__llm-row">
        <select
          id="repo-llm-model"
          class="source-section__select source-section__select--model"
          bind:value={selectedModel}
          disabled={analyzing || modelOptions.length === 0}
          aria-label="LLMHub model"
        >
          {#if modelOptions.length === 0}
            <option value="">No models</option>
          {:else}
            {#each modelOptions as mid (mid)}
              <option value={mid}>{mid}</option>
            {/each}
          {/if}
        </select>
      </div>
    </div>

    <div class="source-section source-section--actions">
      <span class="source-section__label">4 · Actions</span>
      <div class="source-section__buttons">
        {#if analyzing}
          <button type="button" class="source-bar__stop" onclick={handleStop} aria-label="Stop analysis">
            Stop
          </button>
        {:else}
          <button type="submit" class="source-bar__submit" disabled={!validation.valid}>
            Analyze
          </button>
        {/if}
        <button type="button" class="source-bar__reset" disabled={analyzing} onclick={handleReset}>
          Clear
        </button>
      </div>
    </div>
  </form>

  {#if error}
    <p class="source-bar__error" role="alert">{error}</p>
  {/if}
</div>

{#if actionToast}
  {#key actionToast.id}
    <InfoToast
      title={actionToast.title}
      detail={actionToast.detail}
      tone={actionToast.tone}
      durationSec={10}
      onClose={() => (actionToast = null)}
    />
  {/key}
{/if}

<style>
  .source-bar-wrapper {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 6px 24px 8px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
  }

  .source-top-div {
    display: grid;
    grid-template-columns: minmax(180px, 1.2fr) 108px minmax(112px, 148px) auto;
    align-items: end;
    gap: 8px;
    padding: 5px 8px;
    background: var(--surface-muted);
    border: 1px solid var(--border);
    border-radius: 10px;
  }

  .source-section {
    display: flex;
    flex-direction: column;
    gap: 3px;
    min-width: 0;
  }

  .source-section--type,
  .source-section--llm,
  .source-section--actions {
    padding-left: 10px;
    border-left: 1px solid var(--border);
  }

  .source-section--llm {
    max-width: 148px;
  }

  .source-section--actions {
    justify-self: start;
  }

  .source-section__label-row {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }

  .source-section__llm-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .hub-status {
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 18px;
    height: 18px;
    cursor: help;
    flex-shrink: 0;
  }

  .hub-status__tip {
    position: absolute;
    left: 50%;
    bottom: calc(100% + 8px);
    transform: translateX(-50%);
    min-width: 160px;
    max-width: 240px;
    padding: 6px 8px;
    border-radius: 8px;
    background: #0f172a;
    color: #f8fafc;
    font-size: 11px;
    font-weight: 600;
    line-height: 1.35;
    text-align: center;
    white-space: normal;
    box-shadow: var(--shadow-md);
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.12s ease;
    z-index: 40;
  }

  .hub-status:hover .hub-status__tip,
  .hub-status:focus-within .hub-status__tip {
    opacity: 1;
  }

  .hub-dot {
    width: 8px;
    height: 8px;
    border-radius: 999px;
    background: #94a3b8;
    box-shadow: 0 0 0 2px rgba(148, 163, 184, 0.25);
    flex-shrink: 0;
  }

  .hub-dot.is-online {
    background: #16a34a;
    box-shadow: 0 0 0 2px rgba(22, 163, 74, 0.22);
  }

  .hub-dot.is-local {
    background: #0d9488;
    box-shadow: 0 0 0 2px rgba(13, 148, 136, 0.22);
  }

  .hub-dot.is-offline {
    background: #f59e0b;
    box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.22);
  }

  .hub-dot.is-error {
    background: #dc2626;
    box-shadow: 0 0 0 2px rgba(220, 38, 38, 0.2);
  }

  @media (max-width: 960px) {
    .source-top-div {
      grid-template-columns: 1fr;
      align-items: stretch;
    }

    .source-section--type,
    .source-section--llm,
    .source-section--actions {
      padding-left: 0;
      border-left: none;
      padding-top: 6px;
      border-top: 1px solid var(--border);
    }
  }

  .source-section__label {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: var(--text-muted);
  }

  .source-section__field {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .source-section__input {
    width: 100%;
    max-width: 100%;
    padding: 4px 8px;
    border: 1px solid var(--border-strong);
    border-radius: 7px;
    background: var(--surface);
    color: var(--text);
    font-size: 11.5px;
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
    font-size: 10.5px;
  }

  .source-section__validation.is-error {
    color: #dc2626;
    font-weight: 600;
  }

  .source-section__select-wrap {
    display: flex;
  }

  .source-section__select {
    width: 100%;
    min-width: 0;
    padding: 4px 6px;
    border: 1px solid var(--border-strong);
    border-radius: 7px;
    background: var(--surface);
    color: var(--text);
    font-size: 11.5px;
    font-weight: 700;
    cursor: pointer;
  }

  .source-section__select--type {
    max-width: 108px;
  }

  .source-section__select--model {
    max-width: 132px;
    width: 132px;
  }

  .source-section__select option:disabled {
    color: #94a3b8;
  }

  .source-section__select:focus {
    outline: 2px solid var(--blue-200);
    border-color: var(--blue-600);
  }

  .source-section__buttons {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .source-bar__submit {
    padding: 5px 12px;
    border: none;
    border-radius: 7px;
    background: var(--blue-700);
    color: #fff;
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
    white-space: nowrap;
  }

  .source-bar__submit:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }

  .source-bar__stop {
    padding: 5px 12px;
    border: none;
    border-radius: 7px;
    background: #b91c1c;
    color: #fff;
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
    white-space: nowrap;
  }

  .source-bar__reset {
    padding: 5px 10px;
    border: 1px solid var(--border-strong);
    border-radius: 7px;
    background: var(--surface);
    color: var(--blue-700);
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    white-space: nowrap;
  }

  .source-bar__reset:hover {
    border-color: var(--blue-500);
    background: var(--blue-50);
  }

  .source-bar__error {
    margin: 0;
    padding: 5px 9px;
    border-radius: 7px;
    background: #fef2f2;
    border: 1px solid #fecaca;
    color: #b91c1c;
    font-size: 12px;
  }
</style>
