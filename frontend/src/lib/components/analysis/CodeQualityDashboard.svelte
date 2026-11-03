<script>
  /**
   * Code Analysis dashboard — scorecards, model picker, horizontal issue tabs,
   * scrollable issue list, detailed mid pane, recommendations mapped to selection.
   */
  import { formatFriendlyError } from '../../analysisCatalog.js';
  import {
    DEFAULT_ISSUE_FILTER,
    DEFAULT_QUALITY_REPORT,
    ISSUE_FILTERS,
    buildReasoningModelOptions
  } from '../../codeQualityCatalog.js';
  import { getCachedModels, loadLlmHubModels } from '../../llmhubModels.js';
  import InfoToast from '../InfoToast.svelte';
  import OrthosLoader from '../OrthosLoader.svelte';

  let {
    activeSource = '',
    sourceType = 'local',
    catalogId = ''
  } = $props();

  const seed = getCachedModels();
  let modelOptions = $state(buildReasoningModelOptions(seed?.options ?? []));
  let selectedModel = $state(
    buildReasoningModelOptions(seed?.options ?? []).find((m) => m.recommended)?.id ||
      buildReasoningModelOptions(seed?.options ?? [])[0]?.id ||
      'fable-5.1'
  );
  let report = $state(structuredClone(DEFAULT_QUALITY_REPORT));
  let running = $state(false);
  let loadingCache = $state(false);
  /** @type {{ id: number, title: string, detail?: string, tone: 'info' | 'success' | 'warn' | 'error' } | null} */
  let toast = $state(null);
  let filter = $state(DEFAULT_ISSUE_FILTER);
  /** @type {string | null} */
  let selectedIssueId = $state(null);

  let hasAnalysis = $derived(Boolean(report?.ran_at));

  function showToast(title, { detail = '', tone = /** @type {'info'|'success'|'warn'|'error'} */ ('info') } = {}) {
    toast = { id: Date.now(), title, detail, tone };
  }

  function applyReport(data, { fromCache = false } = {}) {
    report = data && typeof data === 'object' ? data : structuredClone(DEFAULT_QUALITY_REPORT);
    filter = DEFAULT_ISSUE_FILTER;
    selectedIssueId = firstIssueIdForFilter(report.issues, DEFAULT_ISSUE_FILTER);
    if (fromCache) return;
    if (data?.design_guide?.active) {
      showToast('Code Analysis saved', {
        detail: `Cited design guide “${data.design_guide.filename}”. Replaces the previous run for this project.`,
        tone: 'success'
      });
    } else if (data?.cached) {
      showToast('Code Analysis saved with this project', {
        detail: 'Replaces the previous run.',
        tone: 'success'
      });
    }
  }

  function resetReport() {
    report = structuredClone(DEFAULT_QUALITY_REPORT);
    filter = DEFAULT_ISSUE_FILTER;
    selectedIssueId = null;
  }

  $effect(() => {
    let cancelled = false;
    loadLlmHubModels().then((cached) => {
      if (cancelled) return;
      modelOptions = buildReasoningModelOptions(cached.options);
      if (!modelOptions.some((m) => m.id === selectedModel)) {
        selectedModel =
          modelOptions.find((m) => m.recommended)?.id || modelOptions[0]?.id || selectedModel;
      }
    });
    return () => {
      cancelled = true;
    };
  });

  /** Load the latest cached report for the open catalog repo (same key as C4 diagrams). */
  $effect(() => {
    const source = activeSource.trim();
    const type = sourceType === 'github' ? 'github' : 'local';
    const entryId = (catalogId || '').trim();
    let cancelled = false;

    if (!source && !entryId) {
      resetReport();
      return;
    }

    loadingCache = true;
    const params = new URLSearchParams();
    if (entryId) params.set('catalog_id', entryId);
    if (source) {
      params.set('source', source);
      params.set('source_type', type);
    }

    fetch(`/api/analysis/quality?${params.toString()}`)
      .then(async (res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        if (cancelled) return;
        if (data?.cached && data.report) {
          applyReport(data.report, { fromCache: true });
        } else {
          resetReport();
        }
      })
      .catch(() => {
        if (!cancelled) resetReport();
      })
      .finally(() => {
        if (!cancelled) loadingCache = false;
      });

    return () => {
      cancelled = true;
    };
  });

  let filteredIssues = $derived.by(() => {
    const list = report.issues ?? [];
    if (filter === 'error') {
      return list.filter((i) => i.category === 'error' || i.severity === 'critical');
    }
    if (filter === 'optimize') {
      return list.filter((i) => i.category === 'optimize' || i.category === 'quality');
    }
    return list.filter((i) => i.category === filter);
  });

  let selectedIssue = $derived.by(() => {
    if (!filteredIssues.length) return null;
    return filteredIssues.find((i) => i.id === selectedIssueId) || filteredIssues[0];
  });

  /** Recommendations for the selected issue, including its primary fix text. */
  let relatedRecs = $derived.by(() => {
    if (!selectedIssue) return [];
    /** @type {{ id: string, title: string, detail: string, citation?: string }[]} */
    const out = [];
    if (selectedIssue.fix) {
      out.push({
        id: `${selectedIssue.id}-fix`,
        title: 'Recommended fix',
        detail: selectedIssue.fix
      });
    }
    const fromIssue = selectedIssue.recommendations || [];
    const mapped = fromIssue.length
      ? fromIssue
      : (report.recommendations || []).filter((r) => r.issue_id === selectedIssue.id);
    for (const rec of mapped) {
      if (!rec) continue;
      out.push(rec);
    }
    return out;
  });

  let cards = $derived([
    {
      key: 'bugs',
      filterId: 'bug',
      label: 'Bugs',
      value: hasAnalysis ? report.scorecards.bugs : 0,
      tip: 'Count of issues categorized as bug (plus security defects). Calculated from agent findings after supervisor merge.'
    },
    {
      key: 'fallacies',
      filterId: 'fallacy',
      label: 'Logical fallacies',
      value: hasAnalysis ? report.scorecards.logical_fallacies : 0,
      tip: 'Count of fallacy findings (nested ternaries, vacuous branches, deferred logic). From bugs/fallacies sub-agent + supervisor.'
    },
    {
      key: 'errors',
      filterId: 'error',
      label: 'Errors',
      value: hasAnalysis ? report.scorecards.errors : 0,
      tip: 'Count of error-category issues plus any critical-severity findings across factors.'
    },
    {
      key: 'security',
      filterId: 'security',
      label: 'Security score',
      value: `${hasAnalysis ? report.scorecards.security_score : 0}/100`,
      tip: '0–100 (100 best). Starts at 100 after a run; minus ~12 per security issue, ~8 per open-endpoint risk, and extra weight for critical severity. Shows 0 before any analysis.'
    },
    {
      key: 'quality',
      filterId: 'quality',
      label: 'Quality',
      value: `${hasAnalysis ? report.scorecards.quality_score : 0}/100`,
      tip: '0–100 (100 best). Starts at 100 after a run; minus ~6 per quality/fallacy issue and ~4 per bug. Shows 0 before any analysis.'
    },
    {
      key: 'vulns',
      filterId: 'security',
      label: 'Vulnerabilities',
      value: hasAnalysis ? report.scorecards.vulnerability_count : 0,
      tip: 'Count of security-category issues (injection sinks, unsafe eval/HTML, etc.) after supervisor dedupe.'
    },
    {
      key: 'memory',
      filterId: 'memory',
      label: 'Memory risk points',
      value: hasAnalysis ? report.scorecards.memory_risk_points : 0,
      tip: 'Count of memory-category findings (unbounded caches, listener leaks, growth risks) from the memory sub-agent.'
    },
    {
      key: 'endpoints',
      filterId: 'endpoint',
      label: 'Open endpoint risks',
      value: hasAnalysis ? report.scorecards.open_endpoint_risks : 0,
      tip: 'Count of endpoint findings that may lack auth or be openly injectable, from the endpoint sub-agent.'
    }
  ]);

  function focusIssueTab(nextFilter) {
    filter = nextFilter;
    selectedIssueId = firstIssueIdForFilter(report.issues, nextFilter);
  }

  function onScorecardClick(card) {
    if (!card?.filterId) return;
    focusIssueTab(card.filterId);
  }

  function firstIssueIdForFilter(issues, nextFilter) {
    const list = issues || [];
    let matched = list;
    if (nextFilter === 'error') {
      matched = list.filter((i) => i.category === 'error' || i.severity === 'critical');
    } else if (nextFilter === 'optimize') {
      matched = list.filter((i) => i.category === 'optimize' || i.category === 'quality');
    } else {
      matched = list.filter((i) => i.category === nextFilter);
    }
    return matched[0]?.id ?? null;
  }

  async function runAnalysis() {
    notice = '';
    running = true;
    const targetSource = activeSource.trim() || '..';
    const type = sourceType === 'github' ? 'github' : 'local';
    try {
      const res = await fetch('/api/analysis/quality', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source: targetSource,
          source_type: type,
          catalog_id: (catalogId || '').trim() || null,
          model: selectedModel
        })
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      applyReport(data, { fromCache: false });
    } catch (err) {
      showToast('Code Analysis failed', {
        detail: formatFriendlyError(err, 'Code Analysis'),
        tone: 'error'
      });
    } finally {
      running = false;
    }
  }
</script>

<div class="cq">
  {#if running}
    <div class="cq-loader" role="status" aria-live="polite">
      <OrthosLoader label="Running Code Analysis agents…" />
    </div>
  {:else if loadingCache}
    <div class="cq-loader cq-loader--soft" role="status" aria-live="polite">
      <OrthosLoader label="Loading cached Code Analysis…" />
    </div>
  {/if}

  {#if toast}
    {#key toast.id}
      <InfoToast
        title={toast.title}
        detail={toast.detail || ''}
        tone={toast.tone}
        durationSec={8}
        onClose={() => (toast = null)}
      />
    {/key}
  {/if}

  <header class="cq-toolbar">
    <div class="cq-toolbar__controls">
      <label class="cq-field" for="cq-model">
        <span class="cq-field__label">LLMHub model</span>
        <select id="cq-model" class="cq-control" bind:value={selectedModel} disabled={running}>
          {#each modelOptions as m (m.id)}
            <option value={m.id}>{m.label}</option>
          {/each}
        </select>
      </label>
      <button type="button" class="cq-control cq-run" disabled={running} onclick={runAnalysis}>
        {running ? 'Running agents…' : 'Run code analysis'}
      </button>
    </div>
  </header>

  <section class="cq-scorecards" aria-label="Code quality scorecards">
    {#each cards as card (card.key)}
      <article
        class="cq-card"
        class:active={filter === card.filterId}
        role="button"
        tabindex="0"
        aria-pressed={filter === card.filterId}
        aria-controls="cq-issue-tabs"
        title={`Show ${card.label} issues`}
        onclick={() => onScorecardClick(card)}
        onkeydown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onScorecardClick(card);
          }
        }}
      >
        <div class="cq-card__head">
          <span class="cq-card__label">
            {card.label}
            <span
              class="cq-card__info"
              tabindex="0"
              role="img"
              aria-label={card.tip}
              data-tip={card.tip}
              onclick={(e) => e.stopPropagation()}
              onkeydown={(e) => e.stopPropagation()}
            >i</span>
          </span>
        </div>
        <strong class="cq-card__value">{card.value}</strong>
      </article>
    {/each}
  </section>

  <div class="cq-status" aria-label="Analysis pipelines">
    {#each Object.entries(report.analyses || {}) as [name, status] (name)}
      <span class="cq-chip" data-status={status}>{name.replaceAll('_', ' ')} · {status}</span>
    {/each}
    {#if report.ran_at}
      <span class="cq-chip cq-chip--muted">
        {report.files_scanned ?? 0} files · model {report.model} · {new Date(report.ran_at).toLocaleString()}
      </span>
    {/if}
  </div>

  <div id="cq-issue-tabs" class="cq-filter-tabs" role="tablist" aria-label="Issue category tabs">
    {#each ISSUE_FILTERS as f (f.id)}
      <button
        type="button"
        role="tab"
        class="cq-tab"
        class:active={filter === f.id}
        aria-selected={filter === f.id}
        onclick={() => focusIssueTab(f.id)}
      >
        {f.label}
      </button>
    {/each}
  </div>

  <section class="cq-panels" aria-label="Issues, detail, and recommendations">
    <aside class="cq-left" aria-label="Issue list">
      <h2>Issues <span class="cq-count">{filteredIssues.length}</span></h2>
      <ul class="cq-issue-list">
        {#each filteredIssues as issue (issue.id)}
          <li>
            <button
              type="button"
              class="cq-issue"
              class:active={selectedIssue?.id === issue.id}
              onclick={() => (selectedIssueId = issue.id)}
            >
              <span class="cq-issue__sev" data-sev={issue.severity}>{issue.severity}</span>
              <span class="cq-issue__title">{issue.title}</span>
              <span class="cq-issue__cat">{issue.category}</span>
            </button>
          </li>
        {:else}
          <li class="cq-empty">Run analysis to list errors, bugs, and logical fallacies.</li>
        {/each}
      </ul>
    </aside>

    <main class="cq-mid" aria-label="Issue detail">
      {#if selectedIssue}
        <h2>{selectedIssue.title}</h2>
        <p class="cq-meta">
          <span>{selectedIssue.category}</span>
          <span>{selectedIssue.severity}</span>
          <code>{selectedIssue.evidence}</code>
        </p>

        <section class="cq-explain">
          <h3>What is the problem?</h3>
          <p>{selectedIssue.problem || selectedIssue.detail}</p>
        </section>

        <section class="cq-explain">
          <h3>Why is this an issue?</h3>
          <p>{selectedIssue.why || selectedIssue.detail}</p>
        </section>

        <section class="cq-explain">
          <h3>Impact if left unfixed</h3>
          <p>
            {selectedIssue.impact ||
              'Raises defect, security, or maintainability risk in production.'}
          </p>
        </section>

        <section class="cq-explain" aria-label="Recommendations">
          <h3>Recommendations</h3>
          <ul class="cq-rec-list">
            {#each relatedRecs as rec (rec.id)}
              <li class="cq-rec">
                <strong>{rec.title}</strong>
                <p>{rec.detail}</p>
                {#if rec.citation}
                  <p class="cq-rec__cite">Cite: {rec.citation}</p>
                {/if}
              </li>
            {:else}
              <li class="cq-empty">No mapped recommendations for this issue.</li>
            {/each}
          </ul>
        </section>

        {#if selectedIssue.design_guide?.filename}
          <section class="cq-explain cq-explain--guide">
            <h3>Design guide citation</h3>
            <p>
              Bible: <strong>{selectedIssue.design_guide.filename}</strong>
            </p>
            {#if selectedIssue.design_guide.citations?.length}
              <ul>
                {#each selectedIssue.design_guide.citations as cite}
                  <li>{cite}</li>
                {/each}
              </ul>
            {/if}
          </section>
        {/if}
      {:else}
        <div class="cq-empty-panel">
          <h2>Detail</h2>
          <p>Select an issue on the left, or run code analysis to populate findings.</p>
        </div>
      {/if}
    </main>
  </section>
</div>

<style>
  .cq {
    position: relative;
    display: flex;
    flex-direction: column;
    gap: 12px;
    height: 100%;
    min-height: 0;
    padding: 16px 20px 20px;
    overflow: hidden;
    background: linear-gradient(180deg, #f7fbff 0%, var(--surface-muted) 40%, var(--canvas-bg) 100%);
  }

  .cq-loader {
    position: absolute;
    inset: 0;
    z-index: 20;
    display: grid;
    place-items: center;
    background: color-mix(in srgb, var(--canvas-bg) 72%, transparent);
    backdrop-filter: blur(2px);
  }

  .cq-loader--soft {
    background: color-mix(in srgb, var(--canvas-bg) 55%, transparent);
  }

  .cq-toolbar {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    align-items: center;
    flex-shrink: 0;
  }

  .cq-toolbar__controls {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    align-items: center;
  }

  .cq-field {
    display: inline-flex;
    flex-direction: row;
    align-items: center;
    gap: 8px;
    margin: 0;
  }

  .cq-field__label {
    font-size: 0.78rem;
    font-weight: 650;
    color: var(--text-muted);
    white-space: nowrap;
  }

  .cq-control {
    box-sizing: border-box;
    height: 40px;
    min-height: 40px;
    padding: 0 14px;
    border: 1px solid var(--border-strong);
    border-radius: 8px;
    font-size: 0.875rem;
    line-height: 1;
    font-family: inherit;
  }

  .cq-field select.cq-control {
    min-width: 240px;
    background: var(--surface);
    color: var(--text);
  }

  .cq-run {
    border-color: var(--pfizer-blue-70);
    background: var(--pfizer-blue-70);
    color: #fff;
    font-weight: 700;
    cursor: pointer;
  }

  .cq-run:disabled {
    opacity: 0.65;
    cursor: wait;
  }

  .cq-scorecards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 10px;
    flex-shrink: 0;
    align-items: stretch;
    overflow: visible;
    z-index: 2;
  }

  .cq-card {
    min-height: 92px;
    padding: 12px 14px;
    border-radius: 10px;
    border: 1px solid var(--border);
    background: var(--surface);
    box-shadow: var(--shadow-sm);
    display: flex;
    flex-direction: column;
    gap: 8px;
    cursor: pointer;
    transition: border-color 0.12s ease, box-shadow 0.12s ease;
  }

  .cq-card:hover {
    border-color: var(--blue-200);
  }

  .cq-card:focus-visible {
    outline: 2px solid var(--pfizer-cyan-50);
    outline-offset: 2px;
  }

  .cq-card.active {
    border-color: var(--pfizer-cyan-50);
    box-shadow: 0 0 0 1px color-mix(in srgb, var(--pfizer-cyan-50) 35%, transparent);
  }

  .cq-card__head {
    display: flex;
    align-items: flex-start;
    min-height: 28px;
  }

  .cq-card__label {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 0.72rem;
    font-weight: 650;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.03em;
    line-height: 1.25;
  }

  .cq-card__info {
    position: relative;
    flex: 0 0 auto;
    display: inline-grid;
    place-items: center;
    width: 12px;
    height: 12px;
    border-radius: 999px;
    border: 1px solid currentColor;
    background: transparent;
    color: #1f2937;
    font-size: 8px;
    font-weight: 700;
    font-style: normal;
    font-family: var(--sans);
    line-height: 1;
    text-transform: none;
    letter-spacing: 0;
    cursor: help;
    padding: 0;
  }

  .cq-card__info::after {
    content: attr(data-tip);
    position: absolute;
    left: 0;
    top: calc(100% + 6px);
    width: max-content;
    max-width: 220px;
    padding: 8px 10px;
    border-radius: 8px;
    border: 1px solid var(--border-strong);
    background: #0f172a;
    color: #f8fafc;
    font-size: 11px;
    font-weight: 500;
    line-height: 1.35;
    text-transform: none;
    letter-spacing: 0;
    white-space: normal;
    box-shadow: var(--shadow-md);
    opacity: 0;
    visibility: hidden;
    pointer-events: none;
    transition: opacity 0.12s ease;
    z-index: 40;
  }

  .cq-card__info:hover::after,
  .cq-card__info:focus-visible::after {
    opacity: 1;
    visibility: visible;
  }

  .cq-card__value {
    margin-top: auto;
    min-height: 1.6em;
    font-size: 1.35rem;
    line-height: 1.2;
    color: var(--pfizer-blue-90);
    display: flex;
    align-items: flex-end;
  }

  .cq-status {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    flex-shrink: 0;
  }

  .cq-chip {
    font-size: 0.72rem;
    padding: 4px 8px;
    border-radius: 999px;
    border: 1px solid var(--border);
    background: var(--surface);
    text-transform: capitalize;
  }

  .cq-chip[data-status='complete'] {
    border-color: #86efac;
    background: #f0fdf4;
  }

  .cq-chip--muted {
    color: var(--text-muted);
  }

  .cq-filter-tabs {
    display: flex;
    flex-wrap: nowrap;
    gap: 6px;
    overflow-x: auto;
    padding-bottom: 2px;
    flex-shrink: 0;
    border-bottom: 1px solid var(--border);
  }

  .cq-tab {
    flex: 0 0 auto;
    border: 1px solid transparent;
    border-bottom: 2px solid transparent;
    border-radius: 8px 8px 0 0;
    background: transparent;
    padding: 8px 12px;
    font-size: 0.8rem;
    color: var(--text-muted);
    cursor: pointer;
    white-space: nowrap;
  }

  .cq-tab.active {
    color: var(--pfizer-blue-90);
    font-weight: 700;
    background: var(--blue-50);
    border-color: var(--blue-200);
    border-bottom-color: var(--pfizer-cyan-50);
  }

  .cq-panels {
    display: grid;
    grid-template-columns: minmax(200px, 28%) minmax(0, 72%);
    gap: 12px;
    flex: 1 1 auto;
    min-height: 280px;
    max-height: 100%;
    overflow: hidden;
  }

  .cq-left,
  .cq-mid {
    border: 1px solid var(--border);
    border-radius: 12px;
    background: var(--surface);
    padding: 12px;
    min-height: 0;
    max-height: 100%;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .cq-left h2,
  .cq-mid h2 {
    font-size: 0.95rem;
    margin: 0 0 8px;
    flex-shrink: 0;
  }

  .cq-count {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text-muted);
  }

  .cq-mid h3 {
    font-size: 0.85rem;
    margin: 0 0 6px;
  }

  .cq-issue-list {
    list-style: none;
    margin: 0;
    padding: 0 4px 0 0;
    display: flex;
    flex-direction: column;
    gap: 6px;
    overflow-y: auto;
    overflow-x: hidden;
    flex: 1 1 auto;
    min-height: 0;
    max-height: 100%;
    overscroll-behavior: contain;
    scrollbar-gutter: stable;
  }

  .cq-rec-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .cq-issue-list::-webkit-scrollbar,
  .cq-mid::-webkit-scrollbar {
    width: 8px;
  }

  .cq-issue-list::-webkit-scrollbar-thumb,
  .cq-mid::-webkit-scrollbar-thumb {
    background: var(--border-strong);
    border-radius: 999px;
  }

  .cq-mid {
    overflow-y: auto;
    overflow-x: hidden;
    scrollbar-gutter: stable;
  }

  .cq-issue {
    width: 100%;
    text-align: left;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: #ffffff;
    padding: 8px;
    cursor: pointer;
    display: grid;
    gap: 4px;
  }

  .cq-issue.active {
    background: #ffffff;
    border-color: var(--pfizer-cyan-50);
    box-shadow: 0 0 0 1px color-mix(in srgb, var(--pfizer-cyan-50) 35%, transparent);
  }

  .cq-issue__sev {
    font-size: 0.65rem;
    text-transform: uppercase;
    font-weight: 700;
    color: var(--text-muted);
  }

  .cq-issue__sev[data-sev='critical'] {
    color: #b91c1c;
  }
  .cq-issue__sev[data-sev='major'] {
    color: #c2410c;
  }

  .cq-issue__title {
    font-size: 0.8rem;
    font-weight: 650;
    color: var(--text);
  }

  .cq-issue__cat {
    font-size: 0.7rem;
    color: var(--text-muted);
    text-transform: capitalize;
  }

  .cq-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    font-size: 0.8rem;
    color: var(--text-muted);
    margin: 0 0 12px;
  }

  .cq-meta code {
    font-family: var(--mono);
    font-size: 0.75rem;
  }

  .cq-explain {
    margin-bottom: 14px;
  }

  .cq-explain p {
    margin: 0;
    font-size: 0.9rem;
    line-height: 1.45;
    color: var(--text);
  }

  .cq-explain--guide {
    padding: 10px;
    border-radius: 8px;
    background: var(--blue-50);
    border: 1px solid var(--blue-200);
  }

  .cq-explain--guide ul {
    margin: 6px 0 0;
    padding-left: 1.1rem;
    font-size: 0.82rem;
  }

  .cq-rec {
    padding: 10px;
    border-radius: 8px;
    border: 1px solid var(--border);
    background: var(--surface-muted);
  }

  .cq-rec strong {
    display: block;
    font-size: 0.82rem;
    margin-bottom: 4px;
  }

  .cq-rec p {
    margin: 0;
    font-size: 0.78rem;
    color: var(--text-muted);
  }

  .cq-rec__cite {
    margin-top: 6px !important;
    font-style: italic;
  }

  .cq-empty,
  .cq-empty-panel {
    color: var(--text-muted);
    font-size: 0.85rem;
  }

  @media (max-width: 960px) {
    .cq {
      overflow: auto;
    }
    .cq-panels {
      grid-template-columns: 1fr;
      min-height: 720px;
    }
    .cq-left,
    .cq-mid {
      max-height: 420px;
    }
  }
</style>
