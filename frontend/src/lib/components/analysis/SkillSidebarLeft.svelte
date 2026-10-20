<script>
  /**
   * Left Docked Collapsible Sidebar (`ui-experience` Principle 2 & 5, Lesson L1).
   * - Hybrid combobox search (<input list="..."> + substring filtering)
   * - Never destroys or re-mounts the <input> while typing (Lesson L1)
   * - Explicit kind/rank badges on every skill item (Principle 13)
   * - Zero nested ternaries (SonarQube S3358)
   */
  import { ORIGIN_FILTERS } from '../../analysisCatalog.js';

  let {
    skills = [],
    selectedSkillId = 'frontend-design',
    searchQuery = '',
    originFilter = 'all',
    collapsed = false,
    onSelectSkill,
    onSearchChange,
    onOriginChange,
    onToggleCollapse
  } = $props();

  let toggleAriaLabel = $derived(
    collapsed ? 'Expand skills & search sidebar' : 'Collapse skills & search sidebar'
  );
  let toggleGlyph = $derived(collapsed ? '»' : '«');
</script>

<aside class="skill-sidebar" class:collapsed aria-label="Coding Agent Skills & Search Filter">
  <div class="skill-sidebar__bar">
    {#if !collapsed}
      <div class="skill-sidebar__heading">
        <span class="skill-sidebar__eyebrow">Left Filter Dock</span>
        <span class="skill-sidebar__title">17 Agent Skills</span>
      </div>
    {/if}
    <button
      type="button"
      class="skill-sidebar__toggle"
      aria-expanded={!collapsed}
      aria-controls="skill-sidebar-body"
      aria-label={toggleAriaLabel}
      onclick={() => onToggleCollapse?.()}
    >
      {toggleGlyph}
    </button>
  </div>

  <div id="skill-sidebar-body" class="skill-sidebar__body" hidden={collapsed}>
    <!-- Principle 5 & Lesson L1: Hybrid combobox search with stable DOM node -->
    <div class="filter-group">
      <label class="filter-group__label" for="skill-hybrid-combobox">
        Hybrid Skill Search (Combobox)
      </label>
      <div class="combobox-wrap">
        <input
          id="skill-hybrid-combobox"
          type="search"
          list="skill-combobox-options"
          class="combobox-input"
          placeholder="Type or pick skill (e.g. /shannon, frontend)..."
          value={searchQuery}
          oninput={(e) => onSearchChange?.(e.currentTarget.value)}
          autocomplete="off"
        />
        {#if searchQuery.length > 0}
          <button
            type="button"
            class="combobox-clear"
            aria-label="Clear skill search"
            onclick={() => onSearchChange?.('')}
          >
            ✕
          </button>
        {/if}
      </div>
      <datalist id="skill-combobox-options">
        {#each skills as item (item.uid)}
          <option value={item.name}>{item.slash_command} · {item.kindBadge}</option>
        {/each}
      </datalist>
    </div>

    <!-- Principle 7: Global origin/category filter cascade -->
    <div class="filter-group">
      <label class="filter-group__label" for="skill-origin-select">
        Skill Collection Cascade
      </label>
      <select
        id="skill-origin-select"
        class="filter-select"
        value={originFilter}
        onchange={(e) => onOriginChange?.(e.currentTarget.value)}
      >
        {#each ORIGIN_FILTERS as opt (opt.id)}
          <option value={opt.id}>{opt.label}</option>
        {/each}
      </select>
    </div>

    <div class="skill-count-bar">
      <span>Showing</span>
      <output class="skill-count-pill" for="skill-hybrid-combobox skill-origin-select">
        {skills.length} of 17 skills
      </output>
    </div>

    <ul class="skill-list" aria-label="Filtered coding agent skills">
      {#each skills as skill (skill.uid)}
        <li>
          <button
            type="button"
            class="skill-item"
            class:selected={skill.skill_id === selectedSkillId}
            aria-current={skill.skill_id === selectedSkillId ? 'true' : undefined}
            onclick={() => onSelectSkill?.(skill.skill_id)}
          >
            <div class="skill-item__top">
              <span class="skill-item__rank">#{skill.rank}</span>
              <span class="skill-item__cmd">{skill.slash_command}</span>
              <span class="skill-item__badge">{skill.kindBadge}</span>
            </div>
            <span class="skill-item__name">{skill.name}</span>
            <span class="skill-item__sub">{skill.subtitle}</span>
          </button>
        </li>
      {/each}
    </ul>
  </div>
</aside>

<style>
  .skill-sidebar {
    width: 300px;
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

  .skill-sidebar.collapsed {
    width: 52px;
  }

  .skill-sidebar__bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 10px 10px 14px;
    border-bottom: 1px solid var(--border);
  }

  .skill-sidebar.collapsed .skill-sidebar__bar {
    justify-content: center;
    padding: 10px 6px;
    border-bottom: none;
  }

  .skill-sidebar__heading {
    display: flex;
    flex-direction: column;
    line-height: 1.2;
  }

  .skill-sidebar__eyebrow {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--blue-700);
  }

  .skill-sidebar__title {
    font-size: 13.5px;
    font-weight: 700;
    color: var(--text);
  }

  .skill-sidebar__toggle {
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

  .skill-sidebar__body {
    overflow-y: auto;
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .skill-sidebar__body[hidden] {
    display: none;
  }

  .filter-group {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .filter-group__label {
    font-size: 10.5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-muted);
  }

  .combobox-wrap {
    position: relative;
    display: flex;
    align-items: center;
  }

  .combobox-input {
    width: 100%;
    padding: 7px 28px 7px 10px;
    border: 1.5px solid var(--border-strong);
    border-radius: 9px;
    background: var(--surface);
    color: var(--text);
    font-size: 12.5px;
  }

  .combobox-input:focus {
    outline: 2px solid var(--blue-200);
    border-color: var(--blue-600);
  }

  .combobox-clear {
    position: absolute;
    right: 6px;
    width: 22px;
    height: 22px;
    border: none;
    border-radius: 6px;
    background: var(--surface-muted);
    color: var(--text-muted);
    font-size: 11px;
    cursor: pointer;
  }

  .filter-select {
    width: 100%;
    padding: 6px 10px;
    border: 1.5px solid var(--border-strong);
    border-radius: 9px;
    background: var(--surface);
    color: var(--text);
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
  }

  .skill-count-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 11.5px;
    color: var(--text-muted);
    padding: 2px 2px 4px;
    border-bottom: 1px solid var(--border);
  }

  .skill-count-pill {
    font-family: var(--mono);
    font-size: 11px;
    font-weight: 700;
    padding: 1px 8px;
    border-radius: 999px;
    background: var(--blue-50);
    color: var(--blue-700);
    border: 1px solid var(--blue-200);
  }

  .skill-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .skill-item {
    width: 100%;
    text-align: left;
    padding: 8px 10px;
    border-radius: 10px;
    border: 1px solid var(--border);
    background: var(--surface-muted);
    display: flex;
    flex-direction: column;
    gap: 3px;
    cursor: pointer;
  }

  .skill-item:hover {
    border-color: var(--blue-400);
    background: var(--blue-50);
  }

  .skill-item.selected {
    border-color: var(--blue-600);
    background: var(--blue-50);
    box-shadow: inset 3px 0 0 var(--blue-700);
  }

  .skill-item__top {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .skill-item__rank {
    font-family: var(--mono);
    font-size: 10.5px;
    font-weight: 700;
    color: var(--blue-700);
  }

  .skill-item__cmd {
    font-family: var(--mono);
    font-size: 10.5px;
    color: var(--text-muted);
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .skill-item__badge {
    font-size: 9.5px;
    font-weight: 700;
    text-transform: uppercase;
    padding: 1px 6px;
    border-radius: 999px;
    background: var(--surface);
    color: var(--blue-700);
    border: 1px solid var(--blue-200);
  }

  .skill-item__name {
    font-size: 12.5px;
    font-weight: 700;
    color: var(--text);
  }

  .skill-item__sub {
    font-size: 11px;
    color: var(--text-muted);
    line-height: 1.3;
  }
</style>
