<script>
  let {
    open = false,
    profileName = 'Architect',
    onClose,
    onSaved
  } = $props();

  /** @type {HTMLDialogElement | undefined} */
  let dialogEl = $state();

  let displayName = $state('');
  let baseUrl = $state('');
  let apiKey = $state('');
  let maskedKey = $state('');
  let keyConfigured = $state(false);
  let showKey = $state(false);
  let keyDirty = $state(false);
  let loading = $state(false);
  let saving = $state(false);
  let error = $state(/** @type {string | null} */ (null));
  let status = $state(/** @type {string | null} */ (null));

  $effect(() => {
    const isOpen = Boolean(open);
    if (!dialogEl) return;
    if (isOpen && !dialogEl.open) {
      dialogEl.showModal();
      void loadCredentials();
    } else if (!isOpen && dialogEl.open) {
      dialogEl.close();
    }
  });

  async function loadCredentials() {
    loading = true;
    error = null;
    status = null;
    keyDirty = false;
    showKey = false;
    displayName = profileName || 'Architect';
    try {
      const res = await fetch('/api/llmhub/credentials');
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || `Could not load credentials (${res.status})`);
      }
      baseUrl = data.base_url || 'https://llmhub.platforms.pfizer/v1';
      maskedKey = data.api_key_masked || '';
      keyConfigured = Boolean(data.api_key_configured);
      apiKey = '';
      if (data.display_name) displayName = data.display_name;
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to load profile settings';
    } finally {
      loading = false;
    }
  }

  function handleBackdropClick(event) {
    if (event.target === dialogEl) onClose?.();
  }

  function onKeyInput(event) {
    keyDirty = true;
    apiKey = event.currentTarget.value;
  }

  async function handleSave(event) {
    event.preventDefault();
    saving = true;
    error = null;
    status = null;
    try {
      const body = {
        base_url: baseUrl.trim() || null
      };
      if (keyDirty) {
        body.api_key = apiKey.trim();
      }

      const res = await fetch('/api/llmhub/credentials', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || `Save failed (${res.status})`);
      }

      maskedKey = data.api_key_masked || '';
      keyConfigured = Boolean(data.api_key_configured);
      baseUrl = data.base_url || baseUrl;
      apiKey = '';
      keyDirty = false;
      showKey = false;
      status = keyConfigured
        ? 'LLMHub credentials saved.'
        : 'Saved. LLMHub API key is empty — LLM analysis will stay offline.';
      onSaved?.({
        display_name: displayName,
        api_key_configured: keyConfigured
      });
    } catch (err) {
      error = err instanceof Error ? err.message : 'Could not save settings';
    } finally {
      saving = false;
    }
  }
</script>

<dialog
  bind:this={dialogEl}
  class="profile-modal"
  aria-labelledby="profile-modal-title"
  onclose={() => onClose?.()}
  onclick={handleBackdropClick}
>
  <form class="profile-modal__inner" onsubmit={handleSave}>
    <header class="profile-modal__header">
      <div>
        <span class="profile-modal__eyebrow">Account · LLMHub</span>
        <h2 id="profile-modal-title" class="profile-modal__title">Profile settings</h2>
      </div>
      <button
        type="button"
        class="profile-modal__close"
        aria-label="Close profile settings"
        onclick={() => onClose?.()}
      >
        ✕
      </button>
    </header>

    <div class="profile-modal__body">
      {#if loading}
        <p class="profile-modal__hint">Loading credentials…</p>
      {:else}
        <label class="profile-modal__field">
          <span class="profile-modal__label">Display name</span>
          <input
            class="profile-modal__input profile-modal__input--locked"
            type="text"
            maxlength="48"
            value={displayName}
            autocomplete="nickname"
            readonly
            aria-readonly="true"
            title="Display name is managed from the Architect Catalog"
          />
        </label>

        <label class="profile-modal__field">
          <span class="profile-modal__label">LLMHub base URL</span>
          <input
            class="profile-modal__input"
            type="url"
            bind:value={baseUrl}
            placeholder="https://llmhub.platforms.pfizer/v1"
            autocomplete="off"
            disabled={saving}
          />
        </label>

        <div class="profile-modal__field">
          <div class="profile-modal__label-row">
            <span class="profile-modal__label" id="llmhub-key-label">LLMHub API key</span>
            <span
              class="profile-modal__badge"
              class:is-on={keyConfigured}
              class:is-off={!keyConfigured}
            >
              {keyConfigured ? 'Configured' : 'Not set'}
            </span>
          </div>
          <div class="profile-modal__secret">
            <input
              class="profile-modal__input profile-modal__input--secret"
              type={showKey ? 'text' : 'password'}
              value={keyDirty ? apiKey : ''}
              placeholder={keyConfigured
                ? maskedKey || '••••••••••••••••'
                : 'Paste LLMHub API key'}
              autocomplete="new-password"
              spellcheck="false"
              aria-labelledby="llmhub-key-label"
              disabled={saving}
              oninput={onKeyInput}
            />
            <button
              type="button"
              class="profile-modal__reveal"
              onclick={() => (showKey = !showKey)}
              disabled={saving || (!keyDirty && !apiKey)}
              aria-pressed={showKey}
            >
              {showKey ? 'Hide' : 'Show'}
            </button>
          </div>
          <p class="profile-modal__hint">
            {#if keyConfigured && !keyDirty}
              Current key is masked ({maskedKey}). Enter a new value only to replace it.
            {:else}
              Stored in backend <code>.env</code> as <code>LLMHUB_API_KEY</code>. Never shown in full.
            {/if}
          </p>
        </div>

        {#if error}
          <p class="profile-modal__error" role="alert">{error}</p>
        {/if}
        {#if status}
          <p class="profile-modal__status" role="status">{status}</p>
        {/if}
      {/if}
    </div>

    <footer class="profile-modal__footer">
      <button type="button" class="profile-modal__btn profile-modal__btn--ghost" onclick={() => onClose?.()}>
        Cancel
      </button>
      <button
        type="submit"
        class="profile-modal__btn profile-modal__btn--primary"
        disabled={loading || saving}
      >
        {saving ? 'Saving…' : 'Save settings'}
      </button>
    </footer>
  </form>
</dialog>

<style>
  .profile-modal {
    width: min(480px, 92vw);
    max-height: 86vh;
    margin: auto;
    padding: 0;
    border: 1px solid var(--border-strong);
    border-radius: 16px;
    background: var(--surface);
    color: var(--text);
    box-shadow: 0 22px 48px rgba(15, 23, 42, 0.24);
  }

  .profile-modal::backdrop {
    background: rgba(15, 23, 42, 0.42);
    backdrop-filter: blur(2px);
  }

  .profile-modal__inner {
    display: flex;
    flex-direction: column;
    max-height: 86vh;
  }

  .profile-modal__header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    padding: 16px 20px 12px;
    border-bottom: 1px solid var(--border);
  }

  .profile-modal__eyebrow {
    font-size: 10.5px;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: var(--blue-700);
  }

  .profile-modal__title {
    margin: 2px 0 0;
    font-size: 18px;
  }

  .profile-modal__close {
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

  .profile-modal__body {
    padding: 16px 20px;
    display: flex;
    flex-direction: column;
    gap: 14px;
    overflow-y: auto;
  }

  .profile-modal__field {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .profile-modal__label-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .profile-modal__label {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--text-muted);
  }

  .profile-modal__badge {
    font-size: 10.5px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 999px;
    border: 1px solid var(--border);
  }

  .profile-modal__badge.is-on {
    background: var(--blue-50);
    border-color: var(--blue-200);
    color: var(--blue-700);
  }

  .profile-modal__badge.is-off {
    background: #fef2f2;
    border-color: #fecaca;
    color: #b91c1c;
  }

  .profile-modal__input {
    width: 100%;
    padding: 9px 12px;
    border: 1.5px solid var(--border-strong);
    border-radius: 9px;
    background: var(--surface);
    color: var(--text);
    font-size: 13px;
  }

  .profile-modal__input:focus {
    outline: 2px solid var(--blue-200);
    border-color: var(--blue-600);
  }

  .profile-modal__input--locked {
    background: var(--surface-muted);
    color: var(--text-muted);
    cursor: default;
  }

  .profile-modal__input--locked:focus {
    outline: none;
    border-color: var(--border-strong);
  }

  .profile-modal__secret {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 8px;
  }

  .profile-modal__input--secret {
    font-family: var(--mono);
    letter-spacing: 0.04em;
  }

  .profile-modal__reveal {
    padding: 0 12px;
    border: 1px solid var(--border-strong);
    border-radius: 9px;
    background: var(--surface-muted);
    color: var(--blue-700);
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
    white-space: nowrap;
  }

  .profile-modal__reveal:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .profile-modal__hint {
    margin: 0;
    font-size: 11.5px;
    color: var(--text-faint);
    line-height: 1.4;
  }

  .profile-modal__hint code {
    font-family: var(--mono);
    font-size: 10.5px;
  }

  .profile-modal__error {
    margin: 0;
    padding: 8px 10px;
    border-radius: 8px;
    background: #fef2f2;
    border: 1px solid #fecaca;
    color: #b91c1c;
    font-size: 12px;
  }

  .profile-modal__status {
    margin: 0;
    padding: 8px 10px;
    border-radius: 8px;
    background: var(--blue-50);
    border: 1px solid var(--blue-200);
    color: var(--blue-800, #1e40af);
    font-size: 12px;
  }

  .profile-modal__footer {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    padding: 12px 20px 16px;
    border-top: 1px solid var(--border);
  }

  .profile-modal__btn {
    padding: 8px 14px;
    border-radius: 9px;
    font-size: 12.5px;
    font-weight: 700;
    cursor: pointer;
  }

  .profile-modal__btn--ghost {
    border: 1px solid var(--border-strong);
    background: var(--surface);
    color: var(--text);
  }

  .profile-modal__btn--primary {
    border: none;
    background: var(--blue-700);
    color: #fff;
  }

  .profile-modal__btn--primary:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }
</style>
