<script>
  /**
   * Right Docked Collapsible Sidebar (`ui-experience` Principle 2 & Lesson L5).
   * - Attribute & severity facet filters (Quick Wins, Severity, Metric Tag [measured]/[projected])
   * - Live Cross-Cutting Checklist verification (`ui-experience` Lesson L5)
   * - Zero nested ternaries (SonarQube S3358)
   */
  import { CROSS_CUTTING_CHECKLIST } from '../../analysisCatalog.js';

  let {
    severityFilter = 'all',
    metricTagFilter = 'all',
    collapsed = false,
    onSeverityChange,
    onMetricTagChange,
    onToggleCollapse,
    onOpenSkillModal
  } = $props();

  let toggleAriaLabel = $derived(
    collapsed ? 'Expand attribute & checklist sidebar' : 'Collapse attribute & checklist sidebar'
  );
  let toggleGlyph = $derived(collapsed ? '«' : '»');
</script>

<aside class="inspector-right" class:collapsed aria-label="Attribute filters and UX checklist">
  <div class="inspector-right__bar">
    <button
      type="button"
      class="inspector-right__toggle"
      aria-expanded={!collapsed}
      aria-controls="inspector-right-body"
      aria-label={toggleAriaLabel}
      onclick={() => onToggleCollapse?.()}
    >
      {toggleGlyph}
    </button>
    {#if !collapsed}
      <div class="inspector-right__heading">
        <span class="inspector-right__eyebrow">Right Attribute Dock</span>
        <span class="inspector-right__title">Standards & Facets</span>
      </div>
    {/if}
  </div>

  <div id="inspector-right-body" class="inspector-right__body" hidden={collapsed}>
    <section class="facet-card">
      <h3>Finding Severity Facet (NN/g 0–4)</h3>
      <div class="facet-buttons" role="group" aria-label="Filter findings by severity">
        <button
          type="button"
          class="facet-btn"
          class:active={severityFilter === 'all'}
          onclick={() => onSeverityChange?.('all')}
        >
          All Findings
        </button>
        <button
          type="button"
          class="facet-btn"
          class:active={severityFilter === 'quick-wins'}
          onclick={() => onSeverityChange?.('quick-wins')}
        >
          Quick Wins (Sev ≥ 3 · Effort S)
        </button>
        <button
          type="button"
          class="facet-btn"
          class:active={severityFilter === 'verified'}
          onclick={() => onSeverityChange?.('verified')}
        >
          Verified Passes (Sev 0)
        </button>
      </div>
    </section>

    <section class="facet-card">
      <h3>Metric Honesty Tag (ui-ux-master §5)</h3>
      <div class="facet-buttons" role="group" aria-label="Filter scorecard by metric tag">
        <button
          type="button"
          class="facet-btn"
          class:active={metricTagFilter === 'all'}
          onclick={() => onMetricTagChange?.('all')}
        >
          All Metrics
        </button>
        <button
          type="button"
          class="facet-btn"
          class:active={metricTagFilter === 'measured'}
          onclick={() => onMetricTagChange?.('measured')}
        >
          [measured] (From Static Code / Sandbox)
        </button>
        <button
          type="button"
          class="facet-btn"
          class:active={metricTagFilter === 'projected'}
          onclick={() => onMetricTagChange?.('projected')}
        >
          [projected] (Needs Live User Test)
        </button>
      </div>
    </section>

    <section class="facet-card">
      <h3>Cross-Cutting Checklist (Lesson L5)</h3>
      <ul class="checklist">
        {#each CROSS_CUTTING_CHECKLIST as item (item.id)}
          <li class="checklist__item">
            <span class="checklist__check" aria-hidden="true">✓</span>
            <div class="checklist__text">
              <strong>{item.rule}</strong>
              <span>{item.status}</span>
            </div>
          </li>
        {/each}
      </ul>
    </section>

    <button
      type="button"
      class="inspect-modal-btn"
      onclick={() => onOpenSkillModal?.()}
    >
      Open Selected Skill Playbook Modal (90% View)
    </button>
  </div>
</aside>

<style>
  .inspector-right {
    width: 310px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    min-height: 0;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    box-shadow: var(--shadow-sm);
    transition: width 0.16s ease;
  }

  .inspector-right.collapsed {
    width: 52px;
  }

  .inspector-right__bar {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px 10px 10px;
    border-bottom: 1px solid var(--border);
  }

  .inspector-right.collapsed .inspector-right__bar {
    justify-content: center;
    padding: 10px 6px;
    border-bottom: none;
  }

  .inspector-right__heading {
    display: flex;
    flex-direction: column;
    line-height: 1.2;
  }

  .inspector-right__eyebrow {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--blue-700);
  }

  .inspector-right__title {
    font-size: 13.5px;
    font-weight: 700;
    color: var(--text);
  }

  .inspector-right__toggle {
    width: 30px;
    height: 30px;
    flex-shrink: 0;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--surface-muted);
    color: var(--blue-700);
    font-weight: 700;
    cursor: pointer;
  }

  .inspector-right__body {
    overflow-y: auto;
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .inspector-right__body[hidden] {
    display: none;
  }

  .facet-card {
    padding: 10px 12px;
    border-radius: 10px;
    background: var(--surface-muted);
    border: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .facet-card h3 {
    margin: 0;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-muted);
  }

  .facet-buttons {
    display: flex;
    flex-direction: column;
    gap: 5px;
  }

  .facet-btn {
    text-align: left;
    padding: 6px 10px;
    border-radius: 8px;
    border: 1px solid var(--border-strong);
    background: var(--surface);
    color: var(--text);
    font-size: 11.5px;
    font-weight: 600;
    cursor: pointer;
  }

  .facet-btn.active {
    background: var(--blue-700);
    border-color: var(--blue-700);
    color: #ffffff;
  }

  .checklist {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .checklist__item {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    font-size: 11.5px;
    line-height: 1.35;
  }

  .checklist__check {
    width: 18px;
    height: 18px;
    border-radius: 999px;
    background: var(--blue-50);
    color: var(--blue-700);
    border: 1px solid var(--blue-200);
    display: grid;
    place-items: center;
    font-size: 10px;
    font-weight: 700;
    flex-shrink: 0;
    margin-top: 1px;
  }

  .checklist__text {
    display: flex;
    flex-direction: column;
    gap: 1px;
  }

  .checklist__text strong {
    color: var(--text);
    font-size: 11.5px;
  }

  .checklist__text span {
    color: var(--text-muted);
    font-size: 11px;
  }

  .inspect-modal-btn {
    padding: 9px 12px;
    border: none;
    border-radius: 10px;
    background: var(--blue-700);
    color: #ffffff;
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
    box-shadow: var(--shadow-sm);
  }

  .inspect-modal-btn:hover {
    background: var(--blue-900);
  }
</style>
