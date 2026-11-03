<script>
  import { onMount } from 'svelte';

  let { label = 'Loading' } = $props();

  /** @type {HTMLElement | undefined} */
  let spinnerEl = $state();

  onMount(() => {
    const el = spinnerEl;
    if (!el) return;

    const reduceMotion =
      typeof matchMedia === 'function' &&
      matchMedia('(prefers-reduced-motion: reduce)').matches;
    // Keep a real spin even with reduced motion — this IS the loading signal.
    // Slow it down instead of freezing (a frozen mark looks broken).
    const degPerMs = reduceMotion ? 0.09 : 0.36; // ~360°/4s vs ~360°/1s

    let angle = 0;
    let frame = 0;
    let last = performance.now();

    const tick = (now) => {
      const dt = Math.min(now - last, 64);
      last = now;
      angle = (angle + degPerMs * dt) % 360;
      el.style.transform = `rotate(${angle}deg)`;
      frame = requestAnimationFrame(tick);
    };

    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  });
</script>

<div class="orthos-loader" role="status" aria-live="polite" aria-label={label}>
  <div class="orthos-loader__stage" aria-hidden="true">
    <div class="orthos-loader__bloom"></div>

    <!-- Static brand tiles -->
    <svg class="orthos-loader__base" viewBox="0 0 32 32" focusable="false">
      <defs>
        <linearGradient id="orthos-loader-face" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="#3B82F6" />
          <stop offset="100%" stop-color="#1D4ED8" />
        </linearGradient>
      </defs>
      <rect width="32" height="32" rx="8" fill="url(#orthos-loader-face)" />
      <rect x="5" y="5" width="8" height="8" rx="2" fill="#EFF6FF" />
      <rect x="19" y="5" width="8" height="8" rx="2" fill="#BFDBFE" />
      <rect x="5" y="19" width="8" height="8" rx="2" fill="#93C5FD" />
      <rect x="19" y="19" width="8" height="8" rx="2" fill="#60A5FA" />
    </svg>

    <!-- Cross spins on an HTML wrapper (JS-driven — not CSS-on-SVG) -->
    <div class="orthos-loader__spinner" bind:this={spinnerEl}>
      <svg class="orthos-loader__axis" viewBox="0 0 32 32" focusable="false">
        <rect x="14.1" y="3.2" width="3.8" height="25.6" rx="1.9" fill="#FFFFFF" />
        <rect x="3.2" y="14.1" width="25.6" height="3.8" rx="1.9" fill="#FFFFFF" />
        <circle cx="16" cy="16" r="3.2" fill="#1E3A8A" />
        <circle cx="16" cy="16" r="1.4" fill="#FFFFFF" />
      </svg>
    </div>
  </div>
  <p class="orthos-loader__word">Orthos</p>
  <p class="orthos-loader__caption">{label}</p>
</div>

<style>
  .orthos-loader {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
  }

  .orthos-loader__stage {
    position: relative;
    width: 88px;
    height: 88px;
  }

  .orthos-loader__bloom {
    position: absolute;
    inset: 2px;
    border-radius: 22px;
    background: radial-gradient(
      circle,
      rgba(147, 197, 253, 0.7) 0%,
      rgba(37, 99, 235, 0.28) 42%,
      transparent 68%
    );
    animation: orthos-bloom 1.6s ease-in-out infinite;
    pointer-events: none;
  }

  .orthos-loader__base,
  .orthos-loader__spinner {
    position: absolute;
    top: 50%;
    left: 50%;
    width: 64px;
    height: 64px;
    margin: -32px 0 0 -32px;
  }

  .orthos-loader__base {
    filter: drop-shadow(0 10px 18px rgba(29, 78, 216, 0.3));
  }

  .orthos-loader__spinner {
    transform-origin: 50% 50%;
    will-change: transform;
    filter: drop-shadow(0 0 8px rgba(255, 255, 255, 0.45));
  }

  .orthos-loader__axis {
    display: block;
    width: 100%;
    height: 100%;
    overflow: visible;
  }

  .orthos-loader__word {
    margin: 0;
    font-size: 22px;
    font-weight: 800;
    letter-spacing: -0.02em;
    color: var(--blue-900, #1e3a8a);
  }

  .orthos-loader__caption {
    margin: 0;
    max-width: 280px;
    text-align: center;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.02em;
    color: var(--text-muted);
    line-height: 1.35;
  }

  @keyframes orthos-bloom {
    0%,
    100% {
      opacity: 0.4;
      transform: scale(0.94);
    }
    50% {
      opacity: 1;
      transform: scale(1.2);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .orthos-loader__bloom {
      animation: none;
      opacity: 0.65;
    }
  }
</style>
