<script>
  /** Inline Orthos brand mark — orthogonal axis over a four-tile architecture grid. */
  let { size = 30, class: className = '' } = $props();
</script>

<svg
  class={className}
  width={size}
  height={size}
  viewBox="0 0 32 32"
  aria-hidden="true"
  focusable="false"
>
  <rect width="32" height="32" rx="8" fill="#1D4ED8" />
  <rect x="5" y="5" width="8" height="8" rx="2" fill="#EFF6FF" />
  <rect x="19" y="5" width="8" height="8" rx="2" fill="#BFDBFE" />
  <rect x="5" y="19" width="8" height="8" rx="2" fill="#93C5FD" />
  <rect x="19" y="19" width="8" height="8" rx="2" fill="#60A5FA" />
  <rect x="14.25" y="4.5" width="3.5" height="23" rx="1.75" fill="#FFFFFF" />
  <rect x="4.5" y="14.25" width="23" height="3.5" rx="1.75" fill="#FFFFFF" />
  <circle cx="16" cy="16" r="2.6" fill="#1E3A8A" />
  <circle cx="16" cy="16" r="1.15" fill="#FFFFFF" />
</svg>
