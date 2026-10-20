<script>
  let {
    plan,
    collapsed = false,
    approved = false,
    onToggleCollapse,
    onRefresh,
    onApprove
  } = $props();
</script>

{#if plan}
  <aside class="plan-panel" class:collapsed aria-label="Implementation plan">
    <div class="plan-panel__bar">
      <button
        type="button"
        class="plan-panel__toggle"
        aria-expanded={!collapsed}
        aria-controls="plan-panel-body"
        aria-label={collapsed ? 'Expand implementation plan panel' : 'Collapse implementation plan panel'}
        onclick={onToggleCollapse}
      >
        {collapsed ? '«' : '»'}
      </button>
      {#if !collapsed}
        <div class="plan-panel__heading">
          <span class="plan-panel__eyebrow">For human approval</span>
          <span class="plan-panel__title">Implementation Plan</span>
        </div>
      {/if}
    </div>

    <div id="plan-panel-body" class="plan-panel__body" hidden={collapsed}>
      <p class="plan-panel__summary">{plan.summary}</p>

      {#if plan.boundaryItems.length > 0}
        <section class="plan-panel__section">
          <h3>Boundaries in this diagram</h3>
          <ul>
            {#each plan.boundaryItems as item}
              <li>{item}</li>
            {/each}
          </ul>
        </section>
      {/if}

      {#if plan.componentItems.length > 0}
        <section class="plan-panel__section">
          <h3>Components read from the canvas ({plan.componentCount})</h3>
          <ol>
            {#each plan.componentItems as item}
              <li>{item}</li>
            {/each}
          </ol>
        </section>
      {/if}

      {#if plan.relationshipItems.length > 0}
        <section class="plan-panel__section">
          <h3>Connections and data flow ({plan.edgeCount})</h3>
          <ol>
            {#each plan.relationshipItems as item}
              <li>{item}</li>
            {/each}
          </ol>
        </section>
      {/if}

      {#if plan.steps.length > 0}
        <section class="plan-panel__section">
          <h3>Proposed build sequence</h3>
          <ol>
            {#each plan.steps as step}
              <li>{step}</li>
            {/each}
          </ol>
        </section>
      {/if}

      <footer class="plan-panel__footer">
        <button type="button" class="plan-panel__refresh" onclick={onRefresh}>
          Re-read diagram
        </button>
        <button type="button" class="plan-panel__approve" onclick={onApprove}>
          {approved ? 'Approved ✓' : 'Approve Plan'}
        </button>
      </footer>
    </div>
  </aside>
{/if}

<style>
  .plan-panel {
    width: 360px;
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

  .plan-panel.collapsed {
    width: 52px;
  }

  .plan-panel__bar {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px 10px 10px;
    border-bottom: 1px solid var(--border);
  }

  .plan-panel.collapsed .plan-panel__bar {
    justify-content: center;
    padding: 10px 6px;
    border-bottom: none;
  }

  .plan-panel__toggle {
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

  .plan-panel__heading {
    display: flex;
    flex-direction: column;
    line-height: 1.2;
  }

  .plan-panel__eyebrow {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--blue-700);
  }

  .plan-panel__title {
    font-size: 14px;
    font-weight: 700;
    color: var(--text);
  }

  .plan-panel__body {
    overflow: auto;
    padding: 14px 16px 16px;
    display: flex;
    flex-direction: column;
    gap: 14px;
    font-size: 13px;
    line-height: 1.5;
  }

  .plan-panel__body[hidden] {
    display: none;
  }

  .plan-panel__summary {
    margin: 0;
    padding: 10px 12px;
    border-radius: 10px;
    background: var(--blue-50);
    border: 1px solid var(--blue-200);
    color: var(--blue-900);
  }

  .plan-panel__section h3 {
    font-size: 12px;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--text-muted);
    margin: 0 0 6px;
  }

  .plan-panel__section ol,
  .plan-panel__section ul {
    margin: 0;
    padding-left: 1.2rem;
    color: var(--text);
  }

  .plan-panel__section li {
    margin-bottom: 6px;
  }

  .plan-panel__footer {
    margin-top: auto;
    padding-top: 12px;
    border-top: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .plan-panel__refresh {
    padding: 7px 12px;
    border: 1px solid var(--border-strong);
    border-radius: 9px;
    background: var(--surface);
    color: var(--text);
    font-size: 12.5px;
    font-weight: 600;
    cursor: pointer;
  }

  .plan-panel__approve {
    padding: 7px 14px;
    border: none;
    border-radius: 9px;
    background: var(--blue-700);
    color: #fff;
    font-size: 12.5px;
    font-weight: 700;
    cursor: pointer;
  }

  .plan-panel__approve:hover {
    background: var(--blue-900);
  }

  @media (max-width: 960px) {
    .plan-panel,
    .plan-panel.collapsed {
      width: auto;
    }
  }
</style>
