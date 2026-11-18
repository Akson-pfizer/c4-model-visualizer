<script>
  import { ControlButton } from '@xyflow/svelte';
  import { panTool, togglePanTool } from '../panMode.svelte.js';
</script>

<ControlButton
  class={panTool.on ? 'pan-control is-active' : 'pan-control'}
  title={panTool.on ? 'Pan on — dragging moves the view' : 'Pan — dragging moves the view'}
  aria-label="Pan"
  aria-pressed={panTool.on}
  onclick={togglePanTool}
>
  <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
    <path
      fill="currentColor"
      d="M23 5.5V20c0 2.2-1.8 4-4 4h-7.3c-1.08 0-2.1-.43-2.85-1.19L1 14.83s1.26-1.23 1.3-1.25c.22-.19.49-.29.79-.29.22 0 .42.06.6.16.04.01 4.31 2.46 4.31 2.46V4c0-.83.67-1.5 1.5-1.5S11 3.17 11 4v7h1V1.5c0-.83.67-1.5 1.5-1.5S15 .67 15 1.5V11h1V2.5c0-.83.67-1.5 1.5-1.5s1.5.67 1.5 1.5V11h1V5.5c0-.83.67-1.5 1.5-1.5s1.5.67 1.5 1.5z"
    />
  </svg>
</ControlButton>

<style>
  :global(.svelte-flow__controls-button.pan-control.is-active) {
    background: var(--blue-50, #eff6ff) !important;
    color: var(--blue-700, #1d4ed8) !important;
  }

  /* Node cards set cursor:pointer, which would hide the pan affordance. */
  :global(.svelte-flow.is-pan-mode .svelte-flow__node),
  :global(.svelte-flow.is-pan-mode .svelte-flow__edge),
  :global(.svelte-flow.is-pan-mode .svelte-flow__edge-label),
  :global(.svelte-flow.is-pan-mode .c4-node) {
    cursor: grab;
  }

  :global(.svelte-flow.is-pan-mode .svelte-flow__pane.dragging),
  :global(.svelte-flow.is-pan-mode .svelte-flow__pane.dragging .svelte-flow__node),
  :global(.svelte-flow.is-pan-mode .svelte-flow__pane.dragging .c4-node) {
    cursor: grabbing;
  }

  /* Text selection or a native drag ghost would interrupt the pan gesture. */
  :global(.svelte-flow.is-pan-mode),
  :global(.svelte-flow.is-pan-mode *) {
    user-select: none;
    -webkit-user-drag: none;
  }
</style>
