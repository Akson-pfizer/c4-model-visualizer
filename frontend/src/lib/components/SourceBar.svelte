<script>
  let {
    source = '',
    analyzing = false,
    error = null,
    activeRepoName = 'Internet Banking System (Demo)',
    agents = [],
    onAnalyze,
    onResetDemo
  } = $props();

  let inputVal = $state('/Users/aksonsamvarghese/Work/claude_bootcamp');
  /** @type {'local' | 'github'} */
  let sourceType = $state('local');
  let touched = $state(false);
  let showAgents = $state(false);

  $effect(() => {
    if (source) {
      inputVal = source;
    }
  });

  const GITHUB_PATTERNS = [
    /^https?:\/\/(www\.)?github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+(\/.*)?$/,
    /^git@github\.com:[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+(\.git)?$/,
    /^github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+(\/.*)?$/
  ];

  const LOCAL_PATH_PATTERN =
    /^(\/[A-Za-z0-9_.\-/ ]+|~\/[A-Za-z0-9_.\-/ ]+|\.\.?\/[A-Za-z0-9_.\-/ ]+|[A-Za-z]:\\[A-Za-z0-9_.\-\\ ]+|[A-Za-z0-9_.-]+(\/[A-Za-z0-9_.\-/ ]*)*)$/;

  function validateSource(raw, type) {
    const val = raw.trim();
    if (!val) {
      return {
        valid: false,
        message:
          type === 'local'
            ? 'Enter a local directory path (e.g. /Users/.../repo or ./project).'
            : 'Enter a GitHub repository URL (e.g. https://github.com/owner/repo).'
      };
    }

    const looksLikeUrl =
      /^https?:\/\//i.test(val) || /^git@/i.test(val) || /^github\.com\//i.test(val);

    if (type === 'local') {
      if (looksLikeUrl) {
        return {
          valid: false,
          message:
            'Invalid Local path: a GitHub/remote URL was entered while "Local" is selected.'
        };
      }
      if (/[<>:"|?*\0]/.test(val) || !LOCAL_PATH_PATTERN.test(val)) {
        return {
          valid: false,
          message:
            'Invalid Local path format. Use a valid filesystem path such as /Users/name/repo or ./folder.'
        };
      }
      return {
        valid: true,
        message: 'Valid local filesystem path format ✓'
      };
    }

    // type === 'github'
    if (val.startsWith('/') || val.startsWith('~/') || val.startsWith('./') || val.startsWith('../')) {
      return {
        valid: false,
        message:
          'Invalid Github path: a local filesystem path was entered while "Github" is selected.'
      };
    }

    const matchesGithub = GITHUB_PATTERNS.some((re) => re.test(val));
    if (!matchesGithub) {
      return {
        valid: false,
        message:
          'Invalid Github path. Expected https://github.com/<owner>/<repo> or git@github.com:<owner>/<repo>.git.'
      };
    }

    return {
      valid: true,
      message: 'Valid GitHub repository path ✓'
    };
  }

  let validation = $derived(validateSource(inputVal, sourceType));
  let showValidationError = $derived((touched || inputVal.trim().length > 0) && !validation.valid);

  function submit(event) {
    event.preventDefault();
    touched = true;
    if (!validation.valid || analyzing) return;
    onAnalyze?.(inputVal.trim(), sourceType);
  }

  function handleReset() {
    touched = false;
    inputVal = '';
    onResetDemo?.();
  }
</script>

<div class="source-bar-wrapper" aria-label="Source code repository controls">
  <form class="source-top-div" onsubmit={submit} novalidate>
    <!-- Section 1: Source Path Input -->
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

    <!-- Section 2: Dropdown to select Local or Github -->
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

    <!-- Section 3: Analyze button and Reset Demo -->
    <div class="source-section source-section--actions">
      <span class="source-section__label">3 · Actions</span>
      <div class="source-section__buttons">
        <button
          type="submit"
          class="source-bar__submit"
          disabled={analyzing || !validation.valid}
        >
          {analyzing ? 'Running Agents…' : 'Analyze'}
        </button>
        <button
          type="button"
          class="source-bar__reset"
          disabled={analyzing}
          onclick={handleReset}
        >
          Reset Demo
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
      {#if agents.length > 0}
        {#each agents as agent (agent.agent_id)}
          <div class="agent-card">
            <div class="agent-card__top">
              <span class="agent-card__id">{agent.agent_id}</span>
              {#if agent.layer}
                <span class="agent-card__layer">{agent.layer}</span>
              {/if}
            </div>
            <span class="agent-card__role">{agent.role}</span>
            <p class="agent-card__summary">{agent.summary}</p>
          </div>
        {/each}
      {:else}
        <div class="agent-card">
          <span class="agent-card__id">c4-manager</span>
          <span class="agent-card__role">Manager Agent</span>
          <p class="agent-card__summary">Accepts local path or GitHub URL, clones/scans repository, and invokes Supervisor.</p>
        </div>
        <div class="agent-card">
          <span class="agent-card__id">c4-supervisor</span>
          <span class="agent-card__role">Supervisor Agent</span>
          <p class="agent-card__summary">Coordinates all 4 layer subagents and links Context → Container → Component → Code as a hierarchy tree.</p>
        </div>
        <div class="agent-card">
          <span class="agent-card__id">subagent-context</span>
          <span class="agent-card__role">Context Specialist</span>
          <p class="agent-card__summary">Extracts top-level actors, systems in scope, and external integrations.</p>
        </div>
        <div class="agent-card">
          <span class="agent-card__id">subagent-container</span>
          <span class="agent-card__role">Container Specialist</span>
          <p class="agent-card__summary">Extracts deployable apps, services, and data stores linked to Context systems.</p>
        </div>
        <div class="agent-card">
          <span class="agent-card__id">subagent-component</span>
          <span class="agent-card__role">Component Specialist</span>
          <p class="agent-card__summary">Extracts controllers, services, and modules linked to parent Containers.</p>
        </div>
        <div class="agent-card">
          <span class="agent-card__id">subagent-code</span>
          <span class="agent-card__role">Code Specialist</span>
          <p class="agent-card__summary">Extracts classes, interfaces, and module exports linked to parent Components.</p>
        </div>
      {/if}
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
    grid-template-columns: minmax(280px, 1fr) 180px auto;
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
  .source-section--actions {
    padding-left: 14px;
    border-left: 1px solid var(--border);
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
    grid-template-columns: repeat(auto-fit, minmax(185px, 1fr));
    gap: 8px;
    padding-top: 4px;
  }

  .agent-card {
    padding: 8px 10px;
    border-radius: 10px;
    border: 1px solid var(--border);
    background: var(--surface-muted);
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .agent-card__top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
  }

  .agent-card__id {
    font-family: var(--mono);
    font-size: 11px;
    font-weight: 700;
    color: var(--blue-700);
  }

  .agent-card__layer {
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
    font-size: 11.5px;
    font-weight: 700;
    color: var(--text);
  }

  .agent-card__summary {
    margin: 2px 0 0;
    font-size: 11px;
    line-height: 1.35;
    color: var(--text-muted);
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
