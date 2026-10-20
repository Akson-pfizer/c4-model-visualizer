<script>
  let { label = 'Loading' } = $props();
</script>

<div class="pfizer-loader" role="status" aria-live="polite" aria-label={label}>
  <p class="pfizer-loader__word" aria-hidden="true">
    <span>pfi</span><span class="pfizer-loader__z">z</span><span>er</span>
  </p>
  <p class="pfizer-loader__caption">{label}</p>
</div>

<style>
  .pfizer-loader {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
  }

  .pfizer-loader__word {
    margin: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 48px;
    font-weight: 700;
    letter-spacing: -0.03em;
    line-height: 1;
    color: var(--blue-900);
    perspective: 280px;
  }

  .pfizer-loader__z {
    display: inline-block;
    width: 0.72em;
    text-align: center;
    color: var(--blue-600);
    transform-origin: center center;
    transform-style: preserve-3d;
    animation-name: pfizer-z-spin;
    animation-duration: 0.8s;
    animation-timing-function: linear;
    animation-iteration-count: infinite;
  }

  .pfizer-loader__caption {
    margin: 0;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.02em;
    color: var(--text-muted);
  }

  @keyframes pfizer-z-spin {
    from {
      transform: rotateY(0deg);
    }
    to {
      transform: rotateY(360deg);
    }
  }
</style>
