<script>
  /**
   * Shared Native `<dialog>` Modal (`ui-experience` Principle 3 & SonarQube S6819).
   * - Uses native `<dialog>` element (never `<div role="dialog">`)
   * - ~90% viewport width/height with a visible `✕` close button
   * - Prevents opening external browser tabs for skill playbooks & citations
   */
  let {
    open = false,
    skill = null,
    onClose
  } = $props();

  /** @type {HTMLDialogElement | undefined} */
  let dialogEl = $state();

  $effect(() => {
    if (!dialogEl) return;
    if (open && !dialogEl.open) {
      dialogEl.showModal();
    } else if (!open && dialogEl.open) {
      dialogEl.close();
    }
  });

  function handleBackdropClick(event) {
    if (event.target === dialogEl) {
      onClose?.();
    }
  }
</script>

<dialog
  bind:this={dialogEl}
  class="skill-modal"
  aria-labelledby="skill-modal-title"
  onclose={() => onClose?.()}
  onclick={handleBackdropClick}
>
  {#if skill}
    <div class="skill-modal__shell">
      <header class="skill-modal__header">
        <div class="skill-modal__title-wrap">
          <span class="skill-modal__eyebrow">
            Skill #{skill.rank} · {skill.skill_markdown_path} · Native &lt;dialog&gt; Modal (Principle 3)
          </span>
          <h2 id="skill-modal-title" class="skill-modal__title">
            {skill.name} — <code>{skill.slash_command}</code>
          </h2>
        </div>
        <button
          type="button"
          class="skill-modal__close"
          aria-label="Close skill playbook modal"
          onclick={() => onClose?.()}
        >
          ✕
        </button>
      </header>

      <div class="skill-modal__body">
        <section class="modal-section">
          <h3>1. Problem Solved & Core Capability</h3>
          <p>{skill.problemSolved}</p>
        </section>

        <div class="modal-grid">
          <section class="modal-section modal-section--accent">
            <h3>2. Adapted with <code>~/.claude/skills/ui-ux-master</code></h3>
            <p>{skill.uiUxMasterRule}</p>
          </section>

          <section class="modal-section modal-section--accent">
            <h3>3. Adapted with <code>~/.claude/skills/ui-experience</code></h3>
            <p>{skill.uiExperienceRule}</p>
          </section>
        </div>

        <section class="modal-section">
          <h3>4. Installation & Invocation</h3>
          <pre class="modal-code"><code># Install portable SKILL.md playbook
{skill.install_command}

# Invoke inside Claude Code / Cursor
{skill.slash_command}</code></pre>
        </section>

        <section class="modal-section">
          <h3>5. Equipped Agents & Repository Evidence</h3>
          <p class="modal-evidence">
            <strong>Codebase Evidence:</strong> <code>{skill.codeEvidence}</code>
          </p>
          <div class="modal-chips">
            {#each skill.applicable_agents as agentId (agentId)}
              <span class="modal-chip">{agentId}</span>
            {/each}
          </div>
        </section>
      </div>

      <footer class="skill-modal__footer">
        <span class="skill-modal__status">Status: {skill.status}</span>
        <button type="button" class="skill-modal__done" onclick={() => onClose?.()}>
          Done (Esc)
        </button>
      </footer>
    </div>
  {/if}
</dialog>

<style>
  .skill-modal {
    width: min(90vw, 1080px);
    height: min(88vh, 780px);
    margin: auto;
    padding: 0;
    border: 1px solid var(--border-strong);
    border-radius: 16px;
    background: var(--surface);
    color: var(--text);
    box-shadow: var(--shadow-lg);
  }

  .skill-modal::backdrop {
    background: rgba(30, 58, 106, 0.42);
    backdrop-filter: blur(2px);
  }

  .skill-modal__shell {
    height: 100%;
    display: flex;
    flex-direction: column;
  }

  .skill-modal__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 16px 22px;
    border-bottom: 1px solid var(--border);
    background: var(--surface-muted);
  }

  .skill-modal__title-wrap {
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  .skill-modal__eyebrow {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--blue-700);
  }

  .skill-modal__title {
    font-size: 18px;
    font-weight: 700;
    margin: 0;
  }

  .skill-modal__close {
    width: 36px;
    height: 36px;
    border-radius: 10px;
    border: 1px solid var(--border-strong);
    background: var(--surface);
    color: var(--text);
    font-size: 16px;
    font-weight: 700;
    cursor: pointer;
  }

  .skill-modal__close:hover {
    background: var(--blue-50);
    color: var(--blue-700);
  }

  .skill-modal__body {
    flex: 1;
    overflow-y: auto;
    padding: 20px 22px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .modal-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 14px;
  }

  .modal-section {
    padding: 14px 16px;
    border-radius: 12px;
    border: 1px solid var(--border);
    background: var(--surface-muted);
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .modal-section--accent {
    background: var(--blue-50);
    border-color: var(--blue-200);
  }

  .modal-section h3 {
    margin: 0;
    font-size: 13px;
    font-weight: 700;
    color: var(--blue-900);
  }

  .modal-section p {
    margin: 0;
    font-size: 13.5px;
    line-height: 1.55;
    color: var(--text);
  }

  .modal-code {
    margin: 0;
    padding: 12px 14px;
    border-radius: 10px;
    background: #1e293b;
    color: #f8fafc;
    font-family: var(--mono);
    font-size: 12.5px;
    overflow-x: auto;
  }

  .modal-evidence {
    font-size: 12.5px;
  }

  .modal-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .modal-chip {
    font-family: var(--mono);
    font-size: 11.5px;
    font-weight: 700;
    padding: 3px 10px;
    border-radius: 999px;
    background: var(--surface);
    color: var(--blue-700);
    border: 1px solid var(--blue-200);
  }

  .skill-modal__footer {
    padding: 12px 22px;
    border-top: 1px solid var(--border);
    background: var(--surface-muted);
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .skill-modal__status {
    font-size: 12.5px;
    font-weight: 700;
    color: var(--blue-700);
  }

  .skill-modal__done {
    padding: 8px 18px;
    border: none;
    border-radius: 9px;
    background: var(--blue-700);
    color: #ffffff;
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
  }
</style>
