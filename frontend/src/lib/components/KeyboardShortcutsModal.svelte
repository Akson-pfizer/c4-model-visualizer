<script>
  import { SHORTCUT_GROUPS } from '../keyboardShortcuts.js';

  let { open = false, onClose } = $props();

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
  class="shortcuts-modal"
  aria-labelledby="shortcuts-modal-title"
  onclose={() => onClose?.()}
  onclick={handleBackdropClick}
>
  <div class="shortcuts-modal__inner">
    <header class="shortcuts-modal__header">
      <div>
        <span class="shortcuts-modal__eyebrow">Cross-Platform Keybindings · macOS & Windows</span>
        <h2 id="shortcuts-modal-title" class="shortcuts-modal__title">
          Keyboard Shortcuts Reference
        </h2>
      </div>
      <button
        type="button"
        class="shortcuts-modal__close"
        aria-label="Close keyboard shortcuts modal"
        onclick={() => onClose?.()}
      >
        ✕
      </button>
    </header>

    <div class="shortcuts-modal__body">
      {#each SHORTCUT_GROUPS as section (section.group)}
        <section class="shortcuts-group">
          <h3 class="shortcuts-group__title">{section.group}</h3>
          <div class="shortcuts-table-wrap">
            <table class="shortcuts-table">
              <thead>
                <tr>
                  <th scope="col">Action</th>
                  <th scope="col">macOS</th>
                  <th scope="col">Windows / Linux</th>
                </tr>
              </thead>
              <tbody>
                {#each section.items as item (item.action)}
                  <tr>
                    <td class="shortcuts-table__action">{item.action}</td>
                    <td><kbd class="kbd-pill">{item.mac}</kbd></td>
                    <td><kbd class="kbd-pill kbd-pill--win">{item.win}</kbd></td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        </section>
      {/each}
    </div>

    <footer class="shortcuts-modal__footer">
      <span>
        Tip: All shortcuts automatically detect <strong>⌘ Command</strong> on macOS and
        <strong>Ctrl</strong> on Windows / Linux.
      </span>
      <button type="button" class="shortcuts-modal__done" onclick={() => onClose?.()}>
        Done
      </button>
    </footer>
  </div>
</dialog>

<style>
  .shortcuts-modal {
    width: min(820px, 92vw);
    max-height: 86vh;
    margin: auto;
    padding: 0;
    border: 1px solid var(--border-strong);
    border-radius: 16px;
    background: var(--surface);
    color: var(--text);
    box-shadow: 0 22px 48px rgba(15, 23, 42, 0.24);
  }

  .shortcuts-modal::backdrop {
    background: rgba(15, 23, 42, 0.42);
    backdrop-filter: blur(2px);
  }

  .shortcuts-modal__inner {
    display: flex;
    flex-direction: column;
    max-height: 86vh;
  }

  .shortcuts-modal__header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    padding: 16px 22px 12px;
    border-bottom: 1px solid var(--border);
  }

  .shortcuts-modal__eyebrow {
    font-size: 10.5px;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: var(--blue-700);
  }

  .shortcuts-modal__title {
    margin: 2px 0 0;
    font-size: 18px;
  }

  .shortcuts-modal__close {
    width: 32px;
    height: 32px;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--surface-muted);
    color: var(--text-muted);
    font-size: 14px;
    font-weight: 700;
    cursor: pointer;
  }

  .shortcuts-modal__close:hover {
    background: var(--blue-50);
    color: var(--blue-700);
  }

  .shortcuts-modal__body {
    padding: 16px 22px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 18px;
  }

  .shortcuts-group__title {
    margin: 0 0 8px;
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--blue-700);
  }

  .shortcuts-table-wrap {
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow: hidden;
  }

  .shortcuts-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12.5px;
  }

  .shortcuts-table th,
  .shortcuts-table td {
    padding: 8px 12px;
    text-align: left;
    border-bottom: 1px solid var(--border);
  }

  .shortcuts-table th {
    background: var(--surface-muted);
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--text-muted);
  }

  .shortcuts-table tr:last-child td {
    border-bottom: none;
  }

  .shortcuts-table__action {
    font-weight: 500;
    color: var(--text);
  }

  .kbd-pill {
    display: inline-block;
    padding: 2px 8px;
    font-family: var(--mono);
    font-size: 11.5px;
    font-weight: 700;
    color: var(--blue-800, #1e40af);
    background: var(--blue-50);
    border: 1px solid var(--blue-200);
    border-radius: 6px;
    white-space: nowrap;
  }

  .kbd-pill--win {
    color: var(--text);
    background: var(--surface-muted);
    border-color: var(--border-strong);
  }

  .shortcuts-modal__footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 12px 22px;
    border-top: 1px solid var(--border);
    background: var(--surface-muted);
    font-size: 12px;
    color: var(--text-muted);
  }

  .shortcuts-modal__done {
    padding: 6px 16px;
    border: none;
    border-radius: 8px;
    background: var(--blue-700);
    color: #ffffff;
    font-size: 12.5px;
    font-weight: 700;
    cursor: pointer;
  }
</style>
