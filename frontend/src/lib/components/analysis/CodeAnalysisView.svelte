<script>
  /**
   * Code Analysis Tab Workspace (`CodeAnalysisView.svelte`).
   * Implements:
   * - All 10 Must-Have Coding Agent Skills (2026 Medium guide by @unicodeveloper) + 7 Core C4 Skills
   * - Adapted with `~/.claude/skills/ui-ux-master` & `~/.claude/skills/ui-experience`
   * - Two docked collapsible sidebars (Principle 2), hybrid combobox search (Principle 5 & L1),
   *   data-first defaults (Principle 9-11), view filter dropdown preserving selections (Principle 8 & 12),
   *   shared friendly error helper (Lesson L4), and native `<dialog>` modal (Principle 3 & S6819).
   */
  import {
    ADAPTED_SKILLS_CATALOG,
    ANALYSIS_VIEWS,
    DEFAULT_ANALYSIS_REPORT,
    formatFriendlyError,
    getSeverityMeta
  } from '../../analysisCatalog.js';
  import SkillSidebarLeft from './SkillSidebarLeft.svelte';
  import AnalysisInspectorRight from './AnalysisInspectorRight.svelte';
  import SkillDetailModal from './SkillDetailModal.svelte';

  let { activeSource = '' } = $props();

  // Data-first defaults (Principle 9, 10, 11): land on most-used view with #1 skill selected
  let activeView = $state('playbooks');
  let selectedSkillId = $state('frontend-design');
  let searchQuery = $state('');
  let originFilter = $state('all');
  let severityFilter = $state('all');
  let metricTagFilter = $state('all');

  let leftCollapsed = $state(false);
  let rightCollapsed = $state(false);
  let modalOpen = $state(false);

  let report = $state(DEFAULT_ANALYSIS_REPORT);
  let runningAudit = $state(false);
  let friendlyNotice = $state('');

  let filteredSkills = $derived.by(() => {
    const q = searchQuery.trim().toLowerCase();
    return ADAPTED_SKILLS_CATALOG.filter((item) => {
      if (originFilter !== 'all' && item.category !== originFilter) return false;
      if (!q) return true;
      const haystack = `${item.name} ${item.skill_id} ${item.slash_command} ${item.kindBadge} ${item.subtitle}`.toLowerCase();
      return haystack.includes(q);
    });
  });

  let selectedSkill = $derived(
    ADAPTED_SKILLS_CATALOG.find((s) => s.skill_id === selectedSkillId) ?? ADAPTED_SKILLS_CATALOG[0]
  );

  let filteredFindings = $derived.by(() => {
    const list = report.findings ?? [];
    if (severityFilter === 'quick-wins') {
      return list.filter((f) => f.severity >= 3 && f.effort === 'S');
    }
    if (severityFilter === 'verified') {
      return list.filter((f) => f.severity === 0);
    }
    return list;
  });

  let filteredScorecard = $derived.by(() => {
    const list = report.scorecard ?? [];
    if (metricTagFilter === 'all') return list;
    return list.filter((row) => row.tag === metricTagFilter);
  });

  async function runLiveCodeAudit() {
    friendlyNotice = '';
    runningAudit = true;
    const targetSource = activeSource.trim() || '..';
    try {
      const res = await fetch('/api/analysis/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: targetSource })
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const data = await res.json();
      report = data;
    } catch (err) {
      friendlyNotice = formatFriendlyError(err, 'Live Code & UX Analysis');
    } finally {
      runningAudit = false;
    }
  }
</script>

<div class="analysis-layout">
  <SkillSidebarLeft
    skills={filteredSkills}
    {selectedSkillId}
    {searchQuery}
    {originFilter}
    collapsed={leftCollapsed}
    onSelectSkill={(id) => (selectedSkillId = id)}
    onSearchChange={(q) => (searchQuery = q)}
    onOriginChange={(origin) => (originFilter = origin)}
    onToggleCollapse={() => (leftCollapsed = !leftCollapsed)}
  />

  <section class="analysis-center" aria-label="Code and UI/UX Analysis Workspace">
    <header class="analysis-bar">
      <div class="analysis-bar__left">
        <label class="analysis-bar__label" for="analysis-view-select">View:</label>
        <select
          id="analysis-view-select"
          class="analysis-bar__select"
          bind:value={activeView}
        >
          {#each ANALYSIS_VIEWS as v (v.id)}
            <option value={v.id}>{v.label}</option>
          {/each}
        </select>
      </div>

      <div class="analysis-bar__kpis" aria-label="Composite evaluation metrics">
        <output class="kpi-pill">
          C4 Score: <strong>{report.composite_scores.composite_architecture_score}/100 [measured]</strong>
        </output>
        <output class="kpi-pill">
          Quick Wins: <strong>{report.composite_scores.quick_win_count} [measured]</strong>
        </output>
        <output class="kpi-pill">
          SUS: <strong>{report.composite_scores.projected_sus_range}</strong>
        </output>
      </div>

      <div class="analysis-bar__actions">
        <button
          type="button"
          class="btn-secondary"
          onclick={() => (modalOpen = true)}
        >
          Playbook Modal
        </button>
        <button
          type="button"
          class="btn-primary"
          disabled={runningAudit}
          onclick={runLiveCodeAudit}
        >
          {runningAudit ? 'Auditing…' : 'Run Live Audit'}
        </button>
      </div>
    </header>

    {#if friendlyNotice}
      <output class="friendly-notice">{friendlyNotice}</output>
    {/if}

    <div class="analysis-scroll">
      <!-- 2-Minute Verdict-First Executive Summary (ui-experience L10 & ui-ux-master §6) -->
      <article class="verdict-banner" aria-label="Executive summary">
        <div class="verdict-banner__top">
          <span class="verdict-banner__tag">2-Min Verdict-First Executive Summary (ui-ux-master & ui-experience L10)</span>
          <span class="verdict-banner__repo">Target: <code>{report.repo_name}</code></span>
        </div>
        <p class="verdict-banner__text">{report.executive_summary}</p>
      </article>

      {#if activeView === 'playbooks'}
        <!-- Selected Skill In-Place Columnar Detail (Principle 14) -->
        <article class="skill-detail-card" aria-label="Selected skill details">
          <header class="skill-detail-card__head">
            <div>
              <span class="skill-detail-card__eyebrow">
                Skill #{selectedSkill.rank} · {selectedSkill.kindBadge} · <code>{selectedSkill.skill_markdown_path}</code>
              </span>
              <h2 class="skill-detail-card__title">
                {selectedSkill.name} (<code>{selectedSkill.slash_command}</code>)
              </h2>
            </div>
            <button
              type="button"
              class="btn-secondary"
              onclick={() => (modalOpen = true)}
            >
              Inspect Full SKILL.md (Modal)
            </button>
          </header>

          <p class="skill-detail-card__desc">{selectedSkill.problemSolved}</p>

          <div class="adaptation-cols">
            <div class="adaptation-box">
              <h3>Adapted with <code>~/.claude/skills/ui-ux-master</code></h3>
              <p>{selectedSkill.uiUxMasterRule}</p>
            </div>
            <div class="adaptation-box">
              <h3>Adapted with <code>~/.claude/skills/ui-experience</code></h3>
              <p>{selectedSkill.uiExperienceRule}</p>
            </div>
          </div>

          <div class="skill-detail-card__meta">
            <span><strong>Install:</strong> <code>{selectedSkill.install_command}</code></span>
            <span><strong>Code Evidence:</strong> <code>{selectedSkill.codeEvidence}</code></span>
          </div>
        </article>

        <!-- Prioritized Code & UX Findings (Quick Wins First) -->
        <section class="findings-section" aria-label="Prioritized code and UX findings">
          <div class="section-head">
            <h2>Prioritized Code & UI/UX Findings (Quick Wins Ranked First)</h2>
            <output class="count-chip">{filteredFindings.length} findings</output>
          </div>

          <div class="findings-list">
            {#each filteredFindings as finding (finding.id)}
              {@const sevMeta = getSeverityMeta(finding.severity)}
              <article class="finding-card">
                <header class="finding-card__top">
                  <span class="finding-card__id">{finding.id}</span>
                  <h3 class="finding-card__title">{finding.title}</h3>
                  {#if finding.is_quick_win}
                    <span class="quick-win-badge">Quick Win (Sev ≥ 3 · Effort S)</span>
                  {/if}
                  <span class="sev-badge sev-badge--{sevMeta.tone}">{sevMeta.label}</span>
                </header>
                <p class="finding-card__issue"><strong>Issue:</strong> {finding.issue}</p>
                <div class="finding-card__grid">
                  <div><strong>Evidence:</strong> <code>{finding.evidence}</code></div>
                  <div><strong>Skill & Standard:</strong> {finding.skill_badge} · {finding.standard_violated}</div>
                  <div><strong>Concrete Fix (Effort {finding.effort}):</strong> {finding.fix}</div>
                  <div><strong>Expected Impact:</strong> {finding.expected_impact}</div>
                </div>
              </article>
            {/each}
          </div>
        </section>
      {:else if activeView === 'scorecard'}
        <section class="scorecard-section" aria-label="Dual-Audience UI/UX Master Scorecard">
          <div class="section-head">
            <h2>UI/UX Master Dual-Audience Scorecard ([measured] vs [projected])</h2>
            <output class="count-chip">{filteredScorecard.length} metrics</output>
          </div>
          <div class="scorecard-list">
            {#each filteredScorecard as row (row.section)}
              <article class="scorecard-row">
                <div class="scorecard-row__head">
                  <h3>{row.section}</h3>
                  <span class="tag-pill tag-pill--{row.tag}">[{row.tag}]</span>
                </div>
                <p class="scorecard-row__val">{row.value}</p>
                <p class="scorecard-row__line"><strong>Business:</strong> {row.business}</p>
                <p class="scorecard-row__line"><strong>Tech:</strong> {row.tech}</p>
                <p class="scorecard-row__plan"><strong>Measurement Plan:</strong> {row.measurement_plan}</p>
              </article>
            {/each}
          </div>
        </section>
      {:else}
        <section class="scorecard-section" aria-label="All 17 Adapted Skills Matrix">
          <div class="section-head">
            <h2>All 17 Coding Agent Skills — UI/UX Master & UI-Experience Matrix</h2>
            <output class="count-chip">{filteredSkills.length} skills</output>
          </div>
          <div class="scorecard-list">
            {#each filteredSkills as item (item.uid)}
              <article class="scorecard-row">
                <div class="scorecard-row__head">
                  <h3>#{item.rank} · {item.name} (<code>{item.slash_command}</code>)</h3>
                  <button
                    type="button"
                    class="btn-secondary"
                    onclick={() => {
                      selectedSkillId = item.skill_id;
                      modalOpen = true;
                    }}
                  >
                    Open Playbook
                  </button>
                </div>
                <p class="scorecard-row__line"><strong>Install:</strong> <code>{item.install_command}</code></p>
                <p class="scorecard-row__line"><strong>ui-ux-master:</strong> {item.uiUxMasterRule}</p>
                <p class="scorecard-row__line"><strong>ui-experience:</strong> {item.uiExperienceRule}</p>
              </article>
            {/each}
          </div>
        </section>
      {/if}
    </div>
  </section>

  <AnalysisInspectorRight
    {severityFilter}
    {metricTagFilter}
    collapsed={rightCollapsed}
    onSeverityChange={(v) => (severityFilter = v)}
    onMetricTagChange={(v) => (metricTagFilter = v)}
    onToggleCollapse={() => (rightCollapsed = !rightCollapsed)}
    onOpenSkillModal={() => (modalOpen = true)}
  />
</div>

<SkillDetailModal
  open={modalOpen}
  skill={selectedSkill}
  onClose={() => (modalOpen = false)}
/>

<style>
  .analysis-layout {
    flex: 1;
    min-height: 0;
    display: flex;
    gap: 14px;
    padding: 14px 24px 18px;
  }

  .analysis-center {
    flex: 1;
    min-width: 0;
    min-height: 0;
    display: flex;
    flex-direction: column;
    background: var(--canvas-bg);
    border: 1px solid var(--border);
    border-radius: 14px;
    box-shadow: var(--shadow-sm);
    overflow: hidden;
  }

  .analysis-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 8px 14px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    flex-wrap: wrap;
  }

  .analysis-bar__left,
  .analysis-bar__kpis,
  .analysis-bar__actions {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .analysis-bar__label {
    font-size: 11.5px;
    font-weight: 700;
    color: var(--text-muted);
  }

  .analysis-bar__select {
    padding: 5px 10px;
    border-radius: 8px;
    border: 1.5px solid var(--border-strong);
    background: var(--surface);
    font-size: 12.5px;
    font-weight: 700;
    color: var(--text);
    cursor: pointer;
  }

  .kpi-pill {
    font-size: 11.5px;
    padding: 3px 9px;
    border-radius: 999px;
    background: var(--surface-muted);
    border: 1px solid var(--border);
    color: var(--text-muted);
  }

  .kpi-pill strong {
    color: var(--blue-700);
  }

  .btn-primary {
    padding: 6px 14px;
    border: none;
    border-radius: 8px;
    background: var(--blue-700);
    color: #ffffff;
    font-size: 12.5px;
    font-weight: 700;
    cursor: pointer;
  }

  .btn-secondary {
    padding: 5px 11px;
    border-radius: 8px;
    border: 1px solid var(--border-strong);
    background: var(--surface);
    color: var(--blue-700);
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
  }

  .friendly-notice {
    margin: 8px 14px 0;
    padding: 8px 12px;
    border-radius: 9px;
    background: var(--blue-50);
    border: 1px solid var(--blue-200);
    color: var(--blue-900);
    font-size: 12px;
  }

  .analysis-scroll {
    flex: 1;
    overflow-y: auto;
    padding: 14px;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .verdict-banner {
    padding: 12px 14px;
    border-radius: 12px;
    background: var(--blue-50);
    border: 1px solid var(--blue-200);
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .verdict-banner__top {
    display: flex;
    justify-content: space-between;
    gap: 8px;
    font-size: 11px;
    font-weight: 700;
    color: var(--blue-700);
    text-transform: uppercase;
  }

  .verdict-banner__text {
    font-size: 12.5px;
    line-height: 1.5;
    color: var(--blue-900);
  }

  .skill-detail-card,
  .finding-card,
  .scorecard-row {
    padding: 14px;
    border-radius: 12px;
    background: var(--surface);
    border: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .skill-detail-card__head,
  .section-head,
  .scorecard-row__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
  }

  .skill-detail-card__eyebrow {
    font-size: 11px;
    font-weight: 700;
    color: var(--blue-700);
  }

  .skill-detail-card__title,
  .section-head h2 {
    font-size: 15px;
    font-weight: 700;
  }

  .skill-detail-card__desc {
    font-size: 13px;
    color: var(--text);
  }

  .adaptation-cols,
  .finding-card__grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 10px;
    font-size: 12.5px;
  }

  .adaptation-box {
    padding: 10px 12px;
    border-radius: 10px;
    background: var(--surface-muted);
    border: 1px solid var(--border);
  }

  .adaptation-box h3 {
    font-size: 12px;
    color: var(--blue-700);
    margin-bottom: 4px;
  }

  .skill-detail-card__meta {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    gap: 8px;
    font-size: 12px;
    color: var(--text-muted);
    padding-top: 6px;
    border-top: 1px solid var(--border);
  }

  .findings-list,
  .scorecard-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .finding-card__top {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  .finding-card__id {
    font-family: var(--mono);
    font-weight: 700;
    color: var(--blue-700);
  }

  .finding-card__title {
    font-size: 13.5px;
    font-weight: 700;
    flex: 1;
  }

  .quick-win-badge,
  .sev-badge,
  .tag-pill,
  .count-chip {
    font-size: 11px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 999px;
    background: var(--blue-50);
    color: var(--blue-700);
    border: 1px solid var(--blue-200);
  }
</style>
