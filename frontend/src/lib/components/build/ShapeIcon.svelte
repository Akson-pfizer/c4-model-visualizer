<script>
  let { id } = $props();
</script>

<svg class="shape-icon" viewBox="0 0 32 32" aria-hidden="true">
  {#if id === 'person'}
    <circle cx="16" cy="9" r="4.2" fill="currentColor" />
    <path d="M8 26c1.2-5 4.2-7.5 8-7.5S22.8 21 24 26" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" />
  {:else if id === 'system'}
    <rect x="5" y="8" width="22" height="16" rx="3" fill="currentColor" />
  {:else if id === 'external-system'}
    <rect x="5" y="8" width="22" height="16" rx="3" fill="none" stroke="currentColor" stroke-width="2" stroke-dasharray="3 2.5" />
  {:else if id === 'container'}
    <rect x="5" y="7" width="22" height="18" rx="3" fill="none" stroke="currentColor" stroke-width="2" />
    <rect x="10" y="12" width="12" height="8" rx="1.5" fill="currentColor" />
  {:else if id === 'database'}
    <ellipse cx="16" cy="9" rx="8" ry="3.2" fill="none" stroke="currentColor" stroke-width="2" />
    <path d="M8 9v12c0 1.8 3.6 3.2 8 3.2s8-1.4 8-3.2V9" fill="none" stroke="currentColor" stroke-width="2" />
    <path d="M8 15c0 1.8 3.6 3.2 8 3.2s8-1.4 8-3.2" fill="none" stroke="currentColor" stroke-width="2" />
  {:else if id === 'component'}
    <rect x="5" y="8" width="22" height="16" rx="3" fill="none" stroke="currentColor" stroke-width="2" />
    <rect x="8" y="11" width="5" height="4" rx="1" fill="currentColor" />
    <rect x="15" y="11" width="8" height="2" rx="1" fill="currentColor" />
    <rect x="15" y="16" width="6" height="2" rx="1" fill="currentColor" />
  {:else if id === 'boundary'}
    <rect x="4" y="6" width="24" height="20" rx="3" fill="none" stroke="currentColor" stroke-width="2" stroke-dasharray="4 3" />
    <path d="M10 6h8" stroke="var(--surface)" stroke-width="3" />
    <path d="M11 6h6" stroke="currentColor" stroke-width="2" />
  {:else if id === 'uses'}
    <path d="M5 16h16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
    <path d="M18 11l7 5-7 5" fill="currentColor" />
  {:else if id === 'async'}
    <path d="M5 16h16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-dasharray="3 2.5" />
    <path d="M18 11l7 5-7 5" fill="currentColor" />
  {:else if id === 'bidirectional'}
    <path d="M10 16h12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
    <path d="M14 11L7 16l7 5" fill="currentColor" />
    <path d="M18 11l7 5-7 5" fill="currentColor" />
  {:else if id === 'dependency'}
    <path d="M5 16h17" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-dasharray="3 2.5" />
    <path d="M18 11l7 5-7 5" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" />
  {/if}
</svg>

<style>
  .shape-icon {
    width: 28px;
    height: 28px;
    display: block;
  }
</style>
